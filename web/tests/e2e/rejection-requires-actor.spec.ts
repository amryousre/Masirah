import { expect, test } from "@playwright/test";

import {
  type Account,
  addJob,
  addRankedCandidate,
  applicationOf,
  createAccount,
  storedDecision,
  userIdOf,
} from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// No path sets a decision without recording who made it (T087, T090 to T092, FR-023). Through the
// interface or straight at the API, the decider is the signed-in member, a rejection needs a
// reason, and every decision leaves an audit row.

let recruiter: Account;
let stranger: Account;
let job: string;
let yasmin: string;
let omar: string;
let strangersApplication: string;

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
  const hidden = await addRankedCandidate(stranger, elsewhere, {
    name: "Hidden Person",
    total: 50,
    justification: "Not yours.",
    confidence: 0.9,
  });
  strangersApplication = await applicationOf(hidden, elsewhere);
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
});

test("shortlisting records the member who did it, and can be undone", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${yasmin}`);
  await expect(page.getByText(/^No decision yet\. The score is advice/)).toBeVisible();
  await page.getByRole("button", { name: "Shortlist candidate" }).click();
  await expect(page.getByRole("button", { name: "Remove from shortlist" })).toBeVisible();

  const stored = await storedDecision(await applicationOf(yasmin, job));
  expect(stored.decision).toBe("shortlisted");
  expect(stored.decided_by).toBe(await userIdOf(recruiter));
  expect(stored.activity.map((row) => row.action)).toEqual(["application.shortlisted"]);
  await expectAccessible(page);

  await page.getByRole("button", { name: "Remove from shortlist" }).click();
  await expect(page.getByRole("button", { name: "Shortlist candidate" })).toBeVisible();
  expect((await storedDecision(await applicationOf(yasmin, job))).decided_by).toBeNull();
});

test("rejecting needs a reason, names the decider and states the consequence", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}/candidates/${omar}`);
  await page.getByRole("button", { name: "Reject candidate…" }).click();
  const dialog = page.getByRole("dialog", { name: "Reject Omar Hassan?" });
  await expect(dialog).toContainText("You'll be recorded as the person who decided.");
  await expect(dialog).toContainText(`Will be recorded: \u2068${recruiter.email}\u2069`);
  await expect(dialog.getByRole("button", { name: "Reject candidate" })).toBeDisabled();
  await dialog
    .getByRole("combobox", { name: "Reason (required)" })
    .selectOption({ label: "Less experience than required" });
  await dialog.getByRole("button", { name: "Reject candidate" }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByRole("button", { name: "Undo rejection" })).toBeVisible();

  const stored = await storedDecision(await applicationOf(omar, job));
  expect(stored.decision).toBe("rejected");
  expect(stored.decided_by).toBe(await userIdOf(recruiter));
  expect(stored.activity.at(-1)).toMatchObject({
    action: "application.rejected",
    metadata: { reason: "experience", previous: "undecided" },
  });

  await page.getByRole("button", { name: "Undo rejection" }).click();
  await expect(page.getByRole("button", { name: "Reject candidate…" })).toBeVisible();
});

test("the ranked list has no reject control in its rows", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto(`/en/jobs/${job}`);
  const table = page.getByRole("table", { name: "Candidates ranked by score" });
  await expect(table.getByRole("row", { name: /Yasmin Farouk/ })).toBeVisible();
  await table.getByRole("row", { name: /Yasmin Farouk/ }).hover();
  await expect(page.getByRole("button", { name: /reject/i })).toHaveCount(0);
});

test.describe("the decision API", () => {
  test("ignores a decider named in the request", async ({ page }) => {
    await signIn(page, recruiter);
    const application = await applicationOf(yasmin, job);
    const response = await page.request.post(`/api/applications/${application}/decision`, {
      data: { decision: "shortlisted", decidedBy: await userIdOf(stranger) },
    });
    expect(response.status()).toBe(200);
    expect(await response.json()).toMatchObject({
      decision: "shortlisted",
      decidedBy: recruiter.email,
    });
    expect((await storedDecision(application)).decided_by).toBe(await userIdOf(recruiter));
    await page.request.post(`/api/applications/${application}/decision`, {
      data: { decision: "undecided" },
    });
  });

  test("refuses a rejection without a reason", async ({ page }) => {
    await signIn(page, recruiter);
    const application = await applicationOf(omar, job);
    const response = await page.request.post(`/api/applications/${application}/decision`, {
      data: { decision: "rejected" },
    });
    expect(response.status()).toBe(400);
    expect((await storedDecision(application)).decision).toBe("undecided");
  });

  test("does not find another organisation's application", async ({ page }) => {
    await signIn(page, recruiter);
    const response = await page.request.post(`/api/applications/${strangersApplication}/decision`, {
      data: { decision: "shortlisted" },
    });
    expect(response.status()).toBe(404);
    expect((await storedDecision(strangersApplication)).decision).toBe("undecided");
  });

  test("refuses a request without a signed-in member", async ({ request }) => {
    const response = await request.post(
      `/api/applications/${await applicationOf(yasmin, job)}/decision`,
      { data: { decision: "shortlisted" } },
    );
    expect(response.status()).toBe(401);
  });
});
