import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { beforeAll, describe, expect, it, vi } from "vitest";

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

// Each case runs the real ESLint, whose first run in a busy suite takes longer than 5 seconds.
vi.setConfig({ testTimeout: 30_000 });

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

// DESIGN.md motion and T108: every motion takes a duration token, which globals.css sets to zero
// for reduced motion, so a module cannot move outside 150-250 ms or keep moving when asked not to.
describe("motion", () => {
  const css = "components/example.module.css";

  it.each([
    ["a written-out transition time", ".a { transition: color 400ms ease; }\n"],
    ["a written-out animation time", ".a { animation: enter 1s ease; }\n"],
    ["a transition delay", ".a { transition-delay: var(--duration-fast); }\n"],
    [
      "a delay in a shorthand",
      ".a { transition: color var(--duration-fast) var(--ease) var(--duration-fast); }\n",
    ],
    ["a staggered animation", ".a { animation-delay: 200ms; }\n"],
    ["an endless animation", ".a { animation: pulse var(--duration-base) var(--ease) infinite; }\n"],
    ["a repeated animation", ".a { animation-iteration-count: 3; }\n"],
    ["motion on a pseudo-element", ".a::after { transition: opacity 600ms; }\n"],
  ])("rejects %s", async (_, code) => {
    expect(await rulesBroken(css, code)).toContain("masirah/motion-tokens");
  });

  it("accepts motion that takes the duration tokens", async () => {
    const code =
      ".a { transition: color var(--duration-fast) var(--ease), border-color var(--duration-slow) var(--ease); animation: enter var(--duration-base) var(--ease); }\n";
    expect(await rulesBroken(css, code)).toEqual([]);
  });

  it("accepts motion turned off", async () => {
    expect(await rulesBroken(css, ".a { transition: none; animation: none 0s; }\n")).toEqual([]);
  });
});
