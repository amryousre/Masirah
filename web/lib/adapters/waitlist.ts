import type { Locale } from "@/i18n/routing";

import type { SupabaseClient } from "./supabase";
import { logEvent, reportError } from "./telemetry";

/**
 * Adds a work email to the landing page's waitlist through public.join_waitlist (migration 0027),
 * the one door a visitor has into it. The list itself is private: nothing here can read it back.
 * The address is the domain's checked form (lib/domain/waitlist.ts).
 */
export async function joinWaitlist(
  supabase: SupabaseClient,
  email: string,
  locale: Locale,
): Promise<"joined" | "invalid" | "unavailable"> {
  const { error } = await supabase.rpc("join_waitlist", { email, locale });
  if (error === null) return "joined";
  // 22023 is the database refusing what the page let through: say so as the page would.
  if (error.code === "22023") return "invalid";
  // The hourly limit (53400) is the waitlist holding off a flood, as designed: logged, not
  // reported, or the flood would spend Sentry's quota and real errors would be dropped.
  if (error.code === "53400") {
    logEvent("warn", "join_waitlist at its hourly limit", { code: error.code });
    return "unavailable";
  }
  // Anything else is ours: an outage or a grant gone wrong. The visitor is told to try later.
  reportError("join_waitlist failed", { code: error.code, message: error.message });
  return "unavailable";
}
