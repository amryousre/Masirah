# Contract: Web surface

What the Next.js application exposes. Two kinds of surface: pages a recruiter navigates, and server
routes the browser calls.

Every path sits beneath the `[lang]` root parameter, so `/ar/jobs` and `/en/jobs` are the same page
in two directions. The root layout sets the document direction from the locale, which is the single
place direction is decided.

## Pages

| Path | Purpose | Requirements |
|---|---|---|
| `/{lang}/sign-in` | Authentication | NFR-08 |
| `/{lang}/jobs` | List jobs in the organisation | FR-001 |
| `/{lang}/jobs/new` | Create a job, including pasting a free-text description | FR-001, FR-002 |
| `/{lang}/jobs/{jobId}` | Job detail with its ranked candidate list | FR-018, FR-013, FR-014 |
| `/{lang}/jobs/{jobId}/upload` | Batch upload against this job | FR-003 |
| `/{lang}/jobs/{jobId}/candidates/{candidateId}` | Profile, original file viewer, score breakdown, justification, for the candidate's application to this job | FR-012, FR-015, FR-016 |
| `/{lang}/candidates/{candidateId}/edit` | Correct extracted fields | FR-010 |
| `/{lang}/review` | Queue of low-confidence and failed documents | FR-011 |
| `/{lang}/settings` | Retention period, interface language, deletion request | FR-028, FR-029 |

The candidate page sits under its job (amended 2026-10-04, T066) because what it shows belongs to an application, not to the person: the score, the reasons, the rank and the previous and next candidates are all for one job. A candidate who never applied to the job is not found there. Correcting extracted fields stays at `/{lang}/candidates/{candidateId}/edit`, since the profile is the CV's and the same for every job.

## Server routes

| Route | Method | Purpose |
|---|---|---|
| `/api/uploads` | POST | Accept a batch of up to 25 files, store originals, create `cv_file` rows, enqueue one `cv_processing` message each |
| `/api/jobs/{jobId}/specification` | POST | Turn a pasted description into a structured specification for review (FR-002) |
| `/api/applications/{id}/decision` | POST | Record a shortlist or rejection with the acting user (FR-023) |
| `/api/candidates/{id}` | DELETE | Deletion request for one candidate's personal data (FR-029) |
| `/api/health` | GET | Liveness, including queue depth and worker last-seen |

## Rules

**Uploads, field by field.** `/api/uploads` takes `multipart/form-data`: `files` (repeated, 1 to 25),
`jobId` (optional, a job of the session's organisation, else 404) and `locale` (`ar` or `en`). It
answers 202 with one outcome per file: `queued` with its `cvFileId`, `rejected` with a `reason`
(`type`, `size` or `empty`), `failed` with the row marked failed so the file stays visible, or
`pending` when even marking it failed did not work: the row is still queued, and the worker's
reconciliation (`worker.requeue_stranded`) queues it again within minutes. A
file is judged by its first bytes as well as its name, the stored object name is ASCII
(`cv.pdf`) because Storage refuses other keys, and each file is at most 10 MiB.

**Uploads never process inline.** `/api/uploads` stores the file, writes the row, enqueues, and
returns. It must not wait for extraction. This is what keeps the batch target achievable and is the
reason the worker exists at all.

**Model keys never reach the browser.** Only server routes and the worker hold provider credentials.
The `/api/jobs/{jobId}/specification` route exists precisely so the browser never calls a provider
directly.

**Reads go straight to the database.** The candidate list, job list and candidate detail read
through the Supabase client with row level security applied, rather than being proxied through
bespoke routes. Writing a route for an ordinary read adds a layer that enforces nothing the database
is not already enforcing.

**Rejection carries an actor.** `/api/applications/{id}/decision` requires the authenticated user
and records them. There is no path, in the interface or the API, that sets a decision without one,
per AI-07. The body is `{ decision, reason? }`: `decision` is `shortlisted`, `rejected` or `undecided` (undoing either), and `reason` is required for a rejection and refused otherwise (`experience`, `skills`, `location` or `other`). A decider named in the body is ignored. Answers: 200 with `{ decision, decidedBy, decidedAt }`, 400 for an invalid body, 401 without a member session, 404 for an application the member cannot see (migration 0021).

**Every route validates tenancy.** The organisation is derived from the session, never from the
request body. A client-supplied organisation identifier is ignored.

**Batch limit is enforced server-side.** The 25-file limit in FR-003 is checked on the server, not
only in the browser.

## Health and observability

`/api/health` reports queue depth and the worker's last heartbeat. This is the cheapest early
warning that the worker has stopped, which would otherwise present as uploads that never finish.
Parse failure rate above five percent must alert, per NFR-14.
