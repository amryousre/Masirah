import { expect, test } from "@playwright/test";

import { signIn, untilHydrated } from "./support/pages";
import { seededScreens } from "./support/screens";

// The landing page (masirah.online's first page): what Masirah does, a way in for invited
// recruiters, and a waitlist for companies that want an account. What the waitlist stores is held to
// the database tests (test_waitlist.py): the list is private, so not even the test can read it here. A signed-in member never sees it:
// they go straight to their jobs.

test("a visitor in Arabic sees what Masirah does and how to get in", async ({ page }) => {
  await page.goto("/ar");
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("300 سيرة ذاتية");
  await expect(page.getByRole("link", { name: "تسجيل الدخول" })).toHaveAttribute(
    "href",
    "/ar/sign-in",
  );
  await expect(
    page.getByRole("button", { name: "الانضمام لقائمة الانتظار" }).first(),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "الخصوصية" })).toHaveAttribute("href", "/ar/privacy");
});

test("the page promises nothing that isn't built", async ({ page }) => {
  await page.goto("/en");
  const text = (await page.locator("body").innerText()).toLowerCase();
  for (const promise of ["pricing", "free plan", "terms", "hello@masirah.online"]) {
    expect(text, `the landing page mentions ${promise}`).not.toContain(promise);
  }
});

test("a company joins the waitlist, and asking twice is fine", async ({ page }) => {
  const email = `waitlist-${String(Date.now())}@delta-soft.example`;
  await page.goto("/en");
  const form = page.getByRole("form", { name: "Join the waitlist" }).first();
  await untilHydrated(page, async () => {
    await form.getByLabel("Work email").fill(email.toUpperCase());
    await form.getByRole("button", { name: "Join the waitlist" }).click();
    await expect(form.getByRole("status")).toContainText("You’re on the list", { timeout: 2_000 });
  });
  // What is stored, and that no API role can read it back, is pipeline/tests/unit/test_waitlist.py.

  await page.reload();
  await untilHydrated(page, async () => {
    await form.getByLabel("Work email").fill(email);
    await form.getByRole("button", { name: "Join the waitlist" }).click();
    await expect(form.getByRole("status")).toContainText("You’re on the list", { timeout: 2_000 });
  });
});

test("an address that isn't one is answered in the page's language", async ({ page }) => {
  await page.goto("/ar");
  const form = page.getByRole("form", { name: "الانضمام لقائمة الانتظار" }).first();
  await untilHydrated(page, async () => {
    await form.getByLabel("البريد الإلكتروني للعمل").fill("nourhan@");
    await form.getByRole("button", { name: "الانضمام لقائمة الانتظار" }).click();
    await expect(form.getByRole("alert")).toContainText("بريد", { timeout: 2_000 });
  });
});

test("choosing a row in the example shows why it ranked there", async ({ page }) => {
  await page.goto("/en");
  const demo = page.getByRole("region", { name: "An example ranking" });
  await untilHydrated(page, async () => {
    await demo.getByRole("button", { name: /Sara Nabil/ }).click();
    await expect(demo.getByRole("heading", { name: "Why fourth" })).toBeVisible({ timeout: 1_000 });
  });
  await expect(demo.getByRole("button", { name: /Sara Nabil/ })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test.describe("a signed-in member", () => {
  const data = seededScreens("Landing Ltd");

  test("goes straight to their jobs", async ({ page }) => {
    await signIn(page, data().account);
    await page.goto("/ar");
    await expect(page).toHaveURL(/\/ar\/jobs$/);
  });
});

// The one motion on the page (DESIGN.md: 150 to 250 ms): the selection slides to the chosen row.
async function selectionTransform(page: import("@playwright/test").Page): Promise<string> {
  return page
    .locator('[data-flip-id="selection"]')
    .evaluate((node) => getComputedStyle(node).transform);
}

test("the selection slides to the chosen row, and settles", async ({ page }) => {
  await page.goto("/en");
  const demo = page.getByRole("region", { name: "An example ranking" });
  await untilHydrated(page, async () => {
    await demo.getByRole("button", { name: /Karim Hamdy/ }).click();
    await expect(demo.getByRole("heading", { name: "Why fifth" })).toBeVisible({ timeout: 1_000 });
  });
  await page.waitForTimeout(400);
  await demo.getByRole("button", { name: /Mona El-Sherif/ }).click();
  expect(await selectionTransform(page)).not.toBe("none");
  await expect
    .poll(() => selectionTransform(page), { timeout: 1_000 })
    .toMatch(/^(none|matrix\(1, 0, 0, 1, 0, 0\))$/);
});

test("with reduced motion the selection just moves", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/en");
  const demo = page.getByRole("region", { name: "An example ranking" });
  await untilHydrated(page, async () => {
    await demo.getByRole("button", { name: /Mona El-Sherif/ }).click();
    await expect(demo.getByRole("heading", { name: "Why first" })).toBeVisible({ timeout: 1_000 });
  });
  expect(await selectionTransform(page)).toBe("none");
});
