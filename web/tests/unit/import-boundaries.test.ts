import path from "node:path";

import { ESLint } from "eslint";
import tseslint from "typescript-eslint";
import { describe, expect, it } from "vitest";

// Constitution II: dependencies point inward. These run the real eslint.config.mjs against
// virtual files, so type-aware rules are switched off: the files have no type information.
const eslint = new ESLint({
  cwd: path.resolve(import.meta.dirname, "../.."),
  overrideConfig: tseslint.configs.disableTypeChecked,
});

async function boundaryViolations(filePath: string, specifier: string): Promise<number> {
  const source = `import { thing } from "${specifier}";\nexport const used = thing;\n`;
  const [result] = await eslint.lintText(source, { filePath });
  return result?.messages.filter((m) => m.ruleId === "no-restricted-imports").length ?? 0;
}

describe("domain", () => {
  it.each([
    "@/lib/adapters/session",
    "../adapters/session",
    "@/components/score-breakdown",
    "../../components/score-breakdown",
    "@/app/[lang]/layout",
    "next/navigation",
    "react",
    "@supabase/supabase-js",
    "@anthropic-ai/sdk",
    "openai",
  ])("may not import %s", async (specifier) => {
    expect(await boundaryViolations("lib/domain/ranking.ts", specifier)).toBe(1);
  });

  it.each(["./ranking-rules", "@/lib/domain/ranking-rules", "@/lib/ports/queue-message"])(
    "may import %s",
    async (specifier) => {
      expect(await boundaryViolations("lib/domain/ranking.ts", specifier)).toBe(0);
    },
  );
});

describe("ports", () => {
  it.each(["@/lib/adapters/session", "../adapters/session"])(
    "may not import %s",
    async (specifier) => {
      expect(await boundaryViolations("lib/ports/queue-message.ts", specifier)).toBe(1);
    },
  );
});

describe("adapters", () => {
  it.each(["@/lib/domain/ranking", "@/lib/ports/queue-message", "@supabase/supabase-js"])(
    "may import %s",
    async (specifier) => {
      expect(await boundaryViolations("lib/adapters/session.ts", specifier)).toBe(0);
    },
  );
});
