import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import {
  type Account,
  activityAbout,
  addFileInReview,
  addJob,
  createAccount,
  userIdOf,
} from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// The review queue (T081, FR-011): every CV that was not ranked is listed with its reason in plain
// words and its original beside it. A badly scanned document and a CV in an unsupported language
// must read differently, because they ask the recruiter for different things.

const CORPUS = path.resolve(import.meta.dirname, "../../../pipeline/tests/fixtures/cvs");

let recruiter: Account;
let stranger: Account;
let empty: Account;
let scan: string;
let french: string;
let hidden: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  empty = await createAccount("Quiet Ltd");
  const job = await addJob(recruiter, { title: "Senior Accountant" });
  scan = await addFileInReview(recruiter, {
    fileName: "scan_0187.pdf",
    jobId: job,
    status: "needs_review",
    reviewReason: "no_text",
    pdf: readFileSync(path.join(CORPUS, "en-scanned-01.pdf")),
  });
  french = await addFileInReview(recruiter, {
    fileName: "CV_Dupont.pdf",
    jobId: job,
    status: "needs_review",
    reviewReason: "unsupported_language",
    reviewLanguage: "fr",
    pdf: readFileSync(path.join(CORPUS, "syn-fr-native-01.pdf")),
  });
  await addFileInReview(recruiter, {
    fileName: "CV_final_v3.pdf",
    status: "failed",
    failureReason: "the file cannot be read: the PDF is password-protected",
  });
  hidden = await addFileInReview(stranger, {
    fileName: "not-yours.pdf",
    status: "needs_review",
    reviewReason: "no_text",
  });
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
  await empty.remove();
});

test("every file not ranked is listed with its reason, and the queue's link counts them", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto("/en/review");
  await expect(page.getByRole("heading", { level: 1, name: "Review queue" })).toBeVisible();
  await expect(page.getByText("3 files were not ranked.")).toBeVisible();
  const list = page.getByRole("navigation", { name: "Files waiting for review" });
  await expect(list.getByRole("link")).toHaveCount(3);
  await expect(list.getByRole("link", { name: /scan_0187\.pdf/ })).toContainText(
    "No text could be read from this file.",
  );
  await expect(list.getByRole("link", { name: /CV_Dupont\.pdf/ })).toContainText(
    "Written in French, which Masirah doesn’t read.",
  );
  await expect(list.getByRole("link", { name: /CV_final_v3\.pdf/ })).toContainText(
    "The file is protected by a password.",
  );
  await expect(list.getByText("not-yours.pdf")).toHaveCount(0);
  await expect(
    page
      .getByRole("navigation", { name: "Main navigation" })
      .getByRole("link", { name: /Review queue/ }),
  ).toContainText("3");
  await expectAccessible(page);
});

test("a chosen file shows what helps and its original, and the view is recorded", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/review?file=${french}`);
  const detail = page.getByRole("region", { name: "CV_Dupont.pdf" });
  await expect(detail).toContainText("Masirah reads CVs in Arabic and English.");
  await expect(detail).toContainText(
    "Read it yourself, or ask the candidate for a CV in Arabic or English.",
  );
  await expect(detail.getByRole("link", { name: "Open Senior Accountant" })).toBeVisible();
  await expect(page.locator(`iframe[title="CV_Dupont.pdf"]`)).toBeVisible();
  // Headless Chromium draws no PDF, so the link the viewer opens is fetched instead.
  const preview = await page.locator(`iframe[title="CV_Dupont.pdf"]`).getAttribute("src");
  const shown = await page.request.get((preview ?? "").split("#")[0] ?? "");
  expect([shown.status(), shown.headers()["content-type"]]).toEqual([200, "application/pdf"]);
  const viewed = (await activityAbout(french)).filter((row) => row.action === "cv_file.viewed");
  expect(viewed).toEqual([
    expect.objectContaining({ actor_id: await userIdOf(recruiter), subject_type: "cv_file" }),
  ]);
});

test("a scan and a CV in another language never read alike", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/review?file=${scan}`);
  const detail = page.getByRole("region", { name: "scan_0187.pdf" });
  await expect(detail).toContainText("Nothing in it could be read as text.");
  await expect(detail).toContainText("Needs review");
  await expect(detail).not.toContainText("Unsupported language");
});

test("the original downloads through the audit trail, and another organisation's does not", async ({
  page,
}) => {
  await signIn(page, recruiter);
  const own = await page.request.get(`/api/cv-files/${scan}/original`, { maxRedirects: 0 });
  expect(own.status()).toBe(302);
  const exported = (await activityAbout(scan)).filter((row) => row.action === "cv_file.exported");
  expect(exported).toHaveLength(1);
  const theirs = await page.request.get(`/api/cv-files/${hidden}/original`, { maxRedirects: 0 });
  expect(theirs.status()).toBe(404);
});

test("in Arabic the language is named in Arabic", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/ar/review?file=${french}`);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("region", { name: "CV_Dupont.pdf" })).toContainText(
    "مكتوبة باللغة الفرنسية",
  );
  await expectAccessible(page);
});

test("on a phone the list and the chosen file take turns", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await signIn(page, recruiter);
  await page.goto("/en/review");
  const list = page.getByRole("navigation", { name: "Files waiting for review" });
  await expect(list).toBeVisible();
  await list.getByRole("link", { name: /CV_final_v3\.pdf/ }).click();
  await expect(page.getByRole("region", { name: "CV_final_v3.pdf" })).toContainText(
    "Ask the candidate for a copy without a password.",
  );
  await expect(list).toBeHidden();
  await page.getByRole("link", { name: "All files" }).click();
  await expect(list).toBeVisible();
  const scrolls = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(scrolls).toBe(false);
});

test("with nothing waiting, the page says what would appear here", async ({ page }) => {
  await signIn(page, empty);
  await page.goto("/en/review");
  await expect(page.getByRole("heading", { name: "Nothing is waiting for review" })).toBeVisible();
  await expect(page.getByText(/so none is ever lost/)).toBeVisible();
});
