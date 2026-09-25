import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import { type Account, createAccount } from "./support/accounts";

// Sign-in (T024) against the local Supabase stack: invitation only, the organisation taken from
// the session, and the no-access page for everyone else.

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const violations = results.violations.map(
    (violation) =>
      `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`,
  );
  expect(violations).toEqual([]);
}

// Next.js keeps an empty role="alert" of its own for route changes, so look inside the page.
async function signIn(page: Page, email: string, password: string) {
  await page.getByLabel("البريد الإلكتروني للعمل").fill(email);
  await page.getByLabel("كلمة المرور", { exact: true }).fill(password);
  await page.getByRole("button", { name: "تسجيل الدخول" }).click();
}

let member: Account;
let stranded: Account;

test.beforeAll(async () => {
  member = await createAccount("دلتا سوفت");
  stranded = await createAccount(null);
});

test.afterAll(async () => {
  await member.remove();
  await stranded.remove();
});

for (const lang of ["ar", "en"] as const) {
  test.describe(`in ${lang}`, () => {
    test("the sign-in page passes the WCAG 2.1 AA checks", async ({ page }) => {
      await page.goto(`/${lang}/sign-in`);
      await expectAccessible(page);
    });

    test("the no-access page passes the WCAG 2.1 AA checks", async ({ page }) => {
      await page.goto(`/${lang}/sign-in/no-access`);
      await expectAccessible(page);
    });

    test("never scrolls sideways on a 360 px phone", async ({ page }) => {
      await page.setViewportSize({ width: 360, height: 780 });
      await page.goto(`/${lang}/sign-in`);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });
  });
}

test("a product page sends a visitor who is not signed in to sign-in", async ({ page }) => {
  await page.goto("/ar/jobs");
  await expect(page).toHaveURL(/\/ar\/sign-in$/);
});

test("signs a member in to their organisation, and out again", async ({ page }) => {
  await page.goto("/ar/sign-in");
  await signIn(page, member.email, member.password);

  await expect(page).toHaveURL(/\/ar\/jobs$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("الوظائف");
  await expect(page.getByText("دلتا سوفت")).toBeVisible();
  await expect(page.getByText(member.email)).toBeVisible();

  // Signed in, the sign-in page has nothing to offer.
  await page.goto("/ar/sign-in");
  await expect(page).toHaveURL(/\/ar\/jobs$/);

  await page.getByRole("button", { name: "تسجيل الخروج" }).click();
  await expect(page).toHaveURL(/\/ar\/sign-in$/);
  await page.goto("/ar/jobs");
  await expect(page).toHaveURL(/\/ar\/sign-in$/);
});

test("on a phone, a short page does not stretch the frame's bar", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 });
  await page.goto("/ar/sign-in");
  await signIn(page, member.email, member.password);
  await expect(page).toHaveURL(/\/ar\/jobs$/);

  const bar = await page.getByRole("complementary").boundingBox();
  const heading = await page.getByRole("heading", { level: 1 }).boundingBox();
  expect(bar?.height).toBeLessThan(260);
  expect(heading?.y).toBeLessThan(320);
});

test("a wrong password says so without saying which part was wrong", async ({ page }) => {
  await page.goto("/ar/sign-in");
  await signIn(page, member.email, "not-the-password");

  await expect(page.getByRole("main").getByRole("alert")).toHaveText(
    "البريد الإلكتروني وكلمة المرور غير متطابقين. تحقّق منهما وحاول مرة أخرى.",
  );
  await expect(page.getByLabel("البريد الإلكتروني للعمل")).toHaveValue(member.email);
  await expect(page).toHaveURL(/\/ar\/sign-in$/);
});

test("an empty form is answered in the page's language", async ({ page }) => {
  await page.goto("/en/sign-in");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("main").getByRole("alert")).toHaveText(
    "Enter your work email and your password.",
  );
});

test("the password can be shown before sending", async ({ page }) => {
  await page.goto("/en/sign-in");
  const password = page.getByLabel("Password", { exact: true });
  const show = page.getByRole("button", { name: "Show password" });
  await expect(password).toHaveAttribute("type", "password");
  await show.click();
  await expect(show).toHaveAttribute("aria-pressed", "true");
  await expect(password).toHaveAttribute("type", "text");
});

test("an account in no organisation gets the no-access page and no session", async ({ page }) => {
  await page.goto("/en/sign-in");
  await page.getByLabel("Work email").fill(stranded.email);
  await page.getByLabel("Password", { exact: true }).fill(stranded.password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/en\/sign-in\/no-access\?reason=no-organisation$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "This account has no access yet",
  );
  await page.goto("/en/jobs");
  await expect(page).toHaveURL(/\/en\/sign-in$/);
});

test("a Google account nobody invited lands on the no-access page", async ({ page }) => {
  // What Supabase Auth sends back when sign-ups are closed and the account is new.
  await page.goto(
    "/ar/auth/callback?error=access_denied&error_code=signup_disabled&error_description=Signups+not+allowed+for+this+instance",
  );
  await expect(page).toHaveURL(/\/ar\/sign-in\/no-access$/);
  await expect(page.getByText("لم يُنشأ حساب ولم يُحفظ شيء.", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: "استخدام حساب آخر" }).click();
  await expect(page).toHaveURL(/\/ar\/sign-in$/);
});

test("a Google sign-in that did not finish is reported on the sign-in page", async ({ page }) => {
  await page.goto("/en/auth/callback?error=access_denied");
  await expect(page).toHaveURL(/\/en\/sign-in\?error=google$/);
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Google sign-in didn't finish.",
  );
});

test("Continue with Google goes to Google through Supabase Auth", async ({ page }) => {
  // Stop at Google's door: the test proves the request is formed, not that Google answers.
  const googleRequest = page.waitForRequest(/^https:\/\/accounts\.google\.com\//);
  await page.route(/^https:\/\/accounts\.google\.com\//, (route) => route.abort());

  await page.goto("/en/sign-in");
  await page.getByRole("button", { name: "Continue with Google" }).click();

  const google = new URL((await googleRequest).url());
  expect(google.searchParams.get("prompt")).toBe("select_account");
  expect(google.searchParams.get("redirect_uri")).toMatch(/\/auth\/v1\/callback$/);
});
