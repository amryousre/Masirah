import { expect, type Locator, type Page, test } from "@playwright/test";

// Every interactive component has seven states (T107, DESIGN.md section 7): default, hover, focus,
// active, disabled, loading and error. The design page shows each component in the states it
// renders; this spec drives the rest, the ones a pointer or a keyboard brings about, and checks
// that each looks different from the one before it. Shipping half of them is shipping an
// unfinished component.

const SETTLE = 300; // longer than the slowest motion token, so a transition has finished

/** What a person sees of an element: its colours, edges, outline, underline and decoration. */
function look(locator: Locator): Promise<string> {
  return locator.evaluate((node) => {
    const style = getComputedStyle(node);
    return [
      style.backgroundColor,
      style.color,
      style.borderColor,
      style.boxShadow,
      style.outlineStyle,
      style.outlineColor,
      style.textDecorationColor,
    ].join("|");
  });
}

interface Looks {
  rest: string;
  hover: string;
  active: string;
  focus: string;
}

async function looksOf(page: Page, target: Locator): Promise<Looks> {
  await target.scrollIntoViewIfNeeded();
  await page.mouse.move(0, 0);
  await page.waitForTimeout(SETTLE);
  const rest = await look(target);
  await target.hover();
  await page.waitForTimeout(SETTLE);
  const hover = await look(target);
  await page.mouse.down();
  await page.waitForTimeout(SETTLE);
  const active = await look(target);
  // Released away from the element, so the press is cancelled rather than a click.
  await page.mouse.move(0, 0);
  await page.mouse.up();
  await target.focus();
  await page.keyboard.press("Shift");
  await page.waitForTimeout(SETTLE);
  const focus = await look(target);
  await target.blur();
  return { rest, hover, active, focus };
}

function expectDistinct(name: string, looks: Looks) {
  expect(looks.hover, `${name}: hover looks like rest`).not.toBe(looks.rest);
  expect(looks.active, `${name}: active looks like hover`).not.toBe(looks.hover);
  expect(looks.focus, `${name}: focus looks like rest`).not.toBe(looks.rest);
}

test.describe("on the design page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/en/design");
    await page.waitForLoadState("networkidle");
  });

  for (const [variant, label] of [
    ["Primary", "Save job"],
    ["Secondary", "Upload CVs"],
    ["Ghost", "Cancel"],
    ["Destructive", "Reject candidate…"],
  ] as const) {
    test(`the ${variant.toLowerCase()} button has hover, active and focus states`, async ({
      page,
    }) => {
      const row = page.getByRole("row", { name: new RegExp(`^${variant}`) });
      const enabled = row.getByRole("button", { name: label, exact: true }).first();
      expectDistinct(variant, await looksOf(page, enabled));
      await expect(row.getByRole("button", { name: label, exact: true }).nth(1)).toBeDisabled();
    });
  }

  test("a text field and a select have hover, active and focus states", async ({ page }) => {
    for (const field of [
      page.getByRole("textbox", { name: "Job title" }).first(),
      page.getByRole("combobox", { name: "Required language" }).first(),
    ]) {
      const looks = await looksOf(page, field);
      expect(looks.hover).not.toBe(looks.rest);
      expect(looks.focus).not.toBe(looks.rest);
    }
  });

  test("a tab that is not selected has hover, active and focus states", async ({ page }) => {
    const tab = page.getByRole("tab", { selected: false }).first();
    expectDistinct("tab", await looksOf(page, tab));
  });

  test("the language switch has every state", async ({ page }) => {
    const section = page
      .locator("section", { has: page.getByRole("heading", { name: /language/i }) })
      .last();
    const live = section.getByRole("link", { name: /العربية/ }).first();
    expectDistinct("language switch", await looksOf(page, live));
    await expect(section.locator("[aria-disabled='true']")).toContainText("العربية");
    await expect(section.getByRole("alert")).toHaveText(
      "Couldn't change the language. The page is still in English.",
    );
  });
});
