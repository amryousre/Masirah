import { describe, expect, it, vi } from "vitest";

import { accessFor } from "@/lib/adapters/session";

// next/headers only exists inside a request; the decision under test does not need it.
vi.mock("next/headers", () => ({ cookies: vi.fn() }));

const membership = { organisation_id: "org-1", organisation: { name: "Delta Soft" } };

describe("access from the session (T024)", () => {
  it("is signed out without verified claims", () => {
    expect(accessFor(null, null)).toEqual({ kind: "signed-out" });
    expect(accessFor(null, membership)).toEqual({ kind: "signed-out" });
  });

  it("has no organisation when the user has no app_user row", () => {
    expect(accessFor({ sub: "user-1", email: "a@example.com" }, null)).toEqual({
      kind: "no-organisation",
    });
  });

  it("takes the organisation from the membership row, not from anything the client sent", () => {
    const access = accessFor(
      { sub: "user-1", email: "a@example.com", user_metadata: { full_name: " Nourhan Saeed " } },
      membership,
    );
    expect(access).toEqual({
      kind: "member",
      session: {
        userId: "user-1",
        email: "a@example.com",
        name: "Nourhan Saeed",
        organisationId: "org-1",
        organisationName: "Delta Soft",
      },
    });
  });

  it("falls back to the provider's name field, and to none", () => {
    const named = accessFor({ sub: "u", user_metadata: { name: "Karim" } }, membership);
    expect(named.kind === "member" && named.session.name).toBe("Karim");
    const unnamed = accessFor(
      { sub: "u", user_metadata: { full_name: "  ", name: 7 } },
      membership,
    );
    expect(unnamed.kind === "member" && unnamed.session.name).toBeNull();
  });
});
