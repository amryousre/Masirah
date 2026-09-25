import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// The bilingual shell (T025 to T027) in a real browser: routing, direction, the shared components'
// keyboard and focus behaviour, and WCAG 2.1 AA (Constitution IV) in both languages.

test.describe("locale routing", () => {
  test("sends an Arabic browser to Arabic", async ({ browser }) => {
    const page = await (await browser.newContext({ locale: "ar-EG" })).newPage();
    await page.goto("/");
    await expect(page).toHaveURL(/\/ar\/design$/);
  });

  test("sends an English browser to English", async ({ browser }) => {
    const page = await (await browser.newContext({ locale: "en-US" })).newPage();
    await page.goto("/");
    await expect(page).toHaveURL(/\/en\/design$/);
  });

  test("answers an unknown page with a translated not-found page", async ({ page }) => {
    const response = await page.goto("/ar/no-such-page");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText("هذه الصفحة غير موجودة");
  });
});

for (const [lang, dir] of [
  ["ar", "rtl"],
  ["en", "ltr"],
] as const) {
  test.describe(`the design system in ${lang}`, () => {
    test(`reads ${dir}`, async ({ page }) => {
      await page.goto(`/${lang}/design`);
      await expect(page.locator("html")).toHaveAttribute("lang", lang);
      await expect(page.locator("html")).toHaveAttribute("dir", dir);
    });

    test("passes the WCAG 2.1 AA checks", async ({ page }) => {
      await page.goto(`/${lang}/design`);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      const violations = results.violations.map(
        (violation) =>
          `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`,
      );
      expect(violations).toEqual([]);
    });

    test("never scrolls sideways on a 360 px phone", async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 780 });
      await page.goto(`/${lang}/design`);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });
  });
}

test("the language switch opens the same page in the other language", async ({ page }) => {
  await page.goto("/ar/design");
  await page.getByRole("banner").getByRole("link", { name: "English" }).click();
  await expect(page).toHaveURL(/\/en\/design$/);
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
});

test("tabs move forward with the left arrow in Arabic", async ({ page }) => {
  await page.goto("/ar/design");
  await page.getByRole("tab", { name: /المرشحون/ }).focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("tab", { name: /قائمة المراجعة/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("tab", { name: /قائمة المراجعة/ })).toBeFocused();
});

test("the dialog opens on the safe choice, closes on Escape and returns focus", async ({
  page,
}) => {
  await page.goto("/en/design");
  const opener = page.getByRole("button", { name: "Discard changes…" });
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "Discard your changes to this job?" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Keep editing" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
});
