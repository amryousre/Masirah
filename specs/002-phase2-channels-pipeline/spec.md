# Feature Specification: Phase 2 Channels and Pipeline

**Feature Branch**: `002-phase2-channels-pipeline`

**Created**: 2026-09-11

**Status**: Draft, forward-looking

**Input**: Written as part of specifying all four phases up front, to give a clear picture of the
whole product before building begins.

Phase 1 proves that a pile of CVs can become a defensible ranking. Phase 2 removes the manual
labour around it. CVs arrive on their own, candidates move through a pipeline, the team works
together, and the screening layer that is the product's actual differentiator arrives.

**Exit criterion**: pilot companies stop uploading manually.

> **This is a forward-looking specification.** Phase 1 has not been built yet. Everything here
> rests on assumptions Phase 1 will test, particularly about extraction quality and how recruiters
> actually behave once they have a ranking. Expect to revise this before starting Phase 2, and
> treat its detail as a considered sketch rather than a contract.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CVs arrive without anyone uploading them (Priority: P1)

Nourhan stops downloading attachments. She forwards her `careers@` mail to the address Masirah gave
her, and the candidates simply appear. The applicants who send a CV to the company WhatsApp number
appear too, which today are the ones most often lost. When the same person applies through two
channels, she sees one candidate rather than two.

**Why this priority**: This is the phase's exit criterion in a single story. Until intake is
automatic, Phase 1 remains a better spreadsheet rather than a system.

**Independent Test**: Forward a mixture of emails to the account address and send CVs to the
connected WhatsApp number. Confirm candidates appear without anyone touching the upload screen, and
that a person who applied twice appears once.

**Acceptance Scenarios**:

1. **Given** an account with its unique forwarding address, **When** a CV is emailed or forwarded to
   it, **Then** the candidate is created and processed exactly as an upload would have been.
2. **Given** an email carrying several attachments, **When** it is ingested, **Then** each CV
   attachment becomes its own candidate and non-CV attachments are ignored rather than parsed.
3. **Given** an email whose body links to a file on Google Drive or Dropbox instead of attaching it,
   **When** it is ingested, **Then** the linked document is retrieved and processed.
4. **Given** a connected WhatsApp Business number, **When** a candidate sends a CV as a document or
   a photograph, **Then** it is ingested and linked to the sender's phone number.
5. **Given** the same person applying by email and again by WhatsApp, **When** both arrive, **Then**
   the system recognises them as one candidate through email, phone number or content fingerprint,
   and merges rather than duplicating.
6. **Given** a merged candidate, **When** the recruiter views them, **Then** every source channel and
   every original file remains visible, and the merge can be undone if it was wrong.

---

### User Story 2 - Move candidates through a hiring process (Priority: P1)

Nourhan stops tracking stages in a spreadsheet beside the tool. Each job has its own stages. She
drags candidates between them, acts on twenty at once instead of one at a time, and can see
everything that has happened to a candidate in one place.

**Why this priority**: Automatic intake without a pipeline just produces a larger pile. These two
stories together are what make Phase 2 worth shipping.

**Independent Test**: Configure stages on a job, move candidates through them individually and in
bulk, and confirm the activity timeline records every change with who made it and when.

**Acceptance Scenarios**:

1. **Given** a job, **When** the recruiter configures its stages, **Then** those stages apply to that
   job without affecting any other.
2. **Given** a job with stages, **When** the recruiter opens the board view, **Then** candidates
   appear in their current stage and can be dragged between stages.
3. **Given** a filtered selection of candidates, **When** the recruiter applies a bulk action,
   **Then** shortlisting, rejecting, tagging, stage moves and emailing all apply to the whole
   selection.
4. **Given** any candidate, **When** the recruiter opens their timeline, **Then** every status
   change, message and note appears in order with its actor and timestamp.
5. **Given** a bulk rejection, **When** it is applied, **Then** a human actor is recorded for every
   affected candidate, exactly as for a single rejection.

---

### User Story 3 - Screen deeper than a CV allows (Priority: P2)

Tarek stops writing screening questions from scratch. The system reads the job specification and
proposes questions with expected answer indicators, a structured scorecard with weighted
competencies, and for each individual candidate a few probing questions aimed at the gaps in that
person's own CV.

