import AxeBuilder from "@axe-core/playwright";
import { expect, type Page } from "@playwright/test";

import type { Account } from "./accounts";

/** Signs in with a password, as the account's owner would, and waits for the job list. */
export async function signIn(page: Page, account: Account) {
  await page.goto("/en/sign-in");
  await page.getByLabel("Work email").fill(account.email);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  // Signing in is a round trip to Auth and a redirect; under a full parallel run it takes longer
  // than the default five seconds.
  await expect(page).toHaveURL(/\/en\/jobs$/, { timeout: 20_000 });
}

/** WCAG 2.1 AA, as Constitution IV requires of every page. */
export async function expectAccessible(page: Page) {
  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(violations.map((violation) => violation.id)).toEqual([]);
}

/**
 * Repeats a page's first interaction until it takes effect. Under a full parallel run the page can
 * render before React has hydrated it, and a change made in that moment is lost.
 */
export async function untilHydrated(page: Page, interact: () => Promise<void>) {
  await expect(interact).toPass({ timeout: 20_000 });
}
