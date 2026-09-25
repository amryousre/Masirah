import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { beforeAll, describe, expect, it } from "vitest";

// DESIGN.md section 2: one token file, one component library, enforced by lint. These tests run
// the real ESLint configuration, so a guard that stops firing fails here rather than silently.

let eslint: ESLint;

beforeAll(() => {
  // The snippets are not files in the TypeScript project, so they are linted without type
  // information. None of the guards under test need it.
  eslint = new ESLint({
    cwd: process.cwd(),
    overrideConfig: { files: ["**/*.{ts,tsx}"], ...tseslint.configs.disableTypeChecked },
  });
}, 120_000);

async function rulesBroken(filePath: string, code: string): Promise<(string | null)[]> {
  const [result] = await eslint.lintText(code, { filePath });
  return result?.messages.map((message) => message.ruleId) ?? [];
}

describe("CSS outside the token file", () => {
  const css = "components/example.module.css";

  it("rejects physical left and right", async () => {
    expect(await rulesBroken(css, ".a { margin-left: 4px; }\n")).toContain(
      "css/prefer-logical-properties",
    );
    expect(await rulesBroken(css, ".a { text-align: left; }\n")).toContain(
      "css/prefer-logical-properties",
    );
  });

  it.each([
    ["a hex color", ".a { color: #fff; }\n"],
    ["an oklch color", ".a { color: oklch(0.55 0.122 65); }\n"],
    ["an rgb color", ".a { background: rgb(0 0 0 / 50%); }\n"],
    ["a named color", ".a { border-color: white; }\n"],
  ])("rejects %s", async (_, code) => {
    expect(await rulesBroken(css, code)).toContain("masirah/no-raw-color");
  });

  it("rejects pixel font sizes", async () => {
    expect(await rulesBroken(css, ".a { font-size: 14px; }\n")).toContain(
      "css/relative-font-units",
    );
  });

  it("accepts tokens and logical properties", async () => {
    const code =
      ".a { color: var(--color-text); margin-inline-start: var(--space-2); background: transparent; }\n";
    expect(await rulesBroken(css, code)).toEqual([]);
  });
});

describe("the token file", () => {
  it("may define raw colors", async () => {
    const code = ":root { --grey-0: oklch(1 0 0); }\n";
    expect(await rulesBroken("app/globals.css", code)).toEqual([]);
  });
});

describe("components and screens", () => {
  const tsx = "components/example.tsx";

  it("reject text written into the markup", async () => {
    const code = "export function A() {\n  return <p>Reject candidate</p>;\n}\n";
    expect(await rulesBroken(tsx, code)).toContain("react/jsx-no-literals");
  });

  it("reject hard-coded accessible names", async () => {
    const code = 'export function A() {\n  return <button aria-label="Close" />;\n}\n';
    expect(await rulesBroken(tsx, code)).toContain("no-restricted-syntax");
  });

  it("reject raw colors in code", async () => {
    const code = 'export const accent = "oklch(0.55 0.122 65)";\n';
    expect(await rulesBroken(tsx, code)).toContain("no-restricted-syntax");
  });

  it("reject inline styles other than custom properties", async () => {
    const code = "export function A() {\n  return <div style={{ marginLeft: 4 }} />;\n}\n";
    expect(await rulesBroken(tsx, code)).toContain("no-restricted-syntax");
  });

  it("accept inline custom properties", async () => {
    const code = 'export function A() {\n  return <div style={{ "--fill": "40%" }} />;\n}\n';
    expect(await rulesBroken(tsx, code)).toEqual([]);
  });
});