**Why this priority**: This is the differentiator the BRD is built around, the thing competitors do
not do. It is P2 only because intake and pipeline must exist for anyone to reach it.

**Independent Test**: Generate screening questions and a scorecard from a job specification, then
generate candidate-specific probes for two very different CVs and confirm the questions actually
differ in a way that reflects each CV.

**Acceptance Scenarios**:

1. **Given** a job specification, **When** the recruiter requests screening questions, **Then** the
   system produces role-specific questions each carrying an indicator of what a good answer contains.
2. **Given** a job specification, **When** the recruiter requests a scorecard, **Then** it contains
   weighted competencies and a rating scale, and is editable before use.
3. **Given** a specific candidate with gaps or ambiguities in their history, **When** probing
   questions are generated, **Then** they reference that candidate's own CV rather than being
   generic to the role.
4. **Given** generated questions, **When** the recruiter edits them, **Then** the edits are kept and
   reused rather than regenerated away.

---

### User Story 4 - Reply to candidates without leaving the tool (Priority: P2)

Every applicant gets an acknowledgement, which is the single thing candidates complain about most.
Rejections go out on a delay the recruiter controls, in the candidate's own language, without
anyone writing them individually.

**Why this priority**: Candidate experience is named in the BRD as a deliberate differentiator, and
acknowledgement is the cheapest part of it. It sits below pipeline because there must be stages
before stage-triggered messages mean anything.

**Independent Test**: Send a bulk email to a filtered selection, and confirm acknowledgements fire
on receipt and rejections fire on stage change after the configured delay.

**Acceptance Scenarios**:

1. **Given** an account with templates in Arabic and English, **When** a message is composed, **Then**
   merge variables resolve correctly in both directions of text.
2. **Given** a filtered selection, **When** the recruiter sends a bulk email, **Then** it is delivered
   at a controlled rate with deliverability safeguards, and failures are visible rather than silent.
3. **Given** a new application from any channel, **When** it is received, **Then** the candidate gets
   an acknowledgement automatically.
4. **Given** a candidate moved to a rejected stage, **When** the configured delay elapses, **Then** a
   rejection notification is sent, and the recruiter can cancel it during the delay.

---

### User Story 5 - Work as a team rather than alone (Priority: P3)

The hiring manager gets access to his own job and nothing else. Interviewers see a scorecard and no
salary discussion. Notes and mentions replace the side conversation in WhatsApp.

**Why this priority**: Phase 1 and 2 pilots are single-user. This matters for the accounts that
follow, and it is a prerequisite for selling in Phase 3.

**Independent Test**: Invite a hiring manager scoped to one job and confirm from their session that
no other job is reachable.

**Acceptance Scenarios**:

1. **Given** an owner, **When** they invite a user as Recruiter, Hiring Manager or Interviewer,
   **Then** that user sees exactly what their role permits and no more.
2. **Given** a Hiring Manager scoped to one job, **When** they sign in, **Then** other jobs and their
   candidates are unreachable by any route, enforced at the data layer.
3. **Given** a candidate, **When** a team member writes a note and mentions a colleague, **Then** the
   colleague is notified and the note appears on the timeline.
4. **Given** tags and filters used repeatedly, **When** the recruiter saves a filter, **Then** it is
   reusable across jobs.
5. **Given** a candidate selection, **When** the recruiter exports, **Then** CSV, Excel and formats
   importable by Workable and Greenhouse are produced, and the export is recorded in the audit log.

---

### User Story 6 - Tune the ranking to match judgement (Priority: P3)

The first ranking is rarely exactly right. Tarek raises the weight on hands-on experience, lowers it
on education, and the list reorders without every CV being read again. He also wants the system to
point at contradictions rather than leaving him to notice them.

**Why this priority**: Valuable but not blocking. It refines a loop that already works.

**Independent Test**: Change the component weights on a job and confirm the ranking recomputes
without re-parsing any CV, and that the original scores remain retrievable.

**Acceptance Scenarios**:

1. **Given** a scored job, **When** the recruiter changes component weights, **Then** candidates are
   rescored from existing parsed profiles with no new extraction cost.
2. **Given** a candidate scored for one job, **When** the recruiter scores them against another job
   in the account, **Then** a new score is produced without re-parsing.
