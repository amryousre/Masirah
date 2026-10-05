import { expect, type Locator, type Page, test } from "@playwright/test";

import { type Account, addJob, addRankedCandidate, createAccount } from "./support/accounts";
import { signIn, untilHydrated } from "./support/pages";

// The whole layout mirrors (T042): in Arabic the frame, the forms, the tables and the score
// breakdown run right to left, measured where they land on the page, and no English string is
// left behind once the page is in Arabic.

let recruiter: Account;
let job: string;
let candidate: string;

test.beforeAll(async () => {
  recruiter = await createAccount("دلتا سوفت");
  job = await addJob(recruiter, { title: "محاسب أول", location: "الجيزة" });
  candidate = await addRankedCandidate(recruiter, job, {
    name: "ياسمين فاروق",
    total: 86,
    justification: "ست سنوات في نايل فارما على إقفال نهاية الشهر.",
    confidence: 0.95,
    ratings: {
      skills_match: 90,
      experience_relevance: 80,
      education: 100,
      tenure_stability: 80,
      language: 100,
      location: 60,
    },
    evidence: "مذكور في السيرة.",
    summary: ["محاسبة بخبرة ست سنوات.", "تستخدم ساب يوميًا."],
  });
  await addRankedCandidate(recruiter, job, {
    name: "عمر حسن",
    total: 74,
    justification: "خبرة جيدة في المراجعة.",
    confidence: 0.92,
  });
});

test.afterAll(async () => {
  await recruiter.remove();
});

async function box(locator: Locator) {
  const found = await locator.boundingBox();
  if (found === null) throw new Error("The element is not on the page.");
  return { left: found.x, right: found.x + found.width };
}

/** Within a pixel: layout rounds, and a mirrored edge need not land on the same fraction. */
function near(a: number, b: number) {
  expect(Math.abs(a - b)).toBeLessThanOrEqual(1);
}

/**
 * The page's visible text, less what is allowed to stay Latin in Arabic: the name of the other
 * language on its switch, file formats, file extensions and email addresses.
 */
async function strayLatin(page: Page): Promise<string[]> {
  // Decoration hidden from assistive technology, such as the avatar's initial, is not text.
  const text = await page.evaluate(() => {
    const body = document.body.cloneNode(true) as HTMLElement;
    for (const hidden of body.querySelectorAll('[aria-hidden="true"]')) hidden.remove();
    document.body.append(body);
    const visible = body.innerText;
    body.remove();
    return visible;
  });
  const allowed = text
    .replace(/\S+@\S+/g, " ")
    .replace(/\b(English|PDF|DOCX|DOC|JPG|PNG|pdf)\b/g, " ");
  return allowed.match(/[A-Za-z]+/g) ?? [];
}

for (const [lang, rtl] of [
  ["ar", true],
  ["en", false],
] as const) {
  test.describe(`in ${lang === "ar" ? "Arabic" : "English"}`, () => {
    test("the frame's navigation sits at the inline start", async ({ page }) => {
      await signIn(page, recruiter);
      await page.goto(`/${lang}/jobs/${job}`);
      const nav = await box(
        page.getByRole("navigation", { name: /Main navigation|التنقل الرئيسي/ }),
      );
      const heading = await box(page.getByRole("heading", { level: 1 }));
      if (rtl) expect(nav.left).toBeGreaterThan(heading.right);
      else expect(nav.right).toBeLessThan(heading.left);
    });

    test("the ranked table's columns run in reading order", async ({ page }) => {
      await signIn(page, recruiter);
      await page.goto(`/${lang}/jobs/${job}`);
      const headers = page.getByRole("table").getByRole("columnheader");
      const rank = await box(headers.nth(0));
      const name = await box(headers.nth(1));
      if (rtl) expect(rank.left).toBeGreaterThan(name.left);
      else expect(rank.left).toBeLessThan(name.left);
    });

    test("a form's label lines up with its field at the inline start", async ({ page }) => {
      await signIn(page, recruiter);
      await page.goto(`/${lang}/jobs/new`);
      // A click before hydration is lost, and the field below would never appear.
      const manual = page.getByRole("tab", { name: /Fill in manually|إدخال يدوي/ });
      await untilHydrated(page, async () => {
        await manual.click();
        await expect(manual).toHaveAttribute("aria-selected", "true", { timeout: 1_000 });
      });
      const field = page.getByRole("textbox", { name: /^(Job title|المسمى الوظيفي)/ });
      const label = page.locator(`label[for="${(await field.getAttribute("id")) ?? ""}"]`);
      const [fieldBox, labelBox] = [await box(field), await box(label)];
      if (rtl) near(labelBox.right, fieldBox.right);
      else near(labelBox.left, fieldBox.left);
    });

    test("the reasons sit at the inline start and the breakdown fills from it", async ({
      page,
    }) => {
      await signIn(page, recruiter);
      await page.goto(`/${lang}/jobs/${job}/candidates/${candidate}`);
      const reasons = await box(page.getByRole("region", { name: /^(Reasons|الأسباب)$/ }));
      const document = await box(
        page.getByRole("region", { name: /^(Original document|المستند الأصلي)$/ }),
      );
      if (rtl) expect(reasons.left).toBeGreaterThan(document.left);
      else expect(reasons.left).toBeLessThan(document.left);

      const track = page.locator("[data-track]").first();
      const [trackBox, fillBox] = [await box(track), await box(track.locator("span").first())];
      if (rtl) near(fillBox.right, trackBox.right);
      else near(fillBox.left, trackBox.left);
    });
  });
}

test("no English string survives on an Arabic page", async ({ page }) => {
  await signIn(page, recruiter);
  for (const path of [
    "/ar/jobs",
    "/ar/jobs/new",
    `/ar/jobs/${job}`,
    `/ar/jobs/${job}/candidates/${candidate}`,
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await strayLatin(page), path).toEqual([]);
  }
  // Unselected, the check below would read the reasons again rather than the profile.
  const profile = page.getByRole("tab", { name: "الملف المستخرج" });
  await untilHydrated(page, async () => {
    await profile.click();
    await expect(profile).toHaveAttribute("aria-selected", "true", { timeout: 1_000 });
  });
  expect(await strayLatin(page), "the extracted profile").toEqual([]);
});
