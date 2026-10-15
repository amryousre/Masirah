import { describe, expect, it } from "vitest";

import { waitlistEmail } from "@/lib/domain/waitlist";

// The landing page's waitlist takes a work email and nothing else. The form checks it before it
// goes to public.join_waitlist (migration 0027), which checks it again: the page answers in its own
// language, the database refuses whatever slips past.

describe("waitlistEmail", () => {
  it("trims and lowercases an address", () => {
    expect(waitlistEmail("  Nourhan@Delta-Soft.com ")).toBe("nourhan@delta-soft.com");
  });

  it.each(["", "   ", "not an email", "nourhan@", "@delta-soft.com", "nourhan@delta", "a b@c.com"])(
    "refuses %j",
    (raw) => {
      expect(waitlistEmail(raw)).toBeNull();
    },
  );

  it("refuses an address longer than an address can be", () => {
    expect(waitlistEmail(`${"a".repeat(250)}@delta-soft.com`)).toBeNull();
  });
});