3. **Given** a CV with overlapping employment dates or a qualification lacking an institution,
   **When** it is analysed, **Then** the contradiction is flagged explicitly rather than silently
   scored.
4. **Given** any rescoring, **When** it completes, **Then** the earlier score remains retrievable
   with its own model identity and prompt version.

---

### Edge Cases

- A spam or marketing email reaches the forwarding address. It must not become a candidate.
- Someone forwards a thread containing several CVs from different people in one message.
- A candidate sends a CV by WhatsApp as six separate photographs, one per page.
- A WhatsApp message arrives with no document at all, just text saying "I want to apply".
- Two different people share a phone number, such as a family handset, so phone-based merging is
  wrong. The merge must be reversible.
- A Google Drive link in an email body is private and cannot be fetched.
- A bulk email selection is 3,000 candidates, large enough to threaten sender reputation.
- A rejection notification is queued behind a delay and the recruiter moves the candidate back.
- A hiring manager is removed from the account while holding the only notes on a candidate.
- WhatsApp template approval is refused or the per-message cost changes, which the BRD records as
  risk R-04.

## Requirements *(mandatory)*

Numbering is local to this specification. The traceability table maps each item to the BRD.

- **FR-001**: Each account MUST be issued a unique forwarding address, and CVs sent there MUST be
  ingested automatically.
- **FR-002**: System MUST extract CVs from email attachments and from Google Drive or Dropbox links
  in the message body.
- **FR-003**: Accounts MUST be able to connect a WhatsApp Business number and receive CVs sent as
  documents or images, linked to the sender's number.
- **FR-004**: System MUST deduplicate candidates across channels using email, phone number and
  content fingerprint, merging rather than duplicating, and merges MUST be reversible.
- **FR-005**: System MUST record the source channel of every application at the moment it arrives.
  Reporting on channel quality is BRD FR-008 and belongs to Phase 3, but the recording cannot wait,
  because a channel not captured at intake is lost permanently.
- **FR-006**: Users MUST be able to configure pipeline stages per job and move candidates between
  them, including by dragging on a board.
- **FR-007**: Users MUST be able to apply bulk actions to a filtered selection: shortlist, reject,
  tag, change stage and email.
- **FR-008**: System MUST maintain a complete activity timeline per candidate showing every change
  with actor and timestamp.
- **FR-009**: Users MUST be able to leave notes and mention colleagues on a candidate.
- **FR-010**: Users MUST be able to create tags and save filters that are reusable across jobs.
- **FR-011**: System MUST generate role-specific screening questions with expected answer indicators.
- **FR-012**: System MUST generate a structured interview scorecard with weighted competencies and a
  rating scale.
- **FR-013**: System MUST generate candidate-specific probing questions derived from gaps in that
  individual CV.
- **FR-014**: System MUST provide bilingual message templates with merge variables per account.
- **FR-015**: System MUST send bulk email to a filtered selection with rate limiting and
  deliverability safeguards.
- **FR-016**: System MUST send an automatic acknowledgement to every candidate on receipt.
- **FR-017**: System MUST send an automatic rejection notification triggered by stage change after a
  configurable delay, cancellable during that delay.
- **FR-018**: System MUST support roles of Owner, Recruiter, Hiring Manager scoped to their own jobs
  with read and comment rights, and Interviewer limited to scorecards.
- **FR-019**: Users MUST be able to export candidate data as CSV, Excel and formats importable by
  Workable and Greenhouse.
- **FR-020**: Users MUST be able to adjust component weights per job and rescore without re-parsing.
- **FR-021**: Users MUST be able to score any candidate against any other job in the account.
- **FR-022**: System MUST flag gaps, contradictions and unverifiable claims, such as overlapping
  employment dates or a qualification without an institution.

### Key Entities

Phase 1 entities continue. New in this phase:

- **Pipeline stage**: A configurable stage belonging to one job, with an order.
- **Message**: An email or WhatsApp message sent to a candidate, linked to the candidate and the
  template used.
- **Template**: A reusable message body per language, per organisation.
- **Tag**: A label applied to candidates, reusable across jobs.
- **Note**: Free text on a candidate, with an author, optionally mentioning other users.
- **Screening question set**: Questions generated for a job or a candidate, editable and retained.
- **Scorecard template**: Weighted competencies and rating scale generated for a job.
- **Channel source**: Records which channel an application arrived through, for FR-005.

