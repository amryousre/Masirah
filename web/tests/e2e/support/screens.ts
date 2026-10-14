import { expect, type Page } from "@playwright/test";

import ar from "../../../messages/ar.json" with { type: "json" };
import en from "../../../messages/en.json" with { type: "json" };
import {
  type Account,
  addFileInReview,
  addJob,
  addRankedCandidate,
  createAccount,
} from "./accounts";

// Every recruiter-facing screen, for the specs that hold all of them to one rule: the WCAG audit
// (T103) and the narrow-screen check (T104). Each screen is seeded with real data, so a list or a
// detail is measured as a recruiter sees it rather than empty.

export const MESSAGES = { ar, en };
export type Lang = keyof typeof MESSAGES;
export const LANGS = ["ar", "en"] as const;

export interface Seeded {
  account: Account;
  jobId: string;
  candidateId: string;
  fileId: string;
}

/** An organisation with a job, a ranked candidate and a file in the review queue. */
export async function seedScreens(organisation: string): Promise<Seeded> {
  const account = await createAccount(organisation);
  const jobId = await addJob(account, { title: "Senior Accountant", location: "Cairo" });
  const candidateId = await addRankedCandidate(account, jobId, {
    name: "Mona Abdallah",
    total: 82,
    justification: "Eight years of audit work at a listed company, and fluent English.",
    confidence: 0.94,
  });
  const fileId = await addFileInReview(account, {
    fileName: "scan_0187.pdf",
    jobId,
    status: "needs_review",
    reviewReason: "no_text",
  });
  return { account, jobId, candidateId, fileId };
}

export const PUBLIC_SCREENS = [
  ["sign-in", "/sign-in"],
  ["no-access", "/sign-in/no-access"],
  ["privacy", "/privacy"],
] as const;

export const SIGNED_IN_SCREENS: readonly (readonly [string, (seeded: Seeded) => string])[] = [
  ["jobs", () => "/jobs"],
  ["new job", () => "/jobs/new"],
  ["job", ({ jobId }) => `/jobs/${jobId}`],
  ["candidate", ({ jobId, candidateId }) => `/jobs/${jobId}/candidates/${candidateId}`],
  ["correction", ({ candidateId }) => `/candidates/${candidateId}/edit`],
  ["review queue", () => "/review"],
  ["review queue's chosen file", ({ fileId }) => `/review?file=${fileId}`],
  ["settings", () => "/settings"],
];

/** The screen asked for, not the not-found page a broken route would fall back to. */
export async function expectScreen(page: Page, lang: Lang) {
  await expect(page.locator("main")).toBeVisible();
  await expect(page.getByRole("heading", { name: MESSAGES[lang].notFound.title })).toHaveCount(0);
}
