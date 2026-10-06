import { NextResponse } from "next/server";

import { recordActivity } from "@/lib/adapters/activity";
import { reviewOriginal } from "@/lib/adapters/review-queue";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
/** Long enough for the browser to follow the redirect, too short to pass the link on. */
const LINK_SECONDS = 60;

// GET /api/cv-files/{id}/original (T081): the original of a CV in the review queue, downloaded.
// It may have no candidate yet, so it is found by its file; taking it out of the product is an
// export, written to the audit trail before the member is redirected to a one-minute link.
export async function GET(
  _request: Request,
  { params }: RouteContext<"/api/cv-files/[id]/original">,
) {
  const supabase = await createSupabaseServerClient();
  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    return NextResponse.json({ error: "not-signed-in" }, { status: 401 });
  }
  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ error: "not-found" }, { status: 404 });

  // Row level security hides another organisation's file, so it reads as missing.
  const original = await reviewOriginal(supabase, id);
  if (original === null) return NextResponse.json({ error: "not-found" }, { status: 404 });

  const { data, error } = await supabase.storage
    .from("cv-originals")
    .createSignedUrl(original.storagePath, LINK_SECONDS, { download: original.fileName });
  if (error) return NextResponse.json({ error: "not-found" }, { status: 404 });

  await recordActivity(supabase, access.session, "cv_file.exported", { type: "cv_file", id });
  const response = NextResponse.redirect(data.signedUrl, 302);
  response.headers.set("cache-control", "no-store");
  return response;
}
