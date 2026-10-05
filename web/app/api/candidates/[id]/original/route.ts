import { NextResponse } from "next/server";

import { recordActivity } from "@/lib/adapters/activity";
import { readCandidatePage } from "@/lib/adapters/candidate-page";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
/** Long enough for the browser to follow the redirect, too short to pass the link on. */
const LINK_SECONDS = 60;

// GET /api/candidates/{id}/original?job={jobId} (T099, FR-030): the candidate's original CV as
// sent for the job, downloaded. Taking a CV out of the product is an export, so it is written to
// the audit trail before the member is redirected to a one-minute signed link.
export async function GET(
  request: Request,
  { params }: RouteContext<"/api/candidates/[id]/original">,
) {
  const supabase = await createSupabaseServerClient();
  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    return NextResponse.json({ error: "not-signed-in" }, { status: 401 });
  }
  const { id } = await params;
  const jobId = new URL(request.url).searchParams.get("job") ?? "";
  if (!UUID.test(id) || !UUID.test(jobId)) {
    return NextResponse.json({ error: "not-found" }, { status: 404 });
  }

  // Row level security hides another organisation's candidate, so it reads as missing.
  const page = await readCandidatePage(supabase, jobId, id);
  if (page?.document == null) return NextResponse.json({ error: "not-found" }, { status: 404 });

  const { data, error } = await supabase.storage
    .from("cv-originals")
    .createSignedUrl(page.document.storagePath, LINK_SECONDS, {
      download: page.document.fileName,
    });
  if (error) return NextResponse.json({ error: "not-found" }, { status: 404 });

  await recordActivity(
    supabase,
    access.session,
    "candidate.exported",
    { type: "candidate", id },
    { job_id: jobId, cv_file_id: page.document.id },
  );
  const response = NextResponse.redirect(data.signedUrl, 302);
  response.headers.set("cache-control", "no-store");
  return response;
}
