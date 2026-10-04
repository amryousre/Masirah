import { expect, test } from "@playwright/test";

import { type Account, addJob, addRankedCandidate, createAccount } from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// A candidate's own page (T065, T066): reached from the ranked list, the written reasons lead,
// the summary and the score's breakdown follow, and the extracted profile is a tab away.

let recruiter: Account;
let stranger: Account;
let job: string;
let otherJob: string;
let yasmin: string;
let omar: string;
let strangersCandidate: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  job = await addJob(recruiter, { title: "Senior Accountant" });
  otherJob = await addJob(recruiter, { title: "HR Coordinator" });
  yasmin = await addRankedCandidate(recruiter, job, {
    name: "Yasmin Farouk",
    total: 86,
    justification: "Six years at Nile Pharma on month-end close. SAP daily.",
    confidence: 0.95,
    ratings: {
      skills_match: 90,
      experience_relevance: 80,
      education: 100,
      tenure_stability: 80,
      language: 100,
      location: 60,
    },
  });
  omar = await addRankedCandidate(recruiter, job, {
    name: "Omar Hassan",
    total: 74,
    justification: "Strong TypeScript. Three jobs in four years.",
    confidence: 0.92,
  });
  const elsewhere = await addJob(stranger, { title: "Someone Else's Job" });
  strangersCandidate = await addRankedCandidate(stranger, elsewhere, {
    name: "Hidden Person",
    total: 50,
    justification: "Not yours.",
    confidence: 0.9,
  });
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
});

test("a name in the ranked list opens the candidate, reasons first", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}`);
  await page.getByRole("link", { name: "Yasmin Farouk" }).click();
  await expect(page).toHaveURL(new RegExp(`/en/jobs/${job}/candidates/${yasmin}$`));
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Yasmin Farouk");
  await expect(page.getByText("Rank 1 of 2 · Score 86 · High confidence")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why rank 1" })).toBeVisible();
  await expect(
    page.getByText("Six years at Nile Pharma on month-end close. SAP daily."),
  ).toBeVisible();
  await expect(page.getByRole("listitem").filter({ hasText: "SAP daily." })).toBeVisible();
  await expectAccessible(page);
});

test("the breakdown shows points earned out of each weight, with its evidence", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  const breakdown = page.getByRole("region", { name: "Reasons" });
  await expect(breakdown.getByText("27 / 30")).toBeVisible();
  await expect(breakdown.getByText("skills_match evidence")).toBeVisible();
  await expect(breakdown.getByText("6 / 10", { exact: true })).toBeVisible();
});

test("a score whose components cannot be read says so instead of inventing points", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${omar}`);
  await expect(page.getByText("The breakdown could not be read for this score.")).toBeVisible();
});

test("the next candidate is one step away, and the last has none after it", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  await page.getByRole("link", { name: "Next candidate" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Omar Hassan");
  await expect(page.getByRole("link", { name: "Next candidate" })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Previous candidate" })).toBeVisible();
});

test("the extracted profile is the second tab, and a missing field says so", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  await page.getByRole("tab", { name: "Extracted profile" }).click();
  await expect(page.getByRole("definition").filter({ hasText: "Yasmin Farouk" })).toBeVisible();
  await expect(page.getByText("Not in the CV").first()).toBeVisible();
  await expectAccessible(page);
});

test("the page reads in Arabic, right to left", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/ar/jobs/${job}/candidates/${yasmin}`);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { name: "لماذا المرتبة 1" })).toBeVisible();
  await expectAccessible(page);
});

test("on a phone the panes are tabs, reasons first", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  const views = page.getByRole("tablist", { name: "Candidate views" });
  await expect(views.getByRole("tab")).toHaveText(["Reasons", "Extracted profile", "Document"]);
  await expect(views.getByRole("tab", { name: "Reasons" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("heading", { name: "Why rank 1" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Original document" })).toBeHidden();

  await views.getByRole("tab", { name: "Document" }).click();
  await expect(page.getByRole("region", { name: "Original document" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why rank 1" })).toBeHidden();
  await expectAccessible(page);
});

test("on a laptop both panes show and there are no view tabs", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  await expect(page.getByRole("tablist", { name: "Candidate views" })).toBeHidden();
  await expect(page.getByRole("region", { name: "Original document" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Why rank 1" })).toBeVisible();
});

test("another organisation's candidate is not found", async ({ page }) => {
  await signIn(page, recruiter);
  const response = await page.goto(`/en/jobs/${job}/candidates/${strangersCandidate}`);
  expect(response?.status()).toBe(404);
});

test("a candidate who never applied to the job is not found there", async ({ page }) => {
  await signIn(page, recruiter);
  const response = await page.goto(`/en/jobs/${otherJob}/candidates/${yasmin}`);
  expect(response?.status()).toBe(404);
});
