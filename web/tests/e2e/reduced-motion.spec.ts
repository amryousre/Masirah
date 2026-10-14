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
// plays a sequence as it loads: the user arrives in a task, not at a performance.
//
// The rule is enforced on every stylesheet by the masirah/motion-tokens lint rule, which also sees
// the states no page shows on arrival (hover, loading, errors, toasts). This spec checks the result
// in the browser, on every screen and on the design page that shows each component in each state.
// The one motion outside the range is the spinner, a loading indicator that turns until the work is
// done; reduced motion stops it too.

const FASTEST = 150;
const SLOWEST = 250;

/** Every element's motion that breaks the rule, pseudo-elements included. */
async function offRhythm(page: Page, reduced: boolean): Promise<string[]> {
  await page.evaluate(() => document.fonts.ready);
  return page.evaluate(
    ({ reduced, fastest, slowest }) => {
      const list = (value: string) => value.split(",").map((part) => part.trim());
      const ms = (value: string) =>
        value.endsWith("ms") ? parseFloat(value) : parseFloat(value) * 1000;
      const problems: string[] = [];
      for (const element of document.querySelectorAll("*")) {
        const spinner = element.getAttribute("class")?.includes("spinner") ?? false;
        for (const pseudo of [null, "::before", "::after"]) {
          const style = getComputedStyle(element, pseudo);
          const name = `${element.tagName.toLowerCase()}.${element.getAttribute("class") ?? ""}${pseudo ?? ""}`;
          const check = (kind: string, duration: string, delay: string, count = "1") => {
            const length = ms(duration);
            if (length === 0) return;
            if (reduced || length < fastest || length > slowest) {
              problems.push(`${name}: ${kind} ${String(length)}ms`);
            }
            if (ms(delay) !== 0) problems.push(`${name}: ${kind} delayed ${delay}`);
            if (count !== "1") problems.push(`${name}: ${kind} runs ${count} times`);
          };
          if (style.transitionProperty !== "none") {
            const delays = list(style.transitionDelay);
            list(style.transitionDuration).forEach((duration, index) => {
              check("transition", duration, delays[index % delays.length] ?? "0s");
            });
          }
          const names = list(style.animationName);
          const durations = list(style.animationDuration);
          const delays = list(style.animationDelay);
          const counts = list(style.animationIterationCount);
          names.forEach((animation, index) => {
            if (animation === "none") return;
            // The spinner's own turning is the exception; any other animation on it is not.
            if (spinner && animation.includes("spin")) {
              if (reduced) problems.push(`${name}: the spinner still turns`);
              return;
            }
            check(
              `animation ${animation}`,
              durations[index % durations.length] ?? "0s",
              delays[index % delays.length] ?? "0s",
              counts[index % counts.length] ?? "1",
            );
          });
        }
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
      .filter((animation) => {
        const target = (animation.effect as KeyframeEffect | null)?.target;
        return !(target?.getAttribute("class")?.includes("spinner") ?? false);
      })
      .map((animation) => (animation as CSSAnimation).animationName || "a transition"),
  );
}

async function settle(page: Page) {
  await page.waitForLoadState("networkidle");
  // The longest motion allowed, and then some: anything still running after it is a sequence.
  await page.waitForTimeout(SLOWEST + 100);
}

async function expectStill(page: Page, reduced: boolean) {
  expect(await offRhythm(page, reduced)).toEqual([]);
  await settle(page);
  expect(await playing(page)).toEqual([]);
}

for (const reducedMotion of ["no-preference", "reduce"] as const) {
  const reduced = reducedMotion === "reduce";
  test.describe(reduced ? "with reduced motion" : "with motion", () => {
    test.use({ reducedMotion });

    for (const [name, route] of [...PUBLIC_SCREENS, ["design", "/design"] as const]) {
      test(`the ${name} screen keeps to the rule`, async ({ page }) => {
        await page.goto(`/en${route}`);
        await expectScreen(page, "en");
        await expectStill(page, reduced);
      });
    }

    test.describe("signed in", () => {
      const data = seededScreens(reduced ? "Still Ltd" : "Motion Ltd");

      for (const [name, route] of SIGNED_IN_SCREENS) {
        test(`the ${name} screen keeps to the rule`, async ({ page }) => {
          await signIn(page, data().account);
          await page.goto(`/en${route(data())}`);
          await expectScreen(page, "en");
          await expectStill(page, reduced);
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
        await expectStill(page, reduced);
      });
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

  test("catches a staggered sequence of in-range animations", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({
      content:
        "@keyframes arrive { from { opacity: 0.5; } } h1 { animation: arrive 200ms ease 400ms; }",
    });
    expect(await offRhythm(page, false)).not.toEqual([]);
  });

  test("catches motion on a pseudo-element", async ({ page }) => {
    await page.goto("/en/sign-in");
    await page.addStyleTag({
      content: "h1::after { content: ''; transition: opacity 600ms ease; }",
    });
    expect(await offRhythm(page, false)).not.toEqual([]);
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
