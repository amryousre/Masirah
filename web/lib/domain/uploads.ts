// Which uploaded files become CVs (T061, FR-003, design-brief.md section 5).

/** The batch ceiling: small enough to show every file's state at once. Enforced on the server. */
export const MAX_BATCH_FILES = 25;

/** Matches the cv-originals bucket's limit (migration 0018). */
export const MAX_FILE_BYTES = 10 * 1024 * 1024;

/** How many leading bytes identify a file's kind. */
export const SIGNATURE_BYTES = 8;

interface Kind {
  mime: string;
  extension: string;
  names: readonly string[];
  signature: readonly number[];
}

// The formats FR-003 accepts, each recognised by its first bytes. DOCX is a zip archive.
const KINDS: readonly Kind[] = [
  {
    mime: "application/pdf",
    extension: "pdf",
    names: ["pdf"],
    signature: [0x25, 0x50, 0x44, 0x46],
  },
  {
    mime: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    extension: "docx",
    names: ["docx"],
    signature: [0x50, 0x4b, 0x03, 0x04],
  },
  {
    mime: "application/msword",
    extension: "doc",
    names: ["doc"],
    signature: [0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1],
  },
  { mime: "image/jpeg", extension: "jpg", names: ["jpg", "jpeg"], signature: [0xff, 0xd8, 0xff] },
  {
    mime: "image/png",
    extension: "png",
    names: ["png"],
    signature: [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a],
  },
];

export type FileRejection = "type" | "size" | "empty";

export type FileCheck =
  { ok: true; mime: string; extension: string } | { ok: false; reason: FileRejection };

/** A file is what its first bytes say, and only if its name agrees. */
export function checkFile(name: string, size: number, head: Uint8Array): FileCheck {
  if (size === 0) return { ok: false, reason: "empty" };
  if (size > MAX_FILE_BYTES) return { ok: false, reason: "size" };
  const extension = name.includes(".") ? name.slice(name.lastIndexOf(".") + 1).toLowerCase() : "";
  const kind = KINDS.find(
    (candidate) =>
      candidate.names.includes(extension) &&
      candidate.signature.every((byte, index) => head[index] === byte),
  );
  return kind === undefined
    ? { ok: false, reason: "type" }
    : { ok: true, mime: kind.mime, extension: kind.extension };
}

export function checkBatch(count: number): boolean {
  return count > 0 && count <= MAX_BATCH_FILES;
}

/**
 * The object's name inside its CV folder. Storage refuses keys with non-ASCII characters, so the
 * uploaded name, Arabic included, is kept in cv_file.original_filename instead.
 */
export function storedFileName(extension: string): string {
  return `cv.${extension}`;
}
