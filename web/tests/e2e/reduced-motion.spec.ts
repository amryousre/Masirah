import { expect, type Page, test } from "@playwright/test";

import { signIn, untilHydrated } from "./support/pages";
import {
  expectScreen,
  MESSAGES,
  PUBLIC_SCREENS,
  seededScreens,
  SIGNED_IN_SCREENS,
} from "./support/screens";

// Motion (T108): every transition and animation takes between 150 and 250 milliseconds, the
// duration tokens in globals.css, and none at all when the visitor asks for reduced motion. No page
// plays a sequence as it loads: the user arrives in a task, not at a performance. The one motion
// outside the range is the spinner, a loading indicator that turns until the work is done; reduced
// motion stops it too.

const FASTEST = 150;
const SLOWEST = 250;

/** Every element's motion that breaks the rule, named by the element and the motion. */
async function offRhythm(page: Page, reduced: boolean): Promise<string[]> {
  await page.evaluate(() => document.fonts.ready);
  return page.evaluate(
    ({ reduced, fastest, slowest }) => {
      const milliseconds = (list: string) =>
        list
          .split(",")
          .map((value) => value.trim())
          .map((value) => (value.endsWith("ms") ? parseFloat(value) : parseFloat(value) * 1000));
      const problems: string[] = [];
      for (const element of document.querySelectorAll("*")) {
        const style = getComputedStyle(element);
        const name = `${element.tagName.toLowerCase()}.${element.getAttribute("class") ?? ""}`;
        const spinner = style.animationName.includes("spin");
        const motions = [
          ["transition", style.transitionProperty === "none" ? "0s" : style.transitionDuration],
          ["animation", style.animationName === "none" || spinner ? "0s" : style.animationDuration],
        ] as const;
        for (const [kind, durations] of motions) {
          for (const duration of milliseconds(durations)) {
            if (duration === 0) continue;
            if (reduced || duration < fastest || duration > slowest) {
              problems.push(`${name}: ${kind} ${String(duration)}ms`);
            }
          }
        }
        if (reduced && spinner) problems.push(`${name}: the spinner still turns`);
      }
      return problems;
    },
    { reduced, fastest: FASTEST, slowest: SLOWEST },
  );
}

/** Animations still running once the page has settled, apart from a loading spinner. */
async function playing(page: Page): Promise<string[]> {
  return page.evaluate(() =>
    document
      .getAnimations()
      .filter((animation) => animation.playState === "running")
      .map((animation) => (animation as CSSAnimation).animationName || "a transition")
      .filter((name) => !name.includes("spin")),
  );
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  // The longest motion allowed, and then some: anything still running after it is a sequence.
  await page.waitForTimeout(SLOWEST + 100);
}

for (const reducedMotion of ["no-preference", "reduce"] as const) {
  const reduced = reducedMotion === "reduce";
  test.describe(reduced ? "with reduced motion" : "with motion", () => {
    test.use({ reducedMotion });
    const data = seededScreens(reduced ? "Still Ltd" : "Motion Ltd");

    for (const [name, route] of PUBLIC_SCREENS) {
      test(`the ${name} screen keeps to the rule`, async ({ page }) => {
        await page.goto(`/en${route}`);
        await expectScreen(page, "en");
        expect(await offRhythm(page, reduced)).toEqual([]);
        await settle(page);
        expect(await playing(page)).toEqual([]);
      });
    }

    for (const [name, route] of SIGNED_IN_SCREENS) {
      test(`the ${name} screen keeps to the rule`, async ({ page }) => {
        await signIn(page, data().account);
        await page.goto(`/en${route(data())}`);
        await expectScreen(page, "en");
        expect(await offRhythm(page, reduced)).toEqual([]);
        await settle(page);
        expect(await playing(page)).toEqual([]);
      });
    }

    test("the reject dialog keeps to the rule", async ({ page }) => {
      const { account, jobId, candidateId } = data();
      await signIn(page, account);
      await page.goto(`/en/jobs/${jobId}/candidates/${candidateId}`);
      await untilHydrated(page, async () => {
        await page.getByRole("button", { name: MESSAGES.en.reject.open }).click();
        await expect(page.getByRole("dialog")).toBeVisible({ timeout: 1_000 });
      });
      expect(await offRhythm(page, reduced)).toEqual([]);
    });
  });
}

test.describe("the check", () => {
  test("catches a motion slower than the range", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({ content: "button { transition: opacity 600ms ease !important; }" });
    expect(await offRhythm(page, false)).not.toEqual([]);
  });

  test("catches motion left on when it was asked to stop", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/en/sign-in");
    await page.addStyleTag({ content: "button { transition: opacity 200ms ease !important; }" });
    expect(await offRhythm(page, true)).not.toEqual([]);
  });

  test("catches a sequence that plays as the page loads", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({
      content:
        "@keyframes arrive { to { opacity: 0.99; } } main { animation: arrive 5s infinite; }",
    });
    await settle(page);
    expect(await playing(page)).toEqual(["arrive"]);
  });
});
