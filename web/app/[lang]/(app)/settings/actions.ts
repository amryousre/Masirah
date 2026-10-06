"use server";

import { readAccess } from "@/lib/adapters/session";
import { type CandidateMatch, findCandidates, setRetention } from "@/lib/adapters/settings";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { lookupPattern, retentionFrom } from "@/lib/domain/settings";

export type SaveRetentionResult =
  { ok: true; months: number | null; affected: number } | { ok: false };

/** Saves the organisation's retention period (T102); set_retention records who changed it. */
export async function saveRetention(choice: string): Promise<SaveRetentionResult> {
  const months = retentionFrom(choice);
  if (months === undefined) return { ok: false };
  const supabase = await createSupabaseServerClient();
  if ((await readAccess(supabase)).kind !== "member") return { ok: false };
  try {
    return { ok: true, months, affected: await setRetention(supabase, months) };
  } catch {
    return { ok: false };
  }
}

/** Candidates a deletion request might be about, by email, phone or name (T102). */
export async function lookUpCandidates(query: string): Promise<CandidateMatch[]> {
  const pattern = lookupPattern(query);
  if (pattern === null) return [];
  const supabase = await createSupabaseServerClient();
  if ((await readAccess(supabase)).kind !== "member") return [];
  return findCandidates(supabase, pattern);
}
