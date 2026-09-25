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

  return { email, password, organisation, remove };
}
