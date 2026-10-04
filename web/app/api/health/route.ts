import { NextResponse } from "next/server";

import { readHealthFigures } from "@/lib/adapters/health";
import { serviceHealth } from "@/lib/domain/health";

// T030: the cheapest early warning that the worker has stopped. An uptime monitor polls this and
// alerts on anything but 200. It needs no sign-in and reports only aggregate figures.
export const dynamic = "force-dynamic";

const NOT_CACHED = { "Cache-Control": "no-store" };

export async function GET() {
  const figures = await readHealthFigures();
  if (figures === null) {
    return NextResponse.json(
      { status: "unavailable", problems: ["database-unreachable"] },
      { status: 503, headers: NOT_CACHED },
    );
  }
  const health = serviceHealth(figures);
  return NextResponse.json(
    { ...health, ...figures },
    { status: health.status === "ok" ? 200 : 503, headers: NOT_CACHED },
  );
}
