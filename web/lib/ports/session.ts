/**
 * Who is signed in, and to which organisation every query they make is scoped (T024). The
 * organisation comes from the session and never from a request body: a client-supplied
 * organisation identifier is ignored (contracts/web-routes.md).
 */
export interface Session {
  readonly userId: string;
  readonly email: string;
  /** The name the identity provider gave, when it gave one. Password accounts have none. */
  readonly name: string | null;
  readonly organisationId: string;
  readonly organisationName: string;
}

/**
 * Signing in is not the same as having access. Sign-ups are closed, so an unknown Google account
 * never gets a user; but a user can exist without an organisation, for example after its
 * organisation was removed, and that user sees the no-access page rather than an empty app.
 */
export type Access =
  | { readonly kind: "signed-out" }
  | { readonly kind: "no-organisation" }
  | { readonly kind: "member"; readonly session: Session };
