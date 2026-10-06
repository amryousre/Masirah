import { expect, test } from "@playwright/test";

import {
  type Account,
  activityAbout,
  addJob,
  addRankedCandidate,
  correctionsOf,
  createAccount,
  extractAgain,
  setExtraction,
  userIdOf,
} from "./support/accounts";
import { expectAccessible, signIn, untilHydrated } from "./support/pages";

// Correcting a wrongly extracted field (T075, T082, T083, FR-010). The recruiter opens a doubtful
// CV from the review queue, corrects what was misread, and the candidate's page then shows the
// corrected value as corrected, with what was read, and keeps it when the CV is read again.

test.describe.configure({ mode: "serial" });

const EXTRACTED = {
  name: "Mona Abdalla",
  emails: ["mona@example.com"],
  phones: ["+201000000101"],
  location: "Cairo",
  years_of_experience: null,
  employment: [{ title: "Accountant", employer: "Nile Pharma", start: "2019-03", end: "present" }],
  education: [],
  skills: ["Excel"],
  languages: [],
  certifications: [],
};

let recruiter: Account;
let stranger: Account;
let job: string;
let mona: string;
let file: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  job = await addJob(recruiter, { title: "Senior Accountant" });
  mona = await addRankedCandidate(recruiter, job, {
    name: "Mona Abdalla",
    total: 70,
    justification: "Five years of accounts.",
    confidence: 0.6,
  });
  file = await setExtraction(mona, EXTRACTED, "low_confidence");
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
});

test("a misread name and a missing skill are corrected from the review queue", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/review?file=${file}`);
  await page.getByRole("link", { name: "Correct the details" }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: "Correct Mona Abdalla’s details" }),
  ).toBeVisible();
  await expectAccessible(page);

  await page.getByLabel("Name", { exact: true }).fill("Mona Abdallah");
  await page.getByLabel("Skills").fill("Excel\nSAP");
  await page.getByRole("button", { name: "Save corrections" }).click();
  await expect(page).toHaveURL(new RegExp(`/en/review\\?file=${file}$`));

  const kept = await correctionsOf(file);
  expect(kept).toEqual({
    name: { value: "Mona Abdallah", by: await userIdOf(recruiter), at: expect.any(String) },
    skills: { value: ["Excel", "SAP"], by: await userIdOf(recruiter), at: expect.any(String) },
  });
  const recorded = (await activityAbout(mona)).filter(
    (row) => row.action === "candidate.corrected",
  );
  expect(recorded).toEqual([
    expect.objectContaining({ metadata: { cv_file_id: file, fields: ["name", "skills"] } }),
  ]);
});

test("the candidate's page shows the corrected value as corrected, with what was read", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${mona}`);
  await untilHydrated(page, async () => {
    await page.getByRole("tab", { name: "Extracted profile" }).click();
    await expect(page.getByText(/Read from the CV: \u2068Mona Abdalla\u2069/)).toBeVisible({
      timeout: 1_000,
    });
  });
  await expect(page.getByText("Corrected", { exact: true })).toHaveCount(2);
  await expect(page.getByText(/Read from the CV: \u2068Excel\u2069/)).toBeVisible();
  await expect(page.getByText(recruiter.email).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Correct details" })).toBeVisible();
});

test("reading the CV again keeps the correction", async ({ page }) => {
  await extractAgain(file, { ...EXTRACTED, location: "Giza" });
  expect(Object.keys(await correctionsOf(file)).sort()).toEqual(["name", "skills"]);
  await signIn(page, recruiter);
  await page.goto(`/en/candidates/${mona}/edit?file=${file}&job=${job}`);
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue("Mona Abdallah");
  await expect(page.getByLabel("City")).toHaveValue("Giza");
});

test("a value that cannot be right is named and nothing is saved", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/candidates/${mona}/edit?file=${file}&job=${job}`);
  await untilHydrated(page, async () => {
    await page.getByLabel("Email addresses").fill("mona at example");
    await page.getByRole("button", { name: "Save corrections" }).click();
    await expect(
      page.getByRole("alert").filter({ hasText: "Some fields need fixing" }),
    ).toBeVisible({
      timeout: 2_000,
    });
  });
  await expect(page.getByText(/each needs a name, an @ and a domain/)).toBeVisible();
  expect(Object.keys(await correctionsOf(file)).sort()).toEqual(["name", "skills"]);
});

test("a job is added and removed as a whole entry", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/candidates/${mona}/edit?file=${file}&job=${job}`);
  const work = page.getByRole("group", { name: "Work experience" });
  // Added once only: a retry before hydration must not add a second row.
  await untilHydrated(page, async () => {
    if ((await work.getByText(/^Entry \d+$/).count()) < 2) {
      await work.getByRole("button", { name: "Add a job" }).click();
    }
    await expect(work.getByText("Entry 2", { exact: true })).toBeVisible({ timeout: 1_000 });
  });
  await work.getByLabel("Job title").nth(1).fill("Junior Accountant");
  await work.getByLabel("Employer").nth(1).fill("Delta Trading");
  await work.getByLabel("From").nth(1).fill("2017");
  await work.getByLabel("To").nth(1).fill("2019");
  await page.getByRole("button", { name: "Save corrections" }).click();
  await expect(page).toHaveURL(new RegExp(`/en/jobs/${job}/candidates/${mona}$`));
  const kept = await correctionsOf(file);
  expect((kept["employment"] as { value: unknown }).value).toEqual([
    { title: "Accountant", employer: "Nile Pharma", start: "2019-03", end: "present" },
    { title: "Junior Accountant", employer: "Delta Trading", start: "2017", end: "2019" },
  ]);
});

test("in Arabic the form is right to left and a current job reads حتى الآن", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/ar/candidates/${mona}/edit?file=${file}&job=${job}`);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByLabel("إلى").first()).toHaveValue("حتى الآن");
  await expectAccessible(page);
});

test("another organisation cannot open the correction page", async ({ page }) => {
  await signIn(page, stranger);
  const response = await page.goto(`/en/candidates/${mona}/edit?file=${file}`);
  expect(response?.status()).toBe(404);
});
