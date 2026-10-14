import { expect, type Page, test } from "@playwright/test";

import { expectAccessible, signIn, untilHydrated } from "./support/pages";
import {
  expectScreen,
  LANGS,
  MESSAGES,
  PUBLIC_SCREENS,
  type Seeded,
  seedScreens,
  SIGNED_IN_SCREENS,
} from "./support/screens";

// The WCAG 2.1 Level AA audit (T103, NFR-11, SC-012): every recruiter-facing screen, in both
// languages, with real data on it, passes axe's AA rules, contrast among them. axe does not test
// placeholder text, so each placeholder is held to the same 4.5:1 here.

let seeded: Seeded | undefined;

test.beforeAll(async () => {
  seeded = await seedScreens("Audit Ltd");
});

test.afterAll(async () => {
  await seeded?.account.remove();
});

function data(): Seeded {
  if (seeded === undefined) throw new Error("The audit's account was not made.");
  return seeded;
}

/**
 * Every placeholder that falls short of 4.5:1 against what is behind it, named by its field: an
 * input's or a text area's placeholder, and a select's while its placeholder option is showing.
 */
async function faintPlaceholders(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    type Rgba = { r: number; g: number; b: number; a: number };
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 1;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (context === null) throw new Error("no canvas");
    const SENTINEL = "#010203";
    // A colour the canvas cannot parse leaves fillStyle as it was, so it is refused rather than
    // read as whatever was drawn last.
    const channels = (color: string): Rgba => {
      context.fillStyle = SENTINEL;
      context.fillStyle = color;
      if (context.fillStyle === SENTINEL && color !== SENTINEL) {
        throw new Error(`a colour the check cannot read: ${color}`);
      }
      context.clearRect(0, 0, 1, 1);
      context.fillRect(0, 0, 1, 1);
      const [r = 0, g = 0, b = 0, a = 255] = context.getImageData(0, 0, 1, 1).data;
      return { r, g, b, a: a / 255 };
    };
    const over = (top: Rgba, below: Rgba): Rgba => ({
      r: top.r * top.a + below.r * (1 - top.a),
      g: top.g * top.a + below.g * (1 - top.a),
      b: top.b * top.a + below.b * (1 - top.a),
      a: 1,
    });
    // What shows behind the field: its own background and its ancestors', the translucent ones
    // blended over the first opaque one, which is white when none is.
    const backdrop = (element: Element): Rgba => {
      const layers: Rgba[] = [];
      for (let node: Element | null = element; node !== null; node = node.parentElement) {
        const color = channels(getComputedStyle(node).backgroundColor);
        if (color.a === 0) continue;
        layers.push(color);
        if (color.a === 1) break;
      }
      return layers.reduceRight((below, top) => over(top, below), channels("white"));
    };
    const luminance = ({ r, g, b }: Rgba) => {
      const linear = (value: number) => {
        const v = value / 255;
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
    };
    const ratio = (ink: Rgba, base: Rgba) => {
      const [light, dark] = [luminance(over(ink, base)), luminance(base)].sort((x, y) => y - x);
      return ((light ?? 0) + 0.05) / ((dark ?? 0) + 0.05);
    };

    const short: string[] = [];
    const judge = (field: HTMLElement, name: string, ink: string) => {
      const value = ratio(channels(ink), backdrop(field));
      if (value < 4.5) short.push(`${name}: ${value.toFixed(2)}`);
    };
    for (const field of document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
      "input[placeholder], textarea[placeholder]",
    )) {
      if (field.placeholder === "" || !field.checkVisibility()) continue;
      judge(field, field.name || field.id, getComputedStyle(field, "::placeholder").color);
    }
    for (const field of document.querySelectorAll("select")) {
      if (field.value !== "" || !field.checkVisibility()) continue;
      judge(field, field.name || field.id, getComputedStyle(field).color);
    }
    return short;
  });
}

for (const lang of LANGS) {
  test.describe(`in ${lang}`, () => {
    for (const [name, route] of PUBLIC_SCREENS) {
      test(`the ${name} screen meets WCAG 2.1 AA`, async ({ page }) => {
        await page.goto(`/${lang}${route}`);
        await expectScreen(page, lang);
        await expectAccessible(page);
        expect(await faintPlaceholders(page)).toEqual([]);
      });
    }

    for (const [name, route] of SIGNED_IN_SCREENS) {
      test(`the ${name} screen meets WCAG 2.1 AA`, async ({ page }) => {
        await signIn(page, data().account);
        await page.goto(`/${lang}${route(data())}`);
        await expectScreen(page, lang);
        await expectAccessible(page);
        expect(await faintPlaceholders(page)).toEqual([]);
      });
    }

    test("the reject dialog meets WCAG 2.1 AA", async ({ page }) => {
      const { account, jobId, candidateId } = data();
      await signIn(page, account);
      await page.goto(`/${lang}/jobs/${jobId}/candidates/${candidateId}`);
      const reject = MESSAGES[lang].reject;
      await untilHydrated(page, async () => {
        await page.getByRole("button", { name: reject.open }).click();
        await expect(page.getByRole("dialog")).toBeVisible({ timeout: 1_000 });
      });
      await expectAccessible(page);
      expect(await faintPlaceholders(page)).toEqual([]);
    });
  });
}

test("the placeholder check finds the placeholders and catches a faint one", async ({ page }) => {
  await page.goto("/en/sign-in");
  await expect(page.getByPlaceholder("name@company.com")).toBeVisible();
  await page.addStyleTag({ content: "input::placeholder { color: #d4d4d4 !important; }" });
  expect(await faintPlaceholders(page)).not.toEqual([]);
});

test("the placeholder check blends a translucent backdrop", async ({ page }) => {
  await page.goto("/en/sign-in");
  // A grey placeholder that passes on white fails once the field sits on a dark veil.
  await page.addStyleTag({
    content: `input::placeholder { color: #595959 !important; }
      input { background: transparent !important; }
      form { background: rgb(0 0 0 / 0.7) !important; }`,
  });
  expect(await faintPlaceholders(page)).not.toEqual([]);
});
