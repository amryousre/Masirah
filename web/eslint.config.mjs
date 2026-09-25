import css from "@eslint/css";
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import prettier from "eslint-config-prettier/flat";
import tseslint from "typescript-eslint";

import masirah from "./eslint/no-raw-color.mjs";

const code = ["**/*.{js,mjs,cjs,ts,tsx}"];

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

// DESIGN.md section 2 and Constitution IV: interface code takes its words from the translation
// files, its colors from the tokens and its styles from CSS modules.
const colorValue = String.raw`/#[0-9a-f]{3,8}\b|\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/i`;
const interfaceRules = [
  {
    selector:
      "JSXAttribute[name.name=/^(aria-label|aria-description|aria-placeholder|aria-roledescription|aria-valuetext|alt|title|placeholder)$/] > Literal",
    message: "Accessible names and hints come from the translation files (Constitution IV).",
  },
  {
    selector: `Literal[value=${colorValue}], TemplateElement[value.raw=${colorValue}]`,
    message: "Colors come from the tokens in app/globals.css (DESIGN.md section 2).",
  },
  {
    selector:
      "JSXAttribute[name.name='style'] ObjectExpression > Property > Identifier.key, JSXAttribute[name.name='style'] ObjectExpression > Property > Literal.key[value=/^(?!--)/]",
    message:
      "Inline styles may only set custom properties (--name); styling belongs in the CSS module (DESIGN.md section 2).",
  },
];

export default defineConfig([
  {
    files: code,
    extends: [...nextVitals, ...nextTs, ...tseslint.configs.strictTypeChecked],
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
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
              regex: "^(next|next-intl|react|react-dom)(/|$)",
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
    files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}"],
    rules: {
      "react/jsx-no-literals": [
        "error",
        { noStrings: true, ignoreProps: true, allowedStrings: ["·", "/", "(", ")", ":", "%"] },
      ],
      "no-restricted-syntax": ["error", ...interfaceRules],
    },
  },
  {
    files: ["**/*.{js,mjs,cjs}"],
    extends: [tseslint.configs.disableTypeChecked],
  },
  {
    files: code,
    extends: [prettier],
  },
  {
    files: ["**/*.css"],
    language: "css/css",
    plugins: { css, masirah },
    extends: ["css/recommended"],
    rules: {
      // Tokens are defined in app/globals.css, which a CSS module cannot see.
      "css/no-invalid-properties": ["error", { allowUnknownVariables: true }],
      "css/prefer-logical-properties": "error",
      "css/relative-font-units": "error",
      // Widely available features only, except these progressive enhancements: where a browser
      // lacks them the text still wraps, the scrollbar still shows, selection still works and a
      // checkbox keeps its default color.
      "css/use-baseline": [
        "error",
        {
          allowProperties: ["text-wrap", "scrollbar-width", "accent-color"],
          allowSelectors: ["selection"],
        },
      ],
      "masirah/no-raw-color": "error",
    },
  },
  {
    // The token file is where colors are defined, so it is the one place they may be written.
    files: ["app/globals.css"],
    rules: { "masirah/no-raw-color": "off" },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "coverage/**",
    "test-results/**",
    "playwright-report/**",
    "next-env.d.ts",
    // Generated from the database schema by the Supabase CLI.
    "lib/adapters/database.types.ts",
  ]),
]);
