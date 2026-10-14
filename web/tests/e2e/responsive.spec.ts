import { expect, type Page, test } from "@playwright/test";

import { signIn, untilHydrated } from "./support/pages";
import {
  expectScreen,
  LANGS,
  MESSAGES,
  PUBLIC_SCREENS,
  type Seeded,
  seedScreens,
  SIGNED_IN_SCREENS,
} from "./support/screens";

// Every screen usable from 360 pixels of width (T104, NFR-12): the page never scrolls sideways,
// and nothing sticks out past the edge of the screen unless it sits in a container of its own that
// scrolls, as a wide table may. A page cannot pass by hiding its overflow either.

const PHONE = { width: 360, height: 740 };

let seeded: Seeded | undefined;

test.beforeAll(async () => {
  seeded = await seedScreens("Narrow Ltd");
});

test.afterAll(async () => {
  await seeded?.account.remove();
});

function data(): Seeded {
  if (seeded === undefined) throw new Error("The narrow-screen account was not made.");
  return seeded;
}

/** What breaks the 360-pixel rule on the page, or nothing. */
async function overflow(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const problems: string[] = [];
    const root = document.documentElement;
    const width = root.clientWidth;
    if (root.scrollWidth > width)
      problems.push(`the page scrolls sideways by ${String(root.scrollWidth - width)}px`);
    for (const element of [root, document.body]) {
      const hidden = getComputedStyle(element).overflowX;
      if (hidden === "hidden" || hidden === "clip") {
        problems.push(`${element.tagName.toLowerCase()} hides its overflow (${hidden})`);
      }
    }
    // An element that reaches past the screen is a problem unless a container it sits in scrolls
    // or clips sideways on its own.
    const contained = (element: Element) => {
      for (
        let node = element.parentElement;
        node !== null && node !== document.body;
        node = node.parentElement
      ) {
        if (getComputedStyle(node).overflowX !== "visible") return true;
      }
      return false;
    };
    for (const element of document.body.querySelectorAll("*")) {
      if (!(element instanceof HTMLElement) || !element.checkVisibility()) continue;
      const box = element.getBoundingClientRect();
      if (box.width === 0 || (box.left >= -1 && box.right <= width + 1)) continue;
      if (contained(element)) continue;
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

for (const lang of LANGS) {
  test.describe(`in ${lang} at 360 px`, () => {
    test.use({ viewport: PHONE });

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

test("the check catches a page that is too wide", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/en/sign-in");
  await page.addStyleTag({ content: "main { min-inline-size: 480px; }" });
  expect(await overflow(page)).not.toEqual([]);
});

test("the check catches a page that hides its overflow", async ({ page }) => {
  await page.setViewportSize(PHONE);
  await page.goto("/en/sign-in");
  await page.addStyleTag({ content: "body { overflow-x: hidden; }" });
  expect(await overflow(page)).not.toEqual([]);
});
