import { describe, expect, it } from "vitest";

import {
  checkBatch,
  checkFile,
  MAX_BATCH_FILES,
  MAX_FILE_BYTES,
  storedFileName,
} from "@/lib/domain/uploads";

// Which uploaded files become CVs (T061, FR-003). A file is judged by its first bytes, not its
// name: a renamed archive is not a PDF because it ends in .pdf.
const bytes = (...values: number[]) =>
  new Uint8Array([...values, ...new Array<number>(16).fill(0)]);
const PDF = bytes(0x25, 0x50, 0x44, 0x46, 0x2d);
const ZIP = bytes(0x50, 0x4b, 0x03, 0x04);
const OLE = bytes(0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1);
const JPEG = bytes(0xff, 0xd8, 0xff);
const PNG = bytes(0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a);

describe("a file", () => {
  it.each([
    ["cv.pdf", PDF, "application/pdf", "pdf"],
    ["سيرة ذاتية.PDF", PDF, "application/pdf", "pdf"],
    [
      "cv.docx",
      ZIP,
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "docx",
    ],
    ["cv.doc", OLE, "application/msword", "doc"],
    ["photo.jpg", JPEG, "image/jpeg", "jpg"],
    ["photo.jpeg", JPEG, "image/jpeg", "jpg"],
    ["scan.png", PNG, "image/png", "png"],
  ])("%s is accepted as what its bytes say", (name, head, mime, extension) => {
    expect(checkFile(name, head.length, head)).toEqual({ ok: true, mime, extension });
  });

  it("is refused when its bytes are not what its name claims", () => {
    expect(checkFile("cv.pdf", ZIP.length, ZIP)).toEqual({ ok: false, reason: "type" });
  });

  it("is refused when it is of a kind no CV comes in", () => {
    expect(checkFile("cv.txt", PDF.length, PDF)).toEqual({ ok: false, reason: "type" });
  });

  it("is refused when empty", () => {
    expect(checkFile("cv.pdf", 0, new Uint8Array())).toEqual({ ok: false, reason: "empty" });
  });

  it("is refused above the size limit", () => {
    expect(checkFile("cv.pdf", MAX_FILE_BYTES + 1, PDF)).toEqual({ ok: false, reason: "size" });
  });
});

describe("a batch", () => {
  it("holds up to the limit", () => {
    expect(checkBatch(MAX_BATCH_FILES)).toBe(true);
    expect(checkBatch(MAX_BATCH_FILES + 1)).toBe(false);
  });

  it("is not empty", () => {
    expect(checkBatch(0)).toBe(false);
  });
});

describe("the stored name", () => {
  it("is ASCII whatever the uploaded name, since Storage refuses other keys", () => {
    expect(storedFileName("pdf")).toBe("cv.pdf");
  });
});
