"use server";

import { hasLocale } from "next-intl";

import { redirect } from "@/i18n/navigation";
import { type Locale, routing } from "@/i18n/routing";
import { readAccess } from "@/lib/adapters/session";
import { createSupabaseServerClient } from "@/lib/adapters/supabase";
import { DEFAULT_WEIGHTS, type DraftErrors, jobDraftFrom } from "@/lib/domain/job-draft";

export interface CreateJobState {
  readonly errors?: DraftErrors;
  /** The job could not be saved for a reason the form cannot fix. */
  readonly failed?: boolean;
}

// The locale is bound on the server, but an action is still an endpoint: check it anyway.
function checked(locale: string): Locale {
  if (!hasLocale(routing.locales, locale)) throw new Error("Unknown locale");
  return locale;
}

/**
 * Saves a job (T059, FR-001). The organisation is the session's, never the form's; row level
 * security checks it again. A new job starts with the default weights (FR-014), which a later
 * phase lets recruiters change (FR-025).
 */
export async function createJob(
  locale: Locale,
  _previous: CreateJobState,
  form: FormData,
): Promise<CreateJobState> {
  const lang = checked(locale);
  const result = jobDraftFrom(form);
  if (!result.ok) return { errors: result.errors };

  const supabase = await createSupabaseServerClient();
  const access = await readAccess(supabase);
  if (access.kind !== "member") return redirect({ href: "/sign-in", locale: lang });

  const { draft } = result;
  const { error } = await supabase.from("job").insert({
    organisation_id: access.session.organisationId,
    title: draft.title,
    description: draft.description,
    required_skills: draft.requiredSkills,
    preferred_skills: draft.preferredSkills,
    minimum_experience_years: draft.minimumExperienceYears,
    location: draft.location,
    language_requirement: draft.languageRequirement,
    weights: DEFAULT_WEIGHTS,
  });
  if (error) return { failed: true };
  // The job's own page, where CVs are dropped, arrives with T063; until then the list shows it.
  return redirect({ href: "/jobs", locale: lang });
}

export type Proposal = { readonly kind: "unavailable" };

/**
 * Turns a pasted description into a specification to review (FR-002). The model call behind it
 * is T060 (POST /api/jobs/{jobId}/specification), so that the browser never reaches a model
 * provider. Until it lands, and takes the pasted text, the form says a proposal is unavailable
 * and keeps what was pasted.
 */
export async function proposeSpecification(locale: Locale): Promise<Proposal> {
  checked(locale);
  return Promise.resolve({ kind: "unavailable" });
}
