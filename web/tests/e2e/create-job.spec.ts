import { expect, test } from "@playwright/test";

import { type Account, createAccount } from "./support/accounts";
import { expectAccessible, signIn } from "./support/pages";

// Creating a job (T059): paste first, with the form as the way through when no proposal can be
// made, and the form itself checked on the server.

let recruiter: Account;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
});

test.afterAll(async () => {
  await recruiter.remove();
});

const DESCRIPTION =
  "We are hiring a Senior Front-end Developer in Cairo. At least 3 years of React and TypeScript.";

test("the page opens on pasting a description", async ({ page }) => {
  await signIn(page, recruiter);
  await page.getByRole("link", { name: "Create job" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Create job");
  await expect(page.getByRole("tab", { name: "Paste a description" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("button", { name: "Propose specification" })).toBeDisabled();
  await expectAccessible(page);
});

test("with no proposal available, the pasted text carries into the form", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/jobs/new");
  await page.getByLabel("Job description").fill(DESCRIPTION);
  await page.getByRole("button", { name: "Propose specification" }).click();
  await expect(page.getByRole("status")).toContainText("isn't available yet");
  await expect(page.getByRole("tab", { name: "Fill in manually" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByLabel("Description", { exact: true })).toHaveValue(DESCRIPTION);
});

test("a job filled in by hand is saved and listed", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/jobs/new?start=manual");
  await page.getByLabel("Job title").fill("Senior Front-end Developer");
  const required = page.getByRole("textbox", { name: "Required skills" });
  for (const skill of ["React", "TypeScript"]) {
    await required.fill(skill);
    await required.press("Enter");
  }
  await expect(
    page.getByRole("list", { name: "Required skills" }).getByRole("listitem"),
  ).toHaveCount(2);
  await page.getByLabel("Minimum experience").selectOption({ label: "3 years" });
  await page.getByLabel("Location").fill("Cairo");
  await page.getByLabel("Language requirement").selectOption({ label: "Arabic and English" });
  await page.getByRole("button", { name: "Save job" }).click();

  await expect(page).toHaveURL(/\/en\/jobs$/, { timeout: 20_000 });
  const row = page.getByRole("row", { name: /Senior Front-end Developer/ });
  await expect(row).toContainText("Cairo · 3+ years");
});

test("a skill can be removed before saving", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/jobs/new?start=manual");
  const preferred = page.getByRole("textbox", { name: "Preferred skills" });
  await preferred.fill("Figma");
  await preferred.press("Enter");
  await page.getByRole("button", { name: "Remove Figma" }).click();
  await expect(page.getByRole("list", { name: "Preferred skills" })).toHaveCount(0);
});

test("a job without a title is refused with a reason", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/en/jobs/new?start=manual");
  await page.getByRole("button", { name: "Save job" }).click();
  await expect(page.getByText("Enter the job title.")).toBeVisible();
  await expect(page).toHaveURL(/\/en\/jobs\/new/);
});

test("the form reads in Arabic, right to left", async ({ page }) => {
  await signIn(page, recruiter);
  await page.goto("/ar/jobs/new?start=manual");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByLabel("المسمى الوظيفي")).toBeVisible();
  await expectAccessible(page);
});
