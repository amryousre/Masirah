import { NextResponse } from "next/server";

import { recordDecision } from "@/lib/adapters/decisions";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { decisionRequest } from "@/lib/domain/decisions";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// POST /api/applications/{id}/decision (T090, contracts/web-routes.md): shortlist, reject with a
// reason, or undo either. The decider is the signed-in member, taken by the database from the
// session; a decider named in the body is ignored. Body: { decision, reason? }.
export async function POST(
  request: Request,
  { params }: RouteContext<"/api/applications/[id]/decision">,
) {
  const supabase = await createSupabaseServerClient();
  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    return NextResponse.json({ error: "not-signed-in" }, { status: 401 });
  }

  const { id } = await params;
  if (!UUID.test(id)) return NextResponse.json({ error: "not-found" }, { status: 404 });

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "not-json" }, { status: 400 });
  }
  const parsed = decisionRequest(body);
  if (!parsed.ok) return NextResponse.json({ error: parsed.error }, { status: 400 });

  const outcome = await recordDecision(supabase, id, parsed.decision, parsed.reason);
  switch (outcome.kind) {
    case "not-found":
      return NextResponse.json({ error: "not-found" }, { status: 404 });
    case "refused":
      return NextResponse.json({ error: "refused" }, { status: 403 });
    case "recorded":
      return NextResponse.json(
        {
          decision: outcome.decision,
          decidedBy: outcome.decidedBy,
          decidedAt: outcome.decidedAt,
        },
        { status: 200 },
      );
  }
}
