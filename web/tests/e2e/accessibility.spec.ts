import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

import {
  type Account,
  addFileInReview,
  addJob,
  addRankedCandidate,
  createAccount,
} from "./support/accounts";
import { signIn } from "./support/pages";

// The WCAG 2.1 Level AA audit (T103, NFR-11, SC-012): every recruiter-facing screen, in both
// languages, with real data on it, passes axe's AA rules, contrast among them. axe does not test
// placeholder text, so each placeholder is held to the same 4.5:1 here.

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

let recruiter: Account;
let jobId: string;
let candidateId: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Audit Ltd");
  jobId = await addJob(recruiter, { title: "Senior Accountant", location: "Cairo" });
  candidateId = await addRankedCandidate(recruiter, jobId, {
    name: "Mona Abdallah",
    total: 82,
    justification: "Eight years of audit work at a listed company, and fluent English.",
    confidence: 0.94,
  });
  await addFileInReview(recruiter, {
    fileName: "scan_0187.pdf",
    jobId,
    status: "needs_review",
    reviewReason: "no_text",
  });
});

test.afterAll(async () => {
  await recruiter.remove();
});

async function expectAccessible(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(
    violations.map(
      (violation) =>
        `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`,
    ),
  ).toEqual([]);
}

/** Every placeholder that falls short of 4.5:1 against its field, named by its field. */
async function faintPlaceholders(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const channels = (color: string) => {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = 1;
      const context = canvas.getContext("2d");
      if (context === null) throw new Error("no canvas");
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      const [r = 0, g = 0, b = 0, a = 255] = context.getImageData(0, 0, 1, 1).data;
      return { r, g, b, a: a / 255 };
    };
    const luminance = ({ r, g, b }: { r: number; g: number; b: number }) => {
      const linear = (value: number) => {
        const v = value / 255;
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      };
      return 0.2126 * linear(r) + 0.7152 * linear(g) + 0.0722 * linear(b);
    };
    // The first opaque background at or above the field.
    const background = (element: Element) => {
      for (let node: Element | null = element; node !== null; node = node.parentElement) {
        const color = channels(getComputedStyle(node).backgroundColor);
        if (color.a === 1) return color;
      }
      return channels("white");
    };
    const short: string[] = [];
    for (const field of document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(
      "input[placeholder], textarea[placeholder]",
    )) {
      if (field.placeholder === "" || field.offsetParent === null) continue;
      const base = background(field);
      const ink = channels(getComputedStyle(field, "::placeholder").color);
      // A translucent placeholder is seen blended over its field.
      const seen = {
        r: ink.r * ink.a + base.r * (1 - ink.a),
        g: ink.g * ink.a + base.g * (1 - ink.a),
        b: ink.b * ink.a + base.b * (1 - ink.a),
      };
      const [light, dark] = [luminance(seen), luminance(base)].sort((x, y) => y - x) as [
        number,
        number,
      ];
      const ratio = (light + 0.05) / (dark + 0.05);
      if (ratio < 4.5) short.push(`${field.name || field.id}: ${ratio.toFixed(2)}`);
    }
    return short;
  });
}

const PUBLIC = [
  ["sign-in", "/sign-in"],
  ["no-access", "/sign-in/no-access"],
  ["privacy", "/privacy"],
] as const;

const SIGNED_IN = [
  ["jobs", () => "/jobs"],
  ["new job", () => "/jobs/new"],
  ["job", () => `/jobs/${jobId}`],
  ["candidate", () => `/jobs/${jobId}/candidates/${candidateId}`],
  ["correction", () => `/candidates/${candidateId}/edit`],
  ["review queue", () => "/review"],
  ["settings", () => "/settings"],
] as const;

for (const lang of ["ar", "en"] as const) {
  test.describe(`in ${lang}`, () => {
    for (const [name, route] of PUBLIC) {
      test(`the ${name} screen meets WCAG 2.1 AA`, async ({ page }) => {
        await page.goto(`/${lang}${route}`);
        await expectAccessible(page);
        expect(await faintPlaceholders(page)).toEqual([]);
      });
    }

    for (const [name, route] of SIGNED_IN) {
      test(`the ${name} screen meets WCAG 2.1 AA`, async ({ page }) => {
        await signIn(page, recruiter);
        await page.goto(`/${lang}${route()}`);
        await expect(page.locator("main")).toBeVisible();
        await expectAccessible(page);
        expect(await faintPlaceholders(page)).toEqual([]);
      });
    }
  });
}

test("the placeholder check finds the placeholders and catches a faint one", async ({ page }) => {
  await page.goto("/en/sign-in");
  await expect(page.getByPlaceholder("name@company.com")).toBeVisible();
  await page.addStyleTag({ content: "input::placeholder { color: #d4d4d4 !important; }" });
  expect(await faintPlaceholders(page)).not.toEqual([]);
});
