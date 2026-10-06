import { NextResponse } from "next/server";

import { requestDeletion } from "@/lib/adapters/deletion";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// DELETE /api/candidates/{id} (T101, FR-076, contracts/web-routes.md): asks for the candidate's
// personal data to be removed. The request is recorded at once and answered 202; the worker's
// purge removes the originals, the identity and the profile on its next sweep, within the hour.
export async function DELETE(_request: Request, { params }: RouteContext<"/api/candidates/[id]">) {
  const supabase = await createSupabaseServerClient();
  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    return NextResponse.json({ error: "not-signed-in" }, { status: 401 });
  }
  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ error: "not-found" }, { status: 404 });

  const outcome = await requestDeletion(supabase, id);
  switch (outcome.kind) {
    case "not-found":
      return NextResponse.json({ error: "not-found" }, { status: 404 });
    case "refused":
      return NextResponse.json({ error: "refused" }, { status: 403 });
    case "requested":
      return NextResponse.json({ requestedAt: outcome.requestedAt }, { status: 202 });
  }
}
