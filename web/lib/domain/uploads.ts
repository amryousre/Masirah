// The batch ceiling for CV uploads (design-brief.md section 5): small enough to show every file's
// state at once. POST /api/uploads (T061) enforces it on the server; the interface states it.
export const MAX_BATCH_FILES = 25;
