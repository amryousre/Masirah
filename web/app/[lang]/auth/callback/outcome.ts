/**
 * What Supabase Auth's return to /{lang}/auth/callback means. Sign-ups are closed, so a Google
 * account nobody invited comes back with error_code=signup_disabled, before any user exists.
 */
export type CallbackOutcome =
  | { readonly kind: "code"; readonly code: string }
  | { readonly kind: "not-invited" }
  | { readonly kind: "failed" };

export function callbackOutcome(query: URLSearchParams): CallbackOutcome {
  if (query.get("error_code") === "signup_disabled") return { kind: "not-invited" };
  const code = query.get("code");
  // Anything else without a code, such as the person cancelling at Google, is a sign-in that
  // did not finish.
  if (query.has("error") || code === null || code === "") return { kind: "failed" };
  return { kind: "code", code };
}
