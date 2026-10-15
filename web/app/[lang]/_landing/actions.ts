"use server";

import { hasLocale } from "next-intl";

import { type Locale, routing } from "@/i18n/routing";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { joinWaitlist } from "@/lib/adapters/waitlist";
import { waitlistEmail } from "@/lib/domain/waitlist";

export interface WaitlistState {
  readonly outcome?: "joined" | "invalid" | "unavailable";
  /** Given back so a refused address does not have to be typed again. */
  readonly email: string;
}

/** The landing page's waitlist form. The locale is bound on the server, and checked anyway. */
export async function joinTheWaitlist(
  locale: Locale,
  _previous: WaitlistState,
  form: FormData,
): Promise<WaitlistState> {
  if (!hasLocale(routing.locales, locale)) throw new Error("Unknown locale");
  const raw = form.get("email");
  const typed = typeof raw === "string" ? raw : "";
  const email = waitlistEmail(typed);
  if (email === null) return { outcome: "invalid", email: typed };
  const outcome = await joinWaitlist(await createSupabaseServerClient(), email, locale);
  return { outcome, email: outcome === "joined" ? "" : typed };
}
