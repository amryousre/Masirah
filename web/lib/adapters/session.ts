import { cache } from "react";

import type { Access } from "@/lib/ports/session";

import { createSupabaseServerClient, type SupabaseClient } from "./supabase";

interface Claims {
  sub: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
}

interface Membership {
  organisation_id: string;
  organisation: { name: string };
}

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value.trim() : null;
}

/** Decides access from verified token claims and the user's app_user row, if any. */
export function accessFor(claims: Claims | null, membership: Membership | null): Access {
  if (!claims) return { kind: "signed-out" };
  if (!membership) return { kind: "no-organisation" };
  const metadata = claims.user_metadata ?? {};
  return {
    kind: "member",
    session: {
      userId: claims.sub,
      email: claims.email ?? "",
      name: text(metadata["full_name"]) ?? text(metadata["name"]),
      organisationId: membership.organisation_id,
      organisationName: membership.organisation.name,
    },
  };
}

/**
 * Resolves the organisation from the session (T024). getClaims verifies the access token rather
 * than trusting the cookie, and the app_user row is read under row level security, so the
 * organisation is whichever one the database says this user belongs to.
 */
export async function readAccess(supabase: SupabaseClient): Promise<Access> {
  const { data } = await supabase.auth.getClaims();
  if (!data) return accessFor(null, null);
  const { data: membership, error } = await supabase
    .from("app_user")
    .select("organisation_id, organisation(name)")
    .eq("id", data.claims.sub)
    .maybeSingle();
  // A failed query is an outage, not a missing organisation, so it must not show the
  // no-access page.
  if (error) throw error;
  return accessFor(data.claims, membership);
}

/** The current request's access, read once however many components ask. */
export const getAccess = cache(async (): Promise<Access> => {
  return readAccess(await createSupabaseServerClient());
});
