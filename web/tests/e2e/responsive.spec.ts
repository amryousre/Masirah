import { expect, type Page, test } from "@playwright/test";

import { signIn, untilHydrated } from "./support/pages";
import {
  expectScreen,
  LANGS,
  MESSAGES,
  PUBLIC_SCREENS,
  seededScreens,
  SIGNED_IN_SCREENS,
} from "./support/screens";

// Every screen usable from 360 pixels of width (T104, NFR-12): the page never scrolls sideways,
// and nothing reaches past the edge of the screen unless it sits in a container that scrolls
// sideways on its own and itself fits, as a wide table may. Hiding overflow does not count as
// fitting: content clipped past the edge cannot be reached at all.

const PHONE = { width: 360, height: 740 };

/** What breaks the 360-pixel rule on the page, or nothing, once its fonts have loaded. */
async function overflow(page: Page): Promise<string[]> {
  await page.evaluate(() => document.fonts.ready);
  return page.evaluate(() => {
    const problems: string[] = [];
    const root = document.documentElement;
    const width = root.clientWidth;
    const outside = (box: DOMRect) => box.left < -1 || box.right > width + 1;
    if (root.scrollWidth > width) {
      problems.push(`the page scrolls sideways by ${String(root.scrollWidth - width)}px`);
    }
    for (const element of [root, document.body]) {
      const hidden = getComputedStyle(element).overflowX;
      if (hidden === "hidden" || hidden === "clip") {
        problems.push(`${element.tagName.toLowerCase()} hides its overflow (${hidden})`);
      }
    }
    // Inside a container that scrolls sideways and fits on the screen, the overflow can still be
    // reached by scrolling that container; inside one that hides or clips it, it cannot.
    const reachable = (element: Element) => {
      for (let node = element.parentElement; node !== null; node = node.parentElement) {
        const scrolls = ["auto", "scroll"].includes(getComputedStyle(node).overflowX);
        if (scrolls && !outside(node.getBoundingClientRect())) return true;
      }
      return false;
    };
    for (const element of document.body.querySelectorAll("*")) {
      if (!(element instanceof HTMLElement) || !element.checkVisibility()) continue;
      const box = element.getBoundingClientRect();
      if (box.width === 0 || !outside(box) || reachable(element)) continue;
      const name = element.id
        ? `#${element.id}`
        : `${element.tagName.toLowerCase()}.${element.className}`;
      problems.push(
        `${name} reaches ${String(Math.round(box.left))}..${String(Math.round(box.right))} of ${String(width)}px`,
      );
    }
    return problems;
  });
}

test.describe("every screen at 360 px", () => {
  test.use({ viewport: PHONE });
  const data = seededScreens("Narrow Ltd");

  for (const lang of LANGS) {
    test.describe(`in ${lang}`, () => {
      for (const [name, route] of PUBLIC_SCREENS) {
        test(`the ${name} screen fits`, async ({ page }) => {
          await page.goto(`/${lang}${route}`);
          await expectScreen(page, lang);
          expect(await overflow(page)).toEqual([]);
        });
      }

      for (const [name, route] of SIGNED_IN_SCREENS) {
        test(`the ${name} screen fits`, async ({ page }) => {
          await signIn(page, data().account);
          await page.goto(`/${lang}${route(data())}`);
          await expectScreen(page, lang);
          expect(await overflow(page)).toEqual([]);
        });
      }

      test("the reject dialog fits", async ({ page }) => {
        const { account, jobId, candidateId } = data();
        await signIn(page, account);
        await page.goto(`/${lang}/jobs/${jobId}/candidates/${candidateId}`);
        await untilHydrated(page, async () => {
          await page.getByRole("button", { name: MESSAGES[lang].reject.open }).click();
          await expect(page.getByRole("dialog")).toBeVisible({ timeout: 1_000 });
        });
        expect(await overflow(page)).toEqual([]);
      });
    });
  }
});

test.describe("the check", () => {
  test.use({ viewport: PHONE });

  test("catches a page that is too wide", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({ content: "main { min-inline-size: 480px; }" });
    expect(await overflow(page)).not.toEqual([]);
  });

  test("catches a page that hides its overflow", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({ content: "body { overflow-x: hidden; }" });
    expect(await overflow(page)).not.toEqual([]);
  });

  // Overflow towards the start of the line never makes the page scroll, so only the element check
  // sees it: past the left edge in English and past the right edge in Arabic.
  for (const lang of LANGS) {
    test(`catches content past the start edge in ${lang}`, async ({ page }) => {
      await page.goto(`/${lang}/sign-in`);
      await page.addStyleTag({ content: "h1 { margin-inline-start: -80px; }" });
      const problems = await overflow(page);
      expect(problems.some((problem) => problem.startsWith("h1"))).toBe(true);
    });
  }

  test("catches content a wrapper clips past the edge", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({
      content: "main { overflow: hidden; } h1 { inline-size: 520px; white-space: nowrap; }",
    });
    const problems = await overflow(page);
    expect(problems.some((problem) => problem.startsWith("h1"))).toBe(true);
  });
});
