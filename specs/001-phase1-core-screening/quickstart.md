# Quickstart: Phase 1 Core Screening

**Date**: 2026-09-11

How to run Phase 1 locally and prove it works. Validation scenarios below map to the user stories
in [spec.md](./spec.md) and the success criteria they satisfy. Entity shapes are in
[data-model.md](./data-model.md); the boundaries between the two runtimes are in
[contracts/](./contracts/).

## Prerequisites

| Requirement | Notes |
|---|---|
| Node 22 and npm | For `web/` |
| Python 3.12 | For `pipeline/` |
| Supabase CLI | Local database and migrations |
| Tesseract with Arabic language data | OCR fallback path |
| Anthropic API key | Required |
| OpenAI API key | Required, because both providers run from day one per decision Q5 |
| Anonymised CV corpus | Committed under `pipeline/tests/fixtures/cvs/` |

The corpus is not optional. Without it the accuracy suite cannot run, and the accuracy suite is the
Phase 1 release gate.

## Setup

1. **Start the database and apply migrations.** The first migration creates every table with its
   `organisation_id` column and row level security enabled. A migration that adds a table without
   both is a defect.
2. **Create the storage bucket** for original CV files, private, with access mediated by row level
   security rather than public URLs.
3. **Create the queues.** `cv_processing` and `cv_rescoring`, as named in
   [contracts/queue-message.md](./contracts/queue-message.md).
4. **Configure environment** for both runtimes. The web application needs the Supabase URL and
   publishable key plus its service credentials for server routes. The worker needs Supabase
   credentials and both provider keys. No provider key belongs in any variable the browser can read.
5. **Seed one organisation and one user.** Phase 1 has no signup flow; that arrives in Phase 3 with
   FR-080.

## Running

Two processes, both required. Uploading with the worker stopped leaves files queued forever, which
is the expected behaviour and is visible on `/api/health`.

| Component | What it does |
|---|---|
| `web/` dev server | Interface and server routes, on the usual Next.js port |
| `pipeline/` worker | Long-running consumer, polls `cv_processing`, exits non-zero on fatal config errors |

## Validation scenarios

### 1. The core loop (User Story 1)

Create a job with a title, required skills and a minimum experience level. Upload a batch of native
PDF and DOCX CVs in Arabic and English. Wait for processing.

**Expect**: every file reaches `extracted`. The job page lists candidates ordered best first. Each
carries a total out of 100, six components, a written justification quoting evidence from that CV,
and a three to five line summary. Opening a candidate shows the original file next to the extracted
fields.

**Proves**: SC-001, SC-005. Covers FR-001 through FR-004, FR-006 through FR-009, FR-012 through
FR-016, FR-018.

### 2. Reading order, mixed language, and unsupported languages

Include a two-column CV, one mixing Arabic and English inside a single document, one written wholly
in French, and one English CV carrying a few French lines such as a course title.

**Expect**: the two-column CV extracts in human reading order rather than interleaving columns. The
Arabic and English mixed document extracts without any language being selected first. Hijri dates
and Arabic-Indic numerals appear normalised. The French CV is flagged as an unsupported language in
the review queue, visibly distinct from a document that was merely scanned badly. The English CV
with a few French lines parses normally and is not flagged.

**Proves**: the hardest part of SC-002, plus SC-015. That last case is the one that catches an
over-eager language detector, which would otherwise reject perfectly supported CVs.

### 3. Photographs and the review queue (User Story 2)

Upload a scanned PDF, a clean phone photograph, a deliberately skewed one, and a deliberately
unreadable one.

**Expect**: the readable images extract. The unreadable one appears in `/review` with its original
attached and a stated reason. Nothing vanishes. Correcting a field on any candidate persists, and
re-running extraction does not discard the correction.

**Proves**: SC-003, SC-006. Covers FR-005, FR-010, FR-011.

### 4. Fairness and auditability (User Story 3)

Take one CV. Produce a copy differing only in name, gender and nationality. Score both against the
same job.

**Expect**: scores fall within the defined tolerance. Inspecting either score shows the provider,
model identifier, prompt version and input hash. The input hash covers the redacted text, so it can
be shown that protected attributes never reached the model. No interface path rejects a candidate
without recording the acting user.

**Proves**: SC-011. Covers FR-017, FR-020, FR-021, FR-023, FR-024.

### 5. Tenant isolation (User Story 4)

Create a second organisation with its own candidates. Sign in as the first organisation's user and
attempt to reach the second organisation's records, by identifier, by list query and by direct
storage path.

**Expect**: nothing is reachable by any route. Verify the block is coming from row level security by
confirming the same query fails with application-layer filtering removed.

**Proves**: FR-019 and NFR-07. A test that only proves the interface hides other tenants' data has
not tested isolation.

### 6. Cost and throughput budgets

Process a batch of 100 CVs. Then re-upload ten files already processed.

**Expect**: the batch finishes within 10 minutes. Recorded cost per CV stays at or below 2.5 EGP.
The re-uploaded files produce no new inference cost, because the content hash matched.

**Proves**: SC-007, SC-008, SC-010. Covers the caching requirement in FR-022.

### 7. Both interface languages

Load any screen in English, then switch to Arabic.

**Expect**: the full layout mirrors, including forms, tables and the score breakdown. No hard-coded
string survives the switch. Justifications generated while the interface is Arabic are written in
Arabic. The page remains usable at 360 pixels wide.

**Proves**: SC-012. Covers FR-027.

## The release gate

Separate from the scenarios above, and the reason Phase 1 cannot be declared done by inspection.

The accuracy suite under `pipeline/tests/accuracy/` runs the committed corpus through extraction and
compares every field against the labelled ground truth. It is a gate, not a test: Phase 1 does not
exit until it reports at least 95 percent field accuracy on native PDFs and 85 percent on scanned
and photographed CVs, per SC-002 and SC-003.

The gate covers Arabic and English, which are the only supported languages in version 1.0. Do not
widen the supported set without first adding labelled CVs for the new language, because a supported
language with no corpus behind it is an unmeasured promise.

Build this suite first, before the interface. If those numbers turn out to be unreachable, the
extraction approach has to change, and it is far cheaper to discover that with nothing built on top
of it. The plan's research notes record that no real Egyptian CV has yet been run through any
extraction pipeline, which makes this the largest unretired risk in the phase.
