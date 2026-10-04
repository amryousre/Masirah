import { NextResponse } from "next/server";
import { hasLocale } from "next-intl";

import { routing } from "@/i18n/routing";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { storeUpload } from "@/lib/adapters/uploads";
import { checkBatch, MAX_BATCH_FILES } from "@/lib/domain/uploads";

// POST /api/uploads (T061, contracts/web-routes.md): a batch of up to 25 CVs, each stored,
// recorded and queued, then an answer at once. Extraction happens in the worker; this route never
// waits for it. The organisation is the session's; any organisation in the form is ignored.
//
// Form fields: files (repeated), jobId (optional), locale ("ar" or "en", the reader's language
// for the justification and summary, FR-015).
export async function POST(request: Request) {
  const supabase = await createSupabaseServerClient();
  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    return NextResponse.json({ error: "not-signed-in" }, { status: 401 });
  }

  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return NextResponse.json({ error: "not-a-form" }, { status: 400 });
  }

  const files = form.getAll("files").filter((value): value is File => value instanceof File);
  if (!checkBatch(files.length)) {
    return NextResponse.json(
      { error: files.length === 0 ? "no-files" : "too-many-files", max: MAX_BATCH_FILES },
      { status: 400 },
    );
  }

  const locale = form.get("locale");
  if (typeof locale !== "string" || !hasLocale(routing.locales, locale)) {
    return NextResponse.json({ error: "locale" }, { status: 400 });
  }

  const jobField = form.get("jobId");
  const jobId = typeof jobField === "string" && jobField !== "" ? jobField : null;
  if (jobId !== null) {
    // Row level security makes another organisation's job invisible, so it reads as missing.
    const { data } = await supabase.from("job").select("id").eq("id", jobId).maybeSingle();
    if (data === null) return NextResponse.json({ error: "job-not-found" }, { status: 404 });
  }

  const outcomes = [];
  for (const file of files) {
    outcomes.push(await storeUpload(supabase, access.session.organisationId, file, jobId, locale));
  }
  return NextResponse.json({ files: outcomes }, { status: 202 });
}
