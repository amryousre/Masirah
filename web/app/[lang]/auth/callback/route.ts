import { type NextRequest, NextResponse } from "next/server";
import { hasLocale } from "next-intl";

import { routing } from "@/i18n/routing";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";

import { callbackOutcome } from "./outcome";

// Where Google sign-in returns (T024). The code is exchanged for a session here, on the server,
// and the session is kept only if the user belongs to an organisation.
export async function GET(request: NextRequest, { params }: RouteContext<"/[lang]/auth/callback">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) return new NextResponse(null, { status: 404 });

  const go = (path: string) => NextResponse.redirect(new URL(`/${lang}${path}`, request.url), 303);

  const outcome = callbackOutcome(request.nextUrl.searchParams);
  if (outcome.kind === "not-invited") return go("/sign-in/no-access");
  if (outcome.kind === "failed") return go("/sign-in?error=google");

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.exchangeCodeForSession(outcome.code);
  if (error) return go("/sign-in?error=google");

  const access = await readAccess(supabase);
  if (access.kind !== "member") {
    await supabase.auth.signOut({ scope: "local" });
    return go("/sign-in/no-access?reason=no-organisation");
  }
  return go("/jobs");
}
