import { nameNormalised } from "@/lib/domain/names";

import type { SupabaseClient } from "./supabase";

/** The organisation's retention period in months, or null when it never deletes automatically. */
export async function readRetention(supabase: SupabaseClient): Promise<number | null> {
  const { data, error } = await supabase.from("organisation").select("retention_months").single();
  if (error) throw new Error(`The settings could not read the retention period: ${error.message}`);
  return data.retention_months;
}

/**
 * Sets the period through set_retention (migration 0022), which records the member and starts the
 * seven days in which a shorter period deletes nobody. Returns how many candidates the new period
 * will remove once those days pass.
 */
export async function setRetention(
  supabase: SupabaseClient,
  months: number | null,
): Promise<number> {
  const { data, error } = await supabase.rpc("set_retention", months === null ? {} : { months });
  if (error) throw new Error(`The retention period could not be saved: ${error.message}`);
  return data;
}

export interface CandidateMatch {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  /** How many jobs they applied to. */
  jobs: number;
  lastActive: string;
}

/**
 * Candidates a deletion request might be about (T102), found by email, phone or name in either
 * script. The pattern has been made safe for the filter by lookupPattern; row level security keeps
 * the search inside the member's organisation, and candidates already deleted are left out.
 */
export async function findCandidates(
  supabase: SupabaseClient,
  pattern: string,
): Promise<CandidateMatch[]> {
  const form = nameNormalised(pattern);
  const matches = [
    `full_name.ilike.%${pattern}%`,
    `email.ilike.%${pattern}%`,
    `phone.ilike.%${pattern}%`,
    ...(form === "" ? [] : [`name_normalised.ilike.%${form}%`]),
  ];
  const { data, error } = await supabase
    .from("candidate")
    .select("id, full_name, email, phone, updated_at, application(count)")
    .is("purged_at", null)
    .or(matches.join(","))
    .order("updated_at", { ascending: false })
    .limit(5);
  if (error) throw new Error(`Candidates could not be looked up: ${error.message}`);
  return data.map((row) => ({
    id: row.id,
    name: row.full_name,
    email: row.email,
    phone: row.phone,
    jobs: row.application[0]?.count ?? 0,
    lastActive: row.updated_at,
  }));
}
