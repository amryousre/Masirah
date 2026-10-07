import type { SupabaseClient } from "./supabase";

export interface OrganisationUsage {
  /** CVs read by a model this month, counted as the worker counts them (migration 0026). */
  used: number;
  limit: number;
  /** Processing is halted: the CV limit or the spend ceiling was reached (FR-026). */
  atLimit: boolean;
  /** Files still queued, which is where the worker leaves them at a limit. */
  waiting: number;
  renewsAt: string;
}

/** The signed-in member's organisation this month, or null when it cannot be read. */
export async function readUsage(supabase: SupabaseClient): Promise<OrganisationUsage | null> {
  const { data, error } = await supabase.rpc("organisation_usage").maybeSingle();
  if (error) throw new Error(`The month's usage could not be read: ${error.message}`);
  if (data === null) return null;
  return {
    used: data.cvs,
    limit: data.cv_limit,
    atLimit: data.at_limit,
    waiting: data.waiting,
    renewsAt: data.renews_at,
  };
}

/** The renewal day as the interface shows it: "1 Nov", in Cairo where the month is counted. */
export function renewalDay(renewsAt: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    day: "numeric",
    month: "short",
    timeZone: "Africa/Cairo",
  }).format(new Date(renewsAt));
}
