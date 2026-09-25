import { describe, expect, it } from "vitest";

import { callbackOutcome } from "@/app/[lang]/auth/callback/outcome";

// What each return from Supabase Auth to /{lang}/auth/callback leads to (T024).
const outcome = (query: string) => callbackOutcome(new URLSearchParams(query));

describe("the sign-in callback", () => {
  it("exchanges a code for a session", () => {
    expect(outcome("code=abc123")).toEqual({ kind: "code", code: "abc123" });
  });

  it("treats a refused sign-up as an account nobody invited", () => {
    expect(
      outcome(
        "error=access_denied&error_code=signup_disabled&error_description=Signups+not+allowed",
      ),
    ).toEqual({ kind: "not-invited" });
  });

  it("treats a cancelled or broken sign-in as one that did not finish", () => {
    expect(outcome("error=access_denied")).toEqual({ kind: "failed" });
    expect(outcome("error=server_error&error_code=unexpected_failure")).toEqual({
      kind: "failed",
    });
    expect(outcome("")).toEqual({ kind: "failed" });
    expect(outcome("code=")).toEqual({ kind: "failed" });
  });

  it("does not exchange a code that arrives with an error", () => {
    expect(outcome("code=abc123&error=access_denied")).toEqual({ kind: "failed" });
  });
});
