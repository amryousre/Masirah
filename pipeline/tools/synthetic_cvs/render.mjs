// Prints every synthetic CV in this folder to PDF with Chromium, as a browser's "Save as PDF" or a
// web CV builder would. Playwright comes from web/, which already installs it for end-to-end tests.
//
//   node pipeline/tools/synthetic_cvs/render.mjs <output folder>
//
// The output is raw: tools.build_synthetic_cvs strips its metadata before it enters the corpus.
// The sources name Windows fonts (Simplified Arabic, Sakkal Majalla, Tahoma, Calibri), so a render
// elsewhere falls back to other fonts and differs from the committed PDFs.
import { mkdirSync, readdirSync } from "node:fs";
import { createRequire } from "node:module";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const output = process.argv[2];
if (!output) {
  console.error("usage: node render.mjs <output folder>");
  process.exit(2);
}
mkdirSync(output, { recursive: true });

const require = createRequire(resolve(here, "../../../web/package.json"));
const { chromium } = require("playwright");

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  for (const file of readdirSync(here).filter((name) => name.endsWith(".html")).sort()) {
    await page.goto(pathToFileURL(join(here, file)).href, { waitUntil: "load" });
    const pdf = join(output, `${basename(file, ".html")}.pdf`);
    await page.pdf({ path: pdf, preferCSSPageSize: true, printBackground: true });
    console.log(pdf);
  }
} finally {
  await browser.close();
}
