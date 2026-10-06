"use server";

import { hasLocale } from "next-intl";

import { redirect } from "@/i18n/navigation";
import { type Locale, routing } from "@/i18n/routing";
import { readCorrectionTarget, saveCorrections } from "@/lib/adapters/corrections";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import {
  type CorrectionError,
  correctionsFromForm,
  type ProfileKey,
} from "@/lib/domain/corrections";
import { nameNormalised } from "@/lib/domain/names";

const ID = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}";
/** The only places the page sends a member back to: the candidate in a job, or the queue. */
const RETURNS = new RegExp(String.raw`^/(review\?file=${ID}|jobs/${ID}/candidates/${ID})$`, "i");

export type CorrectionState =
  | { status: "idle" }
  | { status: "invalid"; errors: Partial<Record<ProfileKey, CorrectionError>> }
  | { status: "failed" };

export interface CorrectionContext {
  lang: Locale;
  candidateId: string;
  fileId: string;
  /** Where the member returns to, decided by the page from its own route. */
  back: string;
}

/**
 * Saves a member's corrections of a candidate's profile (T082, FR-010). Only the fields the form
 * changed are sent, and correct_profile keeps them beside the extraction with the member's name.
 */
export async function correctProfile(
  context: CorrectionContext,
  _previous: CorrectionState,
  form: FormData,
): Promise<CorrectionState> {
  // Bound by the page, but sent back by the browser: the return path must be one the page makes.
  if (!hasLocale(routing.locales, context.lang) || !RETURNS.test(context.back)) {
    return { status: "failed" };
  }
  const supabase = await createSupabaseServerClient();
  if ((await readAccess(supabase)).kind !== "member") return { status: "failed" };
  const target = await readCorrectionTarget(supabase, context.candidateId, context.fileId).catch(
    () => null,
  );
  if (target === null) return { status: "failed" };

  const submitted = [...form.entries()].flatMap(([key, value]) =>
    typeof value === "string" ? [[key, value] as [string, string]] : [],
  );
  const result = correctionsFromForm(submitted, target.profile, target.corrections);
  if (!result.ok) return { status: "invalid", errors: result.errors };

  if (Object.keys(result.corrections).length > 0) {
    const name = result.corrections.name;
    const folded =
      "name" in result.corrections ? nameNormalised(typeof name === "string" ? name : "") : null;
    try {
      await saveCorrections(supabase, target.file.id, result.corrections, folded);
    } catch {
      return { status: "failed" };
    }
  }
  return redirect({ href: context.back, locale: context.lang });
}
