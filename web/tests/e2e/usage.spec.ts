import { expect, test } from "@playwright/test";

import { type Account, addJob, addSpend, createAccount, setLimits } from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// The month's usage on every screen, and a halt that says so (T093, FR-026). The count is the
// CVs a model read this month, as the worker counts them; at a limit, the CV limit or the spend
// ceiling, processing is paused until the month renews, and the screens say so in plain words.

let working: Account;
let halted: Account;
let job: string;

test.beforeAll(async () => {
  working = await createAccount("Delta Soft");
  await addSpend(working, "extraction", 0.4);
  await addSpend(working, "scoring", 1.2);

  halted = await createAccount("Nile Trading");
  job = await addJob(halted, { title: "Store Manager" });
  await addSpend(halted, "extraction", 0.4);
  // The spend ceiling, reached with nearly all the month's CVs left.
  await setLimits(halted, { ceilingEgp: 0.4 });
});

test.afterAll(async () => {
  await working.remove();
  await halted.remove();
});

test("the sidebar counts the CVs read this month against the limit", async ({ page }) => {
  await signIn(page, working);
  const meter = page.getByRole("meter", { name: "CVs this month" });
  await expect(meter).toHaveAttribute("aria-valuenow", "1");
  await expect(meter).toHaveAttribute("aria-valuemax", "300");
  await expect(page.getByText("1 of 300")).toBeVisible();
  await expect(page.getByText(/^Renews on \w{3} \d{1,2}\.$/)).toBeVisible();
  await expectAccessible(page);
});

test("at the spend ceiling, the sidebar and the job say processing is paused", async ({ page }) => {
  await signIn(page, halted);
  await expect(page.getByText(/^Processing is paused\./)).toBeVisible();
  await expect(page.getByText(/when you upgrade/)).toHaveCount(0);
  await page.goto(`/en/jobs/${job}`);
  await expect(page.getByText(/reached this month's limit of 300 CVs/)).toBeVisible();
  await expect(page.getByText(/Everything you uploaded is still here/)).toBeVisible();
  await expectAccessible(page);
});

test("in Arabic the pause is said in Arabic", async ({ page }) => {
  await signIn(page, halted);
  await page.goto("/ar/jobs");
  await expect(page.getByText(/^توقفت المعالجة\./)).toBeVisible();
});
