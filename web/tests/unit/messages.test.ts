import { describe, expect, it } from "vitest";

import ar from "@/messages/ar.json";
import en from "@/messages/en.json";

// Constitution IV: every user-visible string lives in a translation file. Arabic is the original,
// so English must say the same things: the same keys and the same placeholders in each message.

type Tree = { [key: string]: string | Tree };

function flatten(tree: Tree, prefix = ""): Map<string, string> {
  const entries = new Map<string, string>();
  for (const [key, value] of Object.entries(tree)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") {
      entries.set(path, value);
    } else {
      for (const [inner, text] of flatten(value, path)) entries.set(inner, text);
    }
  }
  return entries;
}

// ICU arguments: {name}, {count, plural, ...}. The words inside a plural branch differ by
// language, and so does the number of branches; the set of argument names must not.
function argumentsOf(message: string): string[] {
  const names = [...message.matchAll(/\{\s*([A-Za-z_]\w*)\s*[,}]/g)].map((match) => match[1] ?? "");
  return [...new Set(names)].sort();
}

const arabic = flatten(ar);
const english = flatten(en);

describe("translation files", () => {
  it("have the same keys", () => {
    expect([...english.keys()].sort()).toEqual([...arabic.keys()].sort());
  });

  it("use the same arguments in every message", () => {
    const mismatched = [...arabic].filter(
      ([key, text]) =>
        JSON.stringify(argumentsOf(text)) !== JSON.stringify(argumentsOf(english.get(key) ?? "")),
    );
    expect(mismatched.map(([key]) => key)).toEqual([]);
  });

  it("have no empty messages", () => {
    const empty = [...arabic, ...english].filter(([, text]) => text.trim() === "");
    expect(empty.map(([key]) => key)).toEqual([]);
  });

  it("count with named arguments, never #, so numbers stay in Western digits", () => {
    // Inside a plural, # is formatted with the locale's digits: Arabic-Indic in Arabic. The
    // interface uses Western digits in both languages (DESIGN.md section 4).
    const pound = [...arabic, ...english].filter(
      ([, text]) => text.includes("plural,") && text.includes("#"),
    );
    expect(pound.map(([key]) => key)).toEqual([]);
  });

  it("never use an em dash, per the product's copy rules", () => {
    const dashed = [...arabic, ...english].filter(([, text]) => text.includes("—"));
    expect(dashed.map(([key]) => key)).toEqual([]);
  });
});

// The product's voice (design-brief.md section 8, PRODUCT.md): specific rather than aphoristic. It
// names what happened and why; it never congratulates the user, never celebrates a finished batch,
// and never calls the output intelligent.
describe("the voice", () => {
  const all = [...arabic, ...english];

  it("never exclaims", () => {
    expect(all.filter(([, text]) => /[!¡]/.test(text)).map(([key]) => key)).toEqual([]);
  });

  it("never congratulates, celebrates or calls the output clever", () => {
    const praise =
      /\b(congratulations|congrats|great job|well done|awesome|amazing|hooray|smart|intelligent|magic(al)?)\b|مبروك|تهانينا|أحسنت|رائع|مذهل|ذكي|ذكية|سحري/i;
    expect(all.filter(([, text]) => praise.test(text)).map(([key]) => key)).toEqual([]);
  });

  // Every action is labelled with a verb and its object, so a control says what it acts on
  // (DESIGN.md section 7). A bare verb such as "Remove" or "Close" does not.
  it.each([
    "dialog.close",
    "upload.remove",
    "upload.cancel",
    "upload.hide",
    "upload.review",
    "upload.replace",
    "upload.ignore",
    "upload.openProfile",
    "toast.dismiss",
    "job.addCvs",
    "job.clearFilters",
    "reject.keep",
  ])("labels %s with a verb and its object in both languages", (key) => {
    for (const messages of [arabic, english]) {
      const label = messages.get(key) ?? "";
      expect(label.trim().split(/\s+/).length, `${key}: "${label}"`).toBeGreaterThanOrEqual(2);
    }
  });
});
