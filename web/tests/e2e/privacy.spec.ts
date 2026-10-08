import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

// The privacy page for candidates (T094, AI-09): public, in both languages, and saying that the
// model providers do not train on what is sent to them.

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(results.violations.map((violation) => violation.id)).toEqual([]);
}

test("anyone can read it in Arabic, without signing in", async ({ page }) => {
  await page.goto("/ar/privacy");
  await expect(page).toHaveURL(/\/ar\/privacy$/);
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("خصوصية المتقدمين للوظائف");
  await expect(page.getByRole("heading", { name: "مزوّدو الذكاء الاصطناعي" })).toBeVisible();
  await expect(page.getByText(/لا يستخدم أيٌّ منهما/)).toBeVisible();
  await expectAccessible(page);
});

test("it says the providers do not train on what is sent, in English", async ({ page }) => {
  await page.goto("/en/privacy");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Privacy for candidates");
  await expect(page.getByText(/neither uses what Masirah sends to train/)).toBeVisible();
  await expectAccessible(page);
});

test("sign-in links to it", async ({ page }) => {
  await page.goto("/en/sign-in");
  await page.getByRole("link", { name: "Privacy for candidates" }).click();
  await expect(page).toHaveURL(/\/en\/privacy$/);
});

test("it fits a phone without scrolling sideways", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto("/ar/privacy");
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBe(0);
});
