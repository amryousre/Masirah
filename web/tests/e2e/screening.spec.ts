import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// The screening components in a real browser: the reject confirmation's safeguards, row
// selection, and the app frame's accessibility and layout in both directions.

test("rejecting needs a reason, and opens on keeping the candidate", async ({ page }) => {
  await page.goto("/en/design");
  // The button matrix above also has "Reject candidate…" buttons; this is the dialog specimen.
  const opener = page.getByRole("button", { name: "Reject candidate…" }).last();
  await opener.click();
  const dialog = page.getByRole("dialog", { name: "Reject Mohamed Abdallah?" });
  await expect(dialog.getByRole("button", { name: "Keep candidate" })).toBeFocused();
  const reject = dialog.getByRole("button", { name: "Reject candidate" });
  await expect(reject).toBeDisabled();
  await dialog.getByRole("combobox", { name: "Reason (required)" }).selectOption("experience");
  await expect(reject).toBeEnabled();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect(opener).toBeFocused();
});

test("choosing a candidate moves the selection", async ({ page }) => {
  await page.goto("/en/design");
  const table = page.getByRole("table", { name: "Candidates ranked by score" });
  await table.getByRole("button", { name: "Omar Hassan" }).click();
  await expect(table.getByRole("button", { name: "Omar Hassan" })).toHaveAttribute(
    "aria-current",
    "true",
  );
  await expect(table.getByRole("button", { name: "Mohamed Abdallah" })).not.toHaveAttribute(
    "aria-current",
  );
});

for (const lang of ["ar", "en"] as const) {
  test.describe(`the app frame in ${lang}`, () => {
    test("passes the WCAG 2.1 AA checks", async ({ page }) => {
      await page.goto(`/${lang}/design/frame`);
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
      await page.goto(`/${lang}/design/frame`);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });
  });
}

test("the sidebar sits at the reading start", async ({ page }) => {
  await page.goto("/ar/design/frame");
  const sidebar = await page.getByRole("complementary").boundingBox();
  const main = await page.getByRole("main").boundingBox();
  expect(sidebar && main && sidebar.x > main.x).toBe(true);
  await page.goto("/en/design/frame");
  const sidebarEn = await page.getByRole("complementary").boundingBox();
  const mainEn = await page.getByRole("main").boundingBox();
  expect(sidebarEn && mainEn && sidebarEn.x < mainEn.x).toBe(true);
});

test("keeps usage, the user and the language switch visible on a phone", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto("/ar/design/frame");
  await expect(page.getByRole("meter", { name: "السير الذاتية هذا الشهر" })).toBeVisible();
  await expect(page.getByText("نورهان سعيد")).toBeVisible();
  await expect(page.getByRole("link", { name: "English" })).toBeVisible();
});