## Success Criteria *(mandatory)*

- **SC-001**: Pilot companies stop uploading CVs manually. This is the phase exit criterion.
- **SC-002**: At least 95 percent of inbound CVs are ingested automatically without manual upload.
- **SC-003**: Duplicate candidates across channels are merged rather than duplicated in at least 95
  percent of cases, with no incorrect merge that cannot be undone.
- **SC-004**: Every applicant receives an acknowledgement, without exception.
- **SC-005**: A recruiter can act on a hundred candidates in a single operation rather than one at a
  time.
- **SC-006**: Changing component weights reorders a ranking without incurring any new extraction
  cost.
- **SC-007**: A Hiring Manager scoped to one job cannot reach any other job by any route.
- **SC-008**: Screening questions generated for two different candidates on the same job are
  demonstrably different and reference each candidate's own history.
- **SC-009**: Bulk email to a large selection completes without triggering spam classification.

## Assumptions

- Phase 1 has shipped and its accuracy gates have been met. If extraction quality falls short, this
  specification is premature rather than merely delayed.
- The forwarding address is the primary automatic channel. WhatsApp is additive, per risk R-04,
  because template approval and per-message cost are outside the project's control.
- Gmail and Outlook mailbox synchronisation is **not** in this phase. It is Phase 3, because Google's
  restricted-scope verification takes six to ten weeks and must never be a dependency.
- Deduplication operates within one organisation only. Candidates are never matched across tenants.
- Roles are fixed rather than customisable. Custom permission sets are not in scope.
- Data deletion and the access audit log, which the BRD places in this phase and the next, were
  pulled into Phase 1 by the pilot data decision in ADR 0003 and are therefore absent here.
- Intake remains Arabic and English only, per ADR 0005. Automatic channels do not widen the
  supported languages.

## Traceability to the BRD

| BRD | Requirement | Spec | Story |
|---|---|---|---|
| FR-002 | Unique forwarding address | FR-001 | US1 |
| FR-003 | Email attachments and cloud links | FR-002 | US1 |
| FR-005 | WhatsApp Business intake | FR-003 | US1 |
| FR-006 | Cross-channel deduplication | FR-004 | US1 |
| FR-008 | Source channel recorded (reporting stays in Phase 3) | FR-005 | US1 |
| FR-051 | Configurable pipeline stages, board view | FR-006 | US2 |
| FR-052 | Bulk actions on a filtered selection | FR-007 | US2 |
| FR-055 | Full activity timeline | FR-008 | US2 |
| FR-053 | Notes and mentions | FR-009 | US5 |
| FR-054 | Tags and saved filters | FR-010 | US5 |
| FR-040 | Screening questions with answer indicators | FR-011 | US3 |
| FR-041 | Structured interview scorecard | FR-012 | US3 |
| FR-043 | Candidate-specific probing questions | FR-013 | US3 |
| FR-060 | Bilingual templates with merge variables | FR-014 | US4 |
| FR-061 | Bulk email with rate limiting | FR-015 | US4 |
| FR-064 | Automatic acknowledgement | FR-016 | US4 |
| FR-065 | Delayed automatic rejection | FR-017 | US4 |
| FR-071 | Roles and permissions | FR-018 | US5 |
| FR-075 | Data export | FR-019 | US5 |
| FR-025 | Adjustable weights and rescoring | FR-020 | US6 |
| FR-026 | Rescore against another job | FR-021 | US6 |
| FR-028 | Flag gaps and contradictions | FR-022 | US6 |

All twenty-one Phase 2 requirements are covered. Two entries need explanation.

**FR-008 remains a Phase 3 requirement.** It appears here only as the data-capture half, because
the source channel must be written at intake or it is lost forever, whereas the report built on it
can wait. No requirement has been moved between phases. If you would rather move FR-008 wholesale
into Phase 2, say so and I will change the BRD rather than let the two documents drift.

**FR-076, account-level data deletion, is absent** because ADR 0003 moved it into Phase 1, along
with retention purge and the access audit log, when real pilot data was brought forward.
