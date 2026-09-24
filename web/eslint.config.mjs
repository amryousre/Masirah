import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";
import tseslint from "typescript-eslint";

// Constitution II: dependencies point inward. Adapters may import domain and ports; never the reverse.
const noAdapters = {
  regex: "(^|/)adapters(/|$)",
  message:
    "Domain and ports may not depend on adapters (Constitution II). Depend on a port instead.",
};

// no-restricted-imports cannot see import(), and its specifier can be computed, so the inner
// layers may not use one at all. Pure domain logic has no reason to load code lazily.
const noDynamicImport = {
  selector: "ImportExpression",
  message: "Domain and ports may not use dynamic import() (Constitution II).",
};

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  ...tseslint.configs.strictTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    rules: {
      "@next/next/no-html-link-for-pages": "off",
    },
  },
  {
    files: ["lib/domain/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            noAdapters,
            {
              regex: String.raw`^(@/|(\.\./)+)(app|components)(/|$)`,
              message: "Domain may not depend on the interface layer (Constitution II).",
            },
            {
              regex: "^(next|react|react-dom)(/|$)",
              message: "Domain may not import framework code (Constitution II).",
            },
            {
              regex: "^(@supabase/|@anthropic-ai/|openai(/|$))",
              message:
                "Domain may not import database or model-provider code (Constitution II). Depend on a port instead.",
            },
          ],
        },
      ],
      "no-restricted-syntax": ["error", noDynamicImport],
    },
  },
  {
    files: ["lib/ports/**/*.{ts,tsx}"],
    rules: {
      "no-restricted-imports": ["error", { patterns: [noAdapters] }],
      "no-restricted-syntax": ["error", noDynamicImport],
    },
  },
  {
    files: ["**/*.{js,mjs,cjs}"],
    extends: [tseslint.configs.disableTypeChecked],
  },
  prettier,
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "coverage/**",
    "test-results/**",
    "playwright-report/**",
    "next-env.d.ts",
  ]),
]);
