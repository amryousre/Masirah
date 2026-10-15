import type { Locale } from "@/i18n/routing";

import type { SupabaseClient } from "./supabase";

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
  return error.code === "22023" ? "invalid" : "unavailable";
}
