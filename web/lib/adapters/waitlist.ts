import type { Locale } from "@/i18n/routing";

import type { SupabaseClient } from "./supabase";
import { reportError } from "./telemetry";

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
  // Anything else is ours: an outage, the hourly limit (53400), or a grant gone wrong. The visitor
  // is told to try later; the log says which.
  reportError("join_waitlist failed", { code: error.code, message: error.message });
  return "unavailable";
}
