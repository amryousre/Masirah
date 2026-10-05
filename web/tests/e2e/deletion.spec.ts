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

// Removing a candidate's personal data on request (T101, FR-076). The member asks on the
// candidate's page, after a confirmation that says what goes and what stays; the request is
// recorded with who made it, and the worker removes the data on its next sweep.

let recruiter: Account;
let stranger: Account;
let job: string;
let yasmin: string;
let omar: string;
let strangersCandidate: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  job = await addJob(recruiter, { title: "Senior Accountant" });
  yasmin = await addRankedCandidate(recruiter, job, {
    name: "Yasmin Farouk",
    total: 86,
    justification: "Six years at Nile Pharma.",
    confidence: 0.95,
  });
  omar = await addRankedCandidate(recruiter, job, {
    name: "Omar Hassan",
    total: 61,
    justification: "Strong TypeScript.",
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

test("a member asks for a candidate's data to be removed, after being told what goes", async ({
  page,
}) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  const open = page.getByRole("button", { name: "Remove personal data…" });
  const dialog = page.getByRole("dialog", { name: "Remove Yasmin Farouk’s personal data?" });
  await untilHydrated(page, async () => {
    await open.click();
    await expect(dialog).toBeVisible({ timeout: 1_000 });
  });
  await expect(dialog).toContainText("name, contact details, CV and extracted profile");
  await expect(dialog).toContainText("Scores and decisions stay");
  await expectAccessible(page);
  await dialog.getByRole("button", { name: "Remove personal data" }).click();

  await expect(page.getByText(/^Removal requested/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Remove personal data…" })).toHaveCount(0);
  const requested = (await activityAbout(yasmin)).filter(
    (row) => row.action === "candidate.deletion_requested",
  );
  expect(requested).toEqual([
    expect.objectContaining({ actor_id: await userIdOf(recruiter), subject_type: "candidate" }),
  ]);
});

test("keeping the candidate records nothing", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${omar}`);
  const open = page.getByRole("button", { name: "Remove personal data…" });
  const dialog = page.getByRole("dialog", { name: "Remove Omar Hassan’s personal data?" });
  await untilHydrated(page, async () => {
    await open.click();
    await expect(dialog).toBeVisible({ timeout: 1_000 });
  });
  await dialog.getByRole("button", { name: "Keep the data" }).click();
  await expect(dialog).toBeHidden();
  const requested = (await activityAbout(omar)).filter(
    (row) => row.action === "candidate.deletion_requested",
  );
  expect(requested).toEqual([]);
});

test.describe("the deletion API", () => {
  test("asking twice keeps the first request", async ({ page }) => {
    await signIn(page, recruiter);
    const first = await page.request.delete(`/api/candidates/${omar}`);
    expect(first.status()).toBe(202);
    const again = await page.request.delete(`/api/candidates/${omar}`);
    expect(again.status()).toBe(202);
    expect(await again.json()).toEqual(await first.json());
  });

  test("does not find another organisation's candidate", async ({ page }) => {
    await signIn(page, recruiter);
    const response = await page.request.delete(`/api/candidates/${strangersCandidate}`);
    expect(response.status()).toBe(404);
  });

  test("refuses a request without a signed-in member", async ({ request }) => {
    const response = await request.delete(`/api/candidates/${yasmin}`);
    expect(response.status()).toBe(401);
  });
});
