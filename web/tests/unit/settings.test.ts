import { describe, expect, it } from "vitest";

import { lookupPattern, RETENTION_CHOICES, retentionFrom } from "@/lib/domain/settings";

// The settings page (T102): the retention periods it offers, and the text it searches candidates
// by when one asks for their data to be deleted.

describe("retentionFrom", () => {
  it("reads the offered periods, and never", () => {
    expect(RETENTION_CHOICES).toEqual(["6", "12", "24", "never"]);
    expect(retentionFrom("6")).toBe(6);
    expect(retentionFrom("24")).toBe(24);
    expect(retentionFrom("never")).toBeNull();
  });

  it("refuses anything else", () => {
    for (const value of ["3", "", "12.5", "forever", "-6"]) {
      expect(retentionFrom(value)).toBeUndefined();
    }
  });
});

describe("lookupPattern", () => {
  it("keeps what identifies a person: an email, a phone, a name in either script", () => {
    expect(lookupPattern("  mohamed.abdallah@gmail.com ")).toBe("mohamed.abdallah@gmail.com");
    expect(lookupPattern("+20 100 555 2841")).toBe("+20 100 555 2841");
    expect(lookupPattern("محمد عبد الله")).toBe("محمد عبد الله");
  });

  it("drops the characters a database filter would read as its own syntax", () => {
    expect(lookupPattern("mona%,name.eq.x)(")).toBe("monaname.eq.x");
    expect(lookupPattern("a_b*c\\d")).toBe("abcd");
  });

  it("asks for at least two characters, so one letter does not list everyone", () => {
    expect(lookupPattern("m")).toBeNull();
    expect(lookupPattern("  ")).toBeNull();
    expect(lookupPattern("%%")).toBeNull();
  });
});
