import { randomUUID } from "node:crypto";

import { createClient } from "@supabase/supabase-js";

import type { Database } from "@/lib/adapters/database.types";

// Accounts for the sign-in tests, made the way the operator makes them while sign-ups are closed:
// through the admin API, with the email already confirmed. The secret key is read by the test
// runner only; the app under test never reads it.

function admin() {
  const url = process.env["NEXT_PUBLIC_SUPABASE_URL"];
  const key = process.env["SUPABASE_SECRET_KEY"];
  if (!url || !key) {
    throw new Error(
      "The sign-in tests need NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SECRET_KEY from `supabase status`.",
    );
  }
  return createClient<Database>(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export interface Account {
  email: string;
  password: string;
  organisation: string | null;
  organisationId: string | null;
  remove: () => Promise<void>;
}

/**
 * A user with a password, in a new organisation unless `organisation` is null, in which case the
 * user belongs to none: the case the no-access page covers for an existing account.
 */
export async function createAccount(organisation: string | null): Promise<Account> {
  const client = admin();
  const email = `e2e-${randomUUID()}@example.test`;
  const password = randomUUID();

  const { data: created, error } = await client.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });
  if (error) throw error;
  const userId = created.user.id;

  let organisationId: string | null = null;
  const remove = async () => {
    // Deleting the user removes its app_user row with it.
    await client.auth.admin.deleteUser(userId);
    if (organisationId !== null) {
      // CV files, their stored originals and jobs hang off the organisation, so they go first.
      const { data: files } = await client
        .from("cv_file")
        .select("storage_path")
        .eq("organisation_id", organisationId);
      if (files && files.length > 0) {
        await client.storage.from("cv-originals").remove(files.map((file) => file.storage_path));
      }
      // Scores, applications, profiles and candidates hang off files and jobs; they go first.
      for (const table of ["score", "application", "parsed_profile"] as const) {
        await client.from(table).delete().eq("organisation_id", organisationId);
      }
      await client.from("cv_file").delete().eq("organisation_id", organisationId);
      await client.from("candidate").delete().eq("organisation_id", organisationId);
      await client.from("job").delete().eq("organisation_id", organisationId);
      await client.from("organisation").delete().eq("id", organisationId);
    }
  };

  if (organisation !== null) {
    try {
      const { data: row, error: orgError } = await client
        .from("organisation")
        .insert({ name: organisation, locale: "ar" })
        .select("id")
        .single();
      if (orgError) throw orgError;
      organisationId = row.id;
      const { error: memberError } = await client
        .from("app_user")
        .insert({ id: userId, organisation_id: organisationId, email });
      if (memberError) throw memberError;
    } catch (failure) {
      // A half-made account would outlive the run; take back what was made, then report why.
      await remove();
      throw failure;
    }
  }

  return { email, password, organisation, organisationId, remove };
}

const WEIGHTS = {
  skills_match: 30,
  experience_relevance: 25,
  education: 15,
  tenure_stability: 10,
  language: 10,
  location: 10,
};

/** A job in the account's organisation, made as the web application will make it (T059). */
export async function addJob(
  account: Account,
  job: { title: string; location?: string; minimumExperienceYears?: number },
): Promise<string> {
  if (account.organisationId === null) throw new Error("The account belongs to no organisation.");
  const { data, error } = await admin()
    .from("job")
    .insert({
      organisation_id: account.organisationId,
      title: job.title,
      location: job.location ?? null,
      minimum_experience_years: job.minimumExperienceYears ?? null,
      weights: WEIGHTS,
    })
    .select("id")
    .single();
  if (error) throw error;
  return data.id;
}

/**
 * A candidate already read and scored for a job, as the worker leaves one: a candidate, their
 * extracted CV file with its current profile, an application to the job and a score.
 */
export async function addRankedCandidate(
  account: Account,
  jobId: string,
  candidate: {
    name: string;
    total: number;
    justification: string;
    confidence: number;
    /** Ratings out of 100 by component; empty unless the test reads the breakdown. */
    ratings?: Record<keyof typeof WEIGHTS, number>;
  },
): Promise<string> {
  const organisationId = account.organisationId;
  if (organisationId === null) throw new Error("The account belongs to no organisation.");
  const client = admin();
  const fail = (error: { message: string } | null) => {
    if (error) throw new Error(error.message);
  };

  const person = await client
    .from("candidate")
    .insert({ organisation_id: organisationId, full_name: candidate.name })
    .select("id")
    .single();
  if (person.error) throw new Error(person.error.message);

  const fileId = randomUUID();
  fail(
    (
      await client.from("cv_file").insert({
        id: fileId,
        organisation_id: organisationId,
        candidate_id: person.data.id,
        job_id: jobId,
        storage_path: `organisations/${organisationId}/cv/${fileId}/cv.pdf`,
        original_filename: `${candidate.name}.pdf`,
        mime_type: "application/pdf",
        byte_size: 1024,
        content_hash: randomUUID().replaceAll("-", "").repeat(2),
        status: "extracted",
      })
    ).error,
  );
  fail(
    (
      await client.from("parsed_profile").insert({
        organisation_id: organisationId,
        cv_file_id: fileId,
        version: 1,
        is_current: true,
        extraction_source: "native_text",
        confidence: candidate.confidence,
        profile: { name: candidate.name },
      })
    ).error,
  );

  const application = await client
    .from("application")
    .insert({ organisation_id: organisationId, candidate_id: person.data.id, job_id: jobId })
    .select("id")
    .single();
  if (application.error) throw new Error(application.error.message);

  fail(
    (
      await client.from("score").insert({
        organisation_id: organisationId,
        application_id: application.data.id,
        total: candidate.total,
        components: Object.fromEntries(
          Object.entries(candidate.ratings ?? {}).map(([name, rating]) => [
            name,
            { rating, evidence: `${name} evidence` },
          ]),
        ),
        justification: candidate.justification,
        summary: ["Six years in finance.", "SAP daily."].join("\n"),
        model_id: "test-model",
        provider: "anthropic",
        prompt_version: "test",
        input_hash: "a".repeat(64),
        weights_hash: "b".repeat(64),
        cost_egp: 0,
      })
    ).error,
  );
  return person.data.id;
}

/**
 * Another CV for a candidate already in the organisation, uploaded for a job and applied with:
 * the candidate who sends a second CV for a second job.
 */
export async function addCvFile(
  account: Account,
  candidateId: string,
  jobId: string,
  fileName: string,
): Promise<void> {
  const organisationId = account.organisationId;
  if (organisationId === null) throw new Error("The account belongs to no organisation.");
  const client = admin();
  const fileId = randomUUID();
  const file = await client.from("cv_file").insert({
    id: fileId,
    organisation_id: organisationId,
    candidate_id: candidateId,
    job_id: jobId,
    storage_path: `organisations/${organisationId}/cv/${fileId}/cv.pdf`,
    original_filename: fileName,
    mime_type: "application/pdf",
    byte_size: 1024,
    content_hash: randomUUID().replaceAll("-", "").repeat(2),
    status: "extracted",
  });
  if (file.error) throw new Error(file.error.message);
  const profile = await client.from("parsed_profile").insert({
    organisation_id: organisationId,
    cv_file_id: fileId,
    version: 1,
    is_current: true,
    extraction_source: "native_text",
    confidence: 0.95,
    profile: { name: fileName },
  });
  if (profile.error) throw new Error(profile.error.message);
  const application = await client
    .from("application")
    .insert({ organisation_id: organisationId, candidate_id: candidateId, job_id: jobId });
  if (application.error) throw new Error(application.error.message);
}
