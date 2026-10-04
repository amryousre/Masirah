import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { type Account, addJob, addRankedCandidate, createAccount } from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// A job's own page (T062, T063): ranked candidates in order with the reason for each, files still
// on their way listed below, and CVs added by dropping them on the page, which navigates nowhere.

const CORPUS = path.resolve(import.meta.dirname, "../../../pipeline/tests/fixtures/cvs");

let recruiter: Account;
let stranger: Account;
let rankedJob: string;
let emptyJob: string;
let strangersJob: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  rankedJob = await addJob(recruiter, { title: "Senior Accountant", location: "Giza" });
  emptyJob = await addJob(recruiter, { title: "HR Coordinator" });
  strangersJob = await addJob(stranger, { title: "Someone Else's Job" });
  await addRankedCandidate(recruiter, rankedJob, {
    name: "Omar Hassan",
    total: 74,
    justification: "Strong TypeScript. Three jobs in four years.",
    confidence: 0.92,
  });
  await addRankedCandidate(recruiter, rankedJob, {
    name: "Yasmin Farouk",
    total: 86,
    justification: "Six years at Nile Pharma on month-end close. SAP daily.",
    confidence: 0.7,
  });
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
});

test("candidates are ranked by score, each with the first sentence of its reason", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${rankedJob}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Senior Accountant");
  const table = page.getByRole("table", { name: "Candidates ranked by score" });
  const rows = table.locator("tbody tr");
  await expect(rows.nth(0)).toContainText("Yasmin Farouk");
  await expect(rows.nth(0)).toContainText("Six years at Nile Pharma on month-end close.");
  await expect(rows.nth(0)).not.toContainText("SAP daily");
  await expect(rows.nth(1)).toContainText("Omar Hassan");
  await expectAccessible(page);
});

test("a ranked candidate read with low confidence is marked for review", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${rankedJob}`);
  const yasmin = page.getByRole("row", { name: /Yasmin Farouk/ });
  await expect(yasmin).toContainText("Low confidence");
});

test("dropping CVs adds them without leaving the page", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${emptyJob}`);
  await expect(page.getByText(/No CVs yet/)).toBeVisible();
  await page
    .getByTestId("drop-zone")
    .locator("input[type=file]")
    .setInputFiles({
      name: "Mona Abdallah CV.pdf",
      mimeType: "application/pdf",
      buffer: readFileSync(path.join(CORPUS, "en-native-01.pdf")),
    });
  await expect(page).toHaveURL(new RegExp(`/en/jobs/${emptyJob}$`));
  const table = page.getByRole("table", { name: "Candidates ranked by score" });
  await expect(table).toContainText("Not ranked yet");
  await expect(table.getByRole("row", { name: /Mona Abdallah CV\.pdf/ })).toContainText(
    "Processing",
  );
});

test("the page reads in Arabic, right to left", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/ar/jobs/${rankedJob}`);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Senior Accountant");
  await expectAccessible(page);
});

test("another organisation's job is not found", async ({ page }) => {
  await signIn(page, recruiter);
  const response = await page.goto(`/en/jobs/${strangersJob}`);
  expect(response?.status()).toBe(404);
});

test("an address that is not a job is not found", async ({ page }) => {
  await signIn(page, recruiter);
  const response = await page.goto("/en/jobs/not-a-job");
  expect(response?.status()).toBe(404);
});
