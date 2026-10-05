import { expect, test } from "@playwright/test";

import {
  type Account,
  activityAbout,
  addJob,
  addRankedCandidate,
  createAccount,
  userIdOf,
} from "./support/accounts";
import { expectAccessible, signIn, untilHydrated } from "./support/pages";

// The settings page (T102): the interface language, the organisation's retention period, and
// deleting a candidate's data when they ask, found by email, phone or name.

let recruiter: Account;
let stranger: Account;
let mona: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  const job = await addJob(recruiter, { title: "Senior Accountant" });
  mona = await addRankedCandidate(recruiter, job, {
    name: "Mona Abdallah",
    total: 70,
    justification: "Payroll.",
    confidence: 0.95,
  });
  const elsewhere = await addJob(stranger, { title: "Someone Else's Job" });
  await addRankedCandidate(stranger, elsewhere, {
    name: "Mona Hidden",
    total: 50,
    justification: "Not yours.",
    confidence: 0.9,
  });
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
});

test("the page lays out the three settings and reads in both languages", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/settings");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Settings");
  for (const name of ["Interface language", "Data retention", "Delete a candidate’s data"]) {
    await expect(page.getByRole("region", { name })).toBeVisible();
  }
  await expectAccessible(page);
  await page.goto("/ar/settings");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expectAccessible(page);
});

test("choosing a language opens the settings in it", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/settings");
  await untilHydrated(page, async () => {
    await page.getByRole("radio", { name: "العربية" }).check();
    await expect(page).toHaveURL(/\/ar\/settings$/, { timeout: 2_000 });
  });
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("الإعدادات");
});

test("saving a retention period records who changed it", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/settings");
  const retention = page.getByRole("combobox", {
    name: "Delete candidate data automatically after",
  });
  await expect(retention).toHaveValue("24");
  await untilHydrated(page, async () => {
    await retention.selectOption("12");
    await expect(page.getByText(/12 months after their last activity/)).toBeVisible({
      timeout: 1_000,
    });
  });
  await page.getByRole("button", { name: "Save retention period" }).click();
  await expect(page.getByText("Retention period saved.", { exact: false })).toBeVisible();
  await expect(page.getByText("Nobody is deleted immediately by this change.")).toBeVisible();

  const changes = (await activityAbout(recruiter.organisationId ?? "")).filter(
    (row) => row.action === "organisation.retention_changed",
  );
  expect(changes.at(-1)).toMatchObject({
    actor_id: await userIdOf(recruiter),
    metadata: { from: 24, to: 12 },
  });
  await page.reload();
  await expect(retention).toHaveValue("12");
});

test("a candidate found by name has their data deleted on request", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/settings");
  const search = page.getByRole("searchbox", { name: "Email, phone or name" });
  await untilHydrated(page, async () => {
    await search.fill("");
    await search.fill("Mona");
    await expect(page.getByRole("list", { name: "Candidates found" })).toBeVisible({
      timeout: 2_000,
    });
  });
  const found = page.getByRole("list", { name: "Candidates found" }).getByRole("button");
  await expect(found).toHaveCount(1);
  await expect(found).toContainText("Mona Abdallah");
  await found.click();

  const deletion = page.getByRole("region", { name: "Delete a candidate’s data" });
  await expect(deletion).toContainText("Deleted permanently");
  await expect(deletion).toContainText("Kept in the audit trail");
  await deletion.getByRole("button", { name: "Delete candidate data…" }).click();
  const dialog = page.getByRole("dialog", { name: "Delete Mona Abdallah’s data?" });
  await dialog.getByRole("button", { name: "Delete data permanently" }).click();
  await expect(
    page.getByText("Mona Abdallah’s data will be deleted within the hour.", { exact: false }),
  ).toBeVisible();

  const requested = (await activityAbout(mona)).filter(
    (row) => row.action === "candidate.deletion_requested",
  );
  expect(requested).toHaveLength(1);
});
