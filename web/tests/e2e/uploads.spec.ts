import { readFileSync } from "node:fs";
import path from "node:path";

import { expect, test } from "@playwright/test";

import { type Account, addJob, createAccount } from "./support/accounts";
import { signIn } from "./support/pages";

// POST /api/uploads (T061) against the running app, its database, storage and queue: files are
// judged by their bytes, recorded, stored, queued and answered at once; the batch limit and the
// organisation are the server's to enforce.

const CORPUS = path.resolve(import.meta.dirname, "../../../pipeline/tests/fixtures/cvs");
const pdf = () => ({
  name: "سيرة ذاتية.pdf",
  mimeType: "application/pdf",
  buffer: readFileSync(path.join(CORPUS, "en-native-01.pdf")),
});

let recruiter: Account;
let stranger: Account;
let jobId: string;
let strangersJobId: string;

test.beforeAll(async () => {
  recruiter = await createAccount("Delta Soft");
  stranger = await createAccount("Elsewhere Ltd");
  jobId = await addJob(recruiter, { title: "Senior Accountant" });
  strangersJobId = await addJob(stranger, { title: "Someone Else's Job" });
});

test.afterAll(async () => {
  await recruiter.remove();
  await stranger.remove();
});

test("a CV uploaded for a job is queued at once and shows as being read", async ({ page }) => {
  await signIn(page, recruiter);
  const response = await page.request.post("/api/uploads", {
    multipart: { files: pdf(), jobId, locale: "en" },
  });
  expect(response.status()).toBe(202);
  const body = (await response.json()) as { files: { name: string; status: string }[] };
  expect(body.files).toEqual([
    expect.objectContaining({ name: "سيرة ذاتية.pdf", status: "queued" }),
  ]);

  await page.goto("/en/jobs");
  const row = page.getByRole("row", { name: /Senior Accountant/ });
  await expect(row).toContainText("0 of 1 ranked");
  await expect(row).toContainText("1 processing");
});

test("a file that is not what its name says is refused, and the rest of the batch goes on", async ({
  page,
}) => {
  await signIn(page, recruiter);
  const form = new FormData();
  form.append("files", new Blob(["not a pdf"], { type: "application/pdf" }), "fake.pdf");
  form.append("files", new Blob([pdf().buffer], { type: "application/pdf" }), "real.pdf");
  form.append("locale", "en");
  const response = await page.request.post("/api/uploads", { multipart: form });
  expect(response.status()).toBe(202);
  const body = (await response.json()) as {
    files: { name: string; status: string; reason?: string }[];
  };
  expect(body.files).toEqual([
    expect.objectContaining({ name: "fake.pdf", status: "rejected", reason: "type" }),
    expect.objectContaining({ name: "real.pdf", status: "queued" }),
  ]);
});

test("a batch above the limit is refused by the server", async ({ page }) => {
  await signIn(page, recruiter);
  const form = new FormData();
  for (let n = 0; n < 26; n += 1) {
    form.append(
      "files",
      new Blob([pdf().buffer], { type: "application/pdf" }),
      `cv-${String(n)}.pdf`,
    );
  }
  form.append("locale", "en");
  const response = await page.request.post("/api/uploads", { multipart: form });
  expect(response.status()).toBe(400);
  expect(await response.json()).toEqual({ error: "too-many-files", max: 25 });
});

test("another organisation's job is not there to upload to", async ({ page }) => {
  await signIn(page, recruiter);
  const response = await page.request.post("/api/uploads", {
    multipart: { files: pdf(), jobId: strangersJobId, locale: "en" },
  });
  expect(response.status()).toBe(404);
});

test("a visitor who has not signed in cannot upload", async ({ request }) => {
  const response = await request.post("/api/uploads", {
    multipart: { files: pdf(), locale: "en" },
  });
  expect(response.status()).toBe(401);
});
