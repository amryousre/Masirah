import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { type Account, addJob, addRankedCandidate, createAccount } from "./support/accounts";
import { expectAccessible, signIn, untilHydrated } from "./support/pages";

// A job's own page (T062, T063): ranked candidates in order with the reason for each, files still
// on their way listed below, and CVs added by dropping them on the page, which navigates nowhere.

const CORPUS = path.resolve(import.meta.dirname, "../../../pipeline/tests/fixtures/cvs");

let recruiter: Account;
let stranger: Account;
let rankedJob: string;
let emptyJob: string;
let brokenJob: string;
let strangersJob: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  rankedJob = await addJob(recruiter, { title: "Senior Accountant", location: "Giza" });
  emptyJob = await addJob(recruiter, { title: "HR Coordinator" });
  strangersJob = await addJob(stranger, { title: "Someone Else's Job" });
  brokenJob = await addJob(recruiter, { title: "Payroll Officer" });
  for (const [name, total] of [
    ["Nadia Samir", 90],
    ["Karim Fathy", 88],
    ["Laila Mostafa", 86],
    ["Sherif Adel", 60],
    ["Dina Wahba", 58],
  ] as const) {
    await addRankedCandidate(recruiter, brokenJob, {
      name,
      total,
      justification: "Payroll in Cairo.",
      confidence: 0.95,
    });
  }
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

test("a second batch dropped while the first is sending keeps both in view", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${emptyJob}`);
  // Hold the first request until the second batch has been dropped, so the two overlap.
  let releaseFirst = () => {};
  const firstHeld = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  let requests = 0;
  await page.route("**/api/uploads", async (route) => {
    requests += 1;
    if (requests === 1) await firstHeld;
    await route.continue();
  });
  const input = page.getByTestId("drop-zone").locator("input[type=file]");
  const cv = readFileSync(path.join(CORPUS, "en-native-01.pdf"));
  await input.setInputFiles({ name: "First batch.pdf", mimeType: "application/pdf", buffer: cv });
  await input.setInputFiles({ name: "Second batch.pdf", mimeType: "application/pdf", buffer: cv });
  await expect(page.getByRole("listitem").filter({ hasText: "Second batch.pdf" })).toContainText(
    "Processing",
  );
  releaseFirst();
  await expect(page.getByRole("listitem").filter({ hasText: "First batch.pdf" })).toContainText(
    "Processing",
  );
  await expect(page.getByRole("listitem").filter({ hasText: "Second batch.pdf" })).toContainText(
    "Processing",
  );
});

test("the ranking marks where the scores fall off", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${brokenJob}`);
  const rows = page.getByRole("table", { name: "Candidates ranked by score" }).locator("tbody tr");
  await expect(rows.nth(2)).toContainText("Laila Mostafa");
  await expect(rows.nth(3)).toHaveText("Scores drop 26 points below here");
  await expect(rows.nth(4)).toContainText("Sherif Adel");
  await expectAccessible(page);
});

test("a ranking without a break carries no marker", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${rankedJob}`);
  await expect(page.getByRole("table", { name: "Candidates ranked by score" })).toBeVisible();
  await expect(page.getByText(/Scores drop/)).toHaveCount(0);
});

test("search finds a name however it is spelled, and the address keeps it", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${rankedJob}`);
  // A change made before the page hydrates is lost, so the first one is repeated until it lands.
  await untilHydrated(page, async () => {
    await page.getByRole("searchbox", { name: "Search candidates" }).fill("Yasmine");
    await expect(page).toHaveURL(/\?q=Yasmine$/, { timeout: 1_000 });
  });
  const table = page.getByRole("table", { name: "Candidates ranked by score" });
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(table).toContainText("Yasmin Farouk");
  await expect(page.getByRole("status").filter({ hasText: "Showing" })).toHaveText(
    "Showing 1 of 2",
  );
  await expect(page).toHaveURL(/\?q=Yasmine$/);
  await page.reload();
  await expect(page.getByRole("searchbox", { name: "Search candidates" })).toHaveValue("Yasmine");
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expectAccessible(page);
});

test("filters keep only what needs review, and an empty result can be cleared", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${rankedJob}`);
  await untilHydrated(page, async () => {
    await page.getByRole("checkbox", { name: "Needs review only" }).setChecked(false);
    await page.getByRole("checkbox", { name: "Needs review only" }).check();
    await expect(page).toHaveURL(/\?review=1$/, { timeout: 1_000 });
  });
  const table = page.getByRole("table", { name: "Candidates ranked by score" });
  await expect(table.locator("tbody tr")).toHaveCount(1);
  await expect(table).toContainText("Yasmin Farouk");

  await page.getByRole("searchbox", { name: "Search candidates" }).fill("Omar");
  await expect(page.getByText("Search covers names", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Clear search and filters" }).click();
  await expect(table.locator("tbody tr")).toHaveCount(2);
  await expect(page).toHaveURL(new RegExp(`/en/jobs/${rankedJob}$`));
});

test("sorting by name keeps each candidate's rank by score", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${rankedJob}`);
  await untilHydrated(page, async () => {
    await page.getByRole("combobox", { name: "Sort by" }).selectOption("score");
    await page.getByRole("combobox", { name: "Sort by" }).selectOption("name");
    await expect(page).toHaveURL(/\?sort=name$/, { timeout: 1_000 });
  });
  const rows = page.getByRole("table", { name: "Candidates ranked by score" }).locator("tbody tr");
  await expect(rows.nth(0)).toContainText("Omar Hassan");
  await expect(rows.nth(0).locator("td").first()).toHaveText("2");
  await expect(page.getByRole("columnheader", { name: "Candidate" })).toHaveAttribute(
    "aria-sort",
    "ascending",
  );
});

test("the language switch opens the same job in the other language", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/ar/jobs/${rankedJob}`);
  await page.getByRole("link", { name: "English" }).click();
  await expect(page).toHaveURL(new RegExp(`/en/jobs/${rankedJob}$`));
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Senior Accountant");
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
