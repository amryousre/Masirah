import { expect, test } from "@playwright/test";

import { type Account, addJob, createAccount } from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// The job list (T058) for a signed-in member: an empty state that teaches how a ranking comes
// about, then one row per job of their own organisation and none of anyone else's.

let newcomer: Account;
let recruiter: Account;
let stranger: Account;
const made: Account[] = [];

test.beforeAll(async () => {
  newcomer = await createAccount("Newcomer Co");
  made.push(newcomer);
  recruiter = await createAccount("Delta Soft");
  made.push(recruiter);
  stranger = await createAccount("Elsewhere Ltd");
  made.push(stranger);
  await addJob(recruiter, {
    title: "Senior Accountant",
    location: "Giza",
    minimumExperienceYears: 5,
  });
  await addJob(recruiter, { title: "HR Coordinator" });
  await addJob(stranger, { title: "Someone Else's Job" });
});

test.afterAll(async () => {
  for (const account of made) await account.remove();
});

test("a member with no jobs is shown how a ranking starts", async ({ page }) => {
  await signIn(page, newcomer);
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("No jobs yet");
  await expect(page.getByRole("main").getByRole("listitem")).toHaveCount(3);
  await expect(page.getByRole("link", { name: "Create job" })).toHaveAttribute(
    "href",
    "/en/jobs/new",
  );
  await expect(page.getByRole("link", { name: "Paste a job description" })).toHaveAttribute(
    "href",
    "/en/jobs/new?start=paste",
  );
  await expectAccessible(page);
});

test("the empty state reads in Arabic, right to left", async ({ page }) => {
  await signIn(page, newcomer);
  await page.goto("/ar/jobs");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 2 })).toHaveText("لا توجد وظائف بعد");
  await expectAccessible(page);
});

test("a recruiter's jobs are listed, and only theirs", async ({ page }) => {
  await signIn(page, recruiter);
  const table = page.getByRole("table", { name: "Your jobs, most recently active first" });
  await expect(table.getByRole("row")).toHaveCount(3);
  const accountant = table.getByRole("row", { name: /Senior Accountant/ });
  await expect(accountant).toContainText("Giza · 5+ years");
  await expect(accountant).toContainText("No CVs yet");
  await expect(accountant).toContainText("Drop files onto the job to start ranking");
  await expect(table).not.toContainText("Someone Else's Job");
  await expectAccessible(page);
  await accountant.getByRole("link", { name: "Senior Accountant" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Senior Accountant");
});

test("the list reads in Arabic, right to left", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/ar/jobs");
  const table = page.getByRole("table", { name: "وظائفك، الأحدث نشاطًا أولًا" });
  await expect(table.getByRole("row", { name: /Senior Accountant/ })).toContainText("5+ سنوات");
  await expectAccessible(page);
});

test("on a phone the list never scrolls sideways, and keeps each job's update time", async ({
  page,
}) => {
  await page.setViewportSize({ width: 360, height: 760 });
  await signIn(page, recruiter);
  await expect(page.locator("time").first()).toBeVisible();
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
});
