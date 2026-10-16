// @vitest-environment jsdom
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { docxToSafeHtml } from "@/components/document-pane/docx-html";

// A Word CV shown beside its extraction (T067, FR-012). Word cannot be displayed by the browser,
// so the file is converted to HTML in the recruiter's browser and cleaned before it is shown: a
// CV is written by someone outside the company, so nothing in it may run, and no link in it may
// lead anywhere. Each block finds its own direction, since one CV mixes Arabic and English.

function fixture(): ArrayBuffer {
  // From the project root: under jsdom, import.meta.url is not a file URL.
  const bytes = readFileSync(path.join(process.cwd(), "tests/fixtures/syn-cv.docx"));
  // Copied into the test window's own ArrayBuffer, as a browser's fetch would give one.
  const file = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(file).set(bytes);
  return file;
}

const OPTIONS = { pictureAlt: "A picture in the CV" };

function rendered(html: string): HTMLElement {
  const host = document.createElement("div");
  host.innerHTML = html;
  return host;
}

describe("docxToSafeHtml", () => {
  it("keeps the CV's headings, paragraphs and lists", async () => {
    const page = rendered(await docxToSafeHtml(fixture(), OPTIONS));
    expect(page.querySelector("h1")?.textContent).toBe("سارة نبيل");
    expect(page.querySelector("h2")?.textContent).toBe("Experience");
    expect(page.querySelector("li")?.textContent).toBe("Prepared the quarterly IFRS reports.");
    expect(page.textContent).toContain("Senior Accountant, Delta Soft, 2019 to 2026");
  });

  it("lets every block find its own direction", async () => {
    const page = rendered(await docxToSafeHtml(fixture(), OPTIONS));
    const blocks = [...page.querySelectorAll("h1, h2, p, li")];
    expect(blocks.length).toBeGreaterThan(0);
    for (const block of blocks) expect(block.getAttribute("dir")).toBe("auto");
  });

  it("keeps a link's words and drops where it leads", async () => {
    const page = rendered(await docxToSafeHtml(fixture(), OPTIONS));
    expect(page.querySelector("a")).toBeNull();
    expect(page.textContent).toContain("my work");
    expect(page.innerHTML).not.toContain("javascript:");
  });

  it("keeps a table, each cell finding its own direction", async () => {
    const page = rendered(await docxToSafeHtml(fixture(), OPTIONS));
    const cells = [...page.querySelectorAll("td")].map((cell) => cell.textContent);
    expect(cells).toEqual(["اللغة", "Level", "English", "Fluent"]);
    for (const cell of page.querySelectorAll("td")) expect(cell.getAttribute("dir")).toBe("auto");
  });

  it("shows an embedded picture, described when the CV does not describe it", async () => {
    const [picture, ...others] = rendered(
      await docxToSafeHtml(fixture(), OPTIONS),
    ).querySelectorAll("img");
    expect(picture?.getAttribute("src")).toMatch(/^data:image\/png;base64,/);
    expect(picture?.getAttribute("alt")).toBe("A picture in the CV");
    // The fixture's second picture is a TIFF, a format the preview does not show.
    expect(others).toHaveLength(0);
  });

  it("refuses a file that is not a Word document", async () => {
    await expect(
      docxToSafeHtml(new TextEncoder().encode("not a docx").buffer, OPTIONS),
    ).rejects.toThrow();
  });
});
