# Feature Specification: Phase 1 Core Screening

**Feature Branch**: `001-phase1-core-screening`

**Created**: 2026-09-11

**Status**: Draft

**Input**: User description: "check the brd with the full requirment"

This specification covers **Phase 1 of the Masirah BRD in full**. Every requirement the BRD assigns
to Phase 1 is traced to a user story below, and the traceability table at the end proves complete
coverage. Later phases receive their own specifications.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Screen a batch of CVs against a job (Priority: P1)

Nourhan is the only HR person at a 60-person company. She has a mid-level vacancy and roughly 300
CVs sitting in a folder on her laptop. Today she opens them one at a time and gives up around the
fortieth. Instead, she describes the role once, drops a batch of CV files onto the screen, and
comes back to a list of candidates ordered best-first, each with a score, a breakdown of how that
score was reached, and a short written explanation quoting the parts of the CV that justify it. She
reads the top fifteen instead of all three hundred.

**Why this priority**: This is the entire product loop. Delivered alone it already replaces the
spreadsheet, which the BRD names as the real incumbent. Nothing else in Phase 1 has value without
it.

**Independent Test**: Create a job, upload a batch of native PDF and DOCX CVs in Arabic and
English, and confirm a ranked list appears where each entry carries a score, a component
breakdown, a short summary and a written justification citing evidence from that CV.

**Acceptance Scenarios**:

1. **Given** a recruiter with no jobs yet, **When** she creates a job with a title, description,
   required and preferred skills, minimum experience, location and language requirement, **Then**
   the job is saved and available to score candidates against.
2. **Given** a saved job, **When** the recruiter pastes a free-text job description instead of
   filling fields individually, **Then** the system proposes a structured job specification she can
   review and accept.
3. **Given** a saved job, **When** the recruiter drops up to 25 CV files of mixed type onto the
   upload area, **Then** every file is accepted and queued, and progress is visible per file.
4. **Given** a queued native PDF with a two-column layout, **When** parsing completes, **Then** the
   extracted text follows human reading order rather than interleaving the columns.
5. **Given** a parsed CV, **When** the recruiter opens the candidate, **Then** she sees name,
   contact details, location, years of experience, dated employment history, education, skills,
   languages and certifications, alongside the original file rendered on screen.
6. **Given** a CV written in Arabic, in English, or mixing both inside one document, **When** it is
   parsed, **Then** extraction succeeds without the recruiter selecting a language first.
7. **Given** a CV written in neither Arabic nor English, **When** it is processed, **Then** it is
   flagged as an unsupported language and placed in the review queue, distinguishable from a
   document that merely parsed with low confidence.
8. **Given** a parsed CV containing Hijri dates or Arabic-Indic numerals, **When** extraction
   completes, **Then** dates and numbers are normalised to a single comparable form.
9. **Given** a batch parsed against a job, **When** scoring completes, **Then** each candidate
   carries a score from 0 to 100 broken into skills match, experience relevance, education, tenure
   stability, language and location.
10. **Given** a scored candidate, **When** the recruiter reads the result, **Then** a written
    justification appears in her interface language, citing specific evidence drawn from that CV,
    plus a summary of three to five lines.
11. **Given** a scored batch, **When** the recruiter opens the candidate list, **Then** she can
    sort, filter and search across extracted fields in both Arabic and English.
12. **Given** the interface in English, **When** the recruiter switches to Arabic, **Then** the
    full layout mirrors to right-to-left and all text appears in Arabic.

---

### User Story 2 - Get value from CVs that arrive as photographs (Priority: P2)

Many Egyptian candidates apply with a photograph of a printed CV taken on a phone, often skewed and
poorly lit. Today those are the CVs that get skipped. Nourhan uploads them alongside the rest. Most
are read successfully. The handful that defeat the system are put in front of her in a review queue
with whatever was extracted, so she can correct the fields rather than lose the candidate.

**Why this priority**: Story 1 is viable on native files alone, so this is genuinely separable. But
without it a large share of real Egyptian applications silently fall out of the pipeline, which is
one of the consequences the BRD sets out to eliminate.

**Independent Test**: Upload a set of scanned PDFs and phone photographs, including deliberately
skewed and dim ones, and confirm each either parses into a structured profile or appears in the
review queue. None disappear.

**Acceptance Scenarios**:

1. **Given** a scanned PDF or a phone photograph of a printed CV, **When** it is processed, **Then**
   text is recovered and a structured profile is produced.
2. **Given** a photograph that is skewed or poorly lit, **When** it is processed, **Then** the
   system still attempts recovery rather than rejecting the file on sight.
3. **Given** a document the system could not parse with confidence, **When** processing finishes,
   **Then** it is flagged and placed in a manual review queue, never silently discarded.
4. **Given** a candidate with a wrongly extracted field, **When** the recruiter edits that field,
   **Then** the correction is saved and survives any later reprocessing of the same file.

---

### User Story 3 - Trust that the scoring is fair and auditable (Priority: P2)

Tarek, the engineering manager, does not trust shortlists he did not build. He wants to know what
the ranking was based on and to be certain it was not based on a candidate's name, age or gender.
He also needs to know that nothing was rejected without a person deciding to reject it.

**Why this priority**: Without this the product is legally exposed and commercially unconvincing.
The BRD records the risk of a customer facing a discrimination claim, and the constitution makes
these controls non-negotiable. It ranks below Story 1 only because there must be a ranking before
there is a ranking to audit.

**Independent Test**: Submit two CVs identical in every respect except name, gender and
nationality, and confirm the scores fall within the defined tolerance. Separately, confirm no
interface path rejects a candidate without a deliberate human action.

**Acceptance Scenarios**:

1. **Given** a CV containing name, gender, age, photograph, nationality and marital status, **When**
   it is scored, **Then** none of those attributes form part of the scoring input, and an automated
   test demonstrates the exclusion.
2. **Given** two CVs differing only in name, gender or nationality, **When** both are scored against
   the same job, **Then** the scores fall within the defined tolerance.
3. **Given** any completed score, **When** it is inspected later, **Then** the model identity,
   prompt version and input fingerprint are retrievable so the result can be reproduced.
4. **Given** a low-scoring candidate, **When** the recruiter views the list, **Then** the interface
   never presents the score as an automatic decision, and rejecting the candidate requires an
   explicit human action.
5. **Given** any model interaction, **When** a response is returned, **Then** it is consumed through
   a declared output schema rather than by interpreting free text.
6. **Given** candidate data sent to a model provider, **When** the arrangement with that provider is
   inspected, **Then** it contractually forbids the data being used to train their models, and the
   privacy policy states this to candidates.
7. **Given** an organisation that reaches its processing limit or spending ceiling, **When** further
   work is submitted, **Then** processing halts for that organisation rather than continuing to
   accrue cost.

---

### User Story 4 - Keep pilot data isolated, retained lawfully and deletable (Priority: P3)

The pilot company uploads CVs belonging to its own applicants. Those are real people. Their data
must stay separated from any other account, must not be kept indefinitely, must be removable on
request, and every access to it must leave a trace.

**Why this priority**: These controls were originally Phase 2 features. They move into Phase 1
because the decision to let the pilot company act as data controller puts real personal data into
the system during Phase 1. They rank last because the earlier stories can be built and tested
against anonymised data before any pilot data arrives.

**Independent Test**: Create two organisations, load candidates into each, and confirm from a
signed-in session in one that no record from the other is reachable by any route. Then request
deletion for a candidate and confirm the personal data is gone within the stated window.

**Acceptance Scenarios**:

1. **Given** two separate organisations, **When** a user signed into one attempts to reach a record
   belonging to the other, **Then** the record is unreachable, and isolation is enforced by the data
   store itself rather than by interface logic alone.
2. **Given** candidate data older than the configured retention period, **When** the retention
   process runs, **Then** the personal data is purged automatically.
3. **Given** a deletion request for an account, **When** it is actioned, **Then** candidate personal
   data is removed within 30 days.
4. **Given** any access to or export of candidate data, **When** it occurs, **Then** an immutable
   record is written showing who did what and when.

---

### Edge Cases

- A file is password-protected, corrupt, or zero bytes. It must surface as a clear failure in the
  review queue, not as a silent drop or a crash.
- A photograph is too dark or blurred for any text to be recovered. The candidate must still appear
  for manual entry with the original image attached.
- The uploaded file is not a CV at all, such as a certificate, an invoice or a cover letter. The
  system must flag low confidence rather than fabricate a profile.
- A CV is 40 pages long, or is a design portfolio that is mostly images.
- A CV is written in a language outside the supported set, such as French or Tagalog. It must be
  flagged as unsupported rather than silently mis-parsed, and the recruiter must be able to tell
  that case apart from a document that was in a supported language but scanned too poorly to read.
- A CV is mostly English with a few lines of a third language. Language detection must not flag the
  whole document as unsupported on the strength of a minority of its text.
- A CV contains no contact details at all.
- The same person applies twice with two different file formats. Phase 1 has no deduplication, so
  two records will exist. This is a known and accepted limitation until Phase 2.
- Two different candidates share an identical Arabic name.
- The job description is written in one language and the CVs arrive in another.
- The model provider becomes unavailable part-way through a batch. Completed work must be retained
  and the remainder resumable without re-charging for what already succeeded.
- The same file is uploaded a second time. It must not incur fresh processing cost.
- A batch is uploaded while a previous batch is still processing.

## Requirements *(mandatory)*

### Functional Requirements

Numbering below is local to this specification. The traceability table maps each item to the BRD
requirement it satisfies.

- **FR-001**: Users MUST be able to create a job carrying a title, description, required skills,
  preferred skills, minimum experience, location and language requirement.
- **FR-002**: System MUST be able to produce a structured job specification from a pasted free-text
  job description, for the user to review before saving.
- **FR-003**: Users MUST be able to submit multiple CV files at once, up to 25 per batch, accepting
  PDF, DOCX, DOC, JPG and PNG.
- **FR-004**: System MUST extract text from native PDF and DOCX files while preserving human reading
  order in multi-column layouts.
- **FR-005**: System MUST recover text from scanned documents and photographed CVs, including
  skewed and poorly lit phone photographs.
- **FR-006**: System MUST process Arabic, English and mixed Arabic/English CVs without the user
  selecting a language beforehand, and MUST detect a document in neither language and flag it as
  unsupported rather than presenting an extraction as though it had been understood.
- **FR-007**: System MUST unify Arabic name spelling variants so that the same person is findable
  regardless of transliteration.
- **FR-008**: System MUST extract a structured profile covering name, contact details, location,
  years of experience, dated employment history, education, skills, languages and certifications.
- **FR-009**: System MUST normalise Hijri and Gregorian dates and interpret Arabic-Indic numerals.
- **FR-010**: Users MUST be able to correct any extracted field, and corrections MUST be retained.
- **FR-011**: System MUST flag CVs it could not parse with confidence and route them to a manual
  review queue rather than discarding them.
- **FR-012**: System MUST retain every original file and display it alongside the extracted data.
- **FR-013**: System MUST score each candidate against a chosen job on a scale from 0 to 100.
- **FR-014**: System MUST break each score into weighted components covering skills match,
  experience relevance, education, tenure stability, language and location.
- **FR-015**: System MUST accompany every score with a written justification in the user's interface
  language that cites specific evidence from that CV.
- **FR-016**: System MUST produce a candidate summary of three to five lines in Arabic or English.
- **FR-017**: System MUST exclude name, gender, age, photograph, nationality and marital status from
  scoring inputs, and this exclusion MUST be demonstrable by an automated test.
- **FR-018**: Users MUST be able to view candidates in a list supporting sorting, filtering and
  full-text search across extracted fields in both languages.
- **FR-019**: System MUST isolate each organisation's data such that no user can reach another
  organisation's records, enforced at the data layer.
- **FR-020**: System MUST consume model responses through declared output schemas, never by
  interpreting free text.
- **FR-021**: System MUST record the model identity, prompt version and input fingerprint for every
  score so that any result can be reproduced later.
- **FR-022**: System MUST avoid repeat processing cost when the same file content is submitted
  again.
- **FR-023**: System MUST present scores as advisory, and MUST require a deliberate human action to
  reject a candidate.
- **FR-024**: System MUST verify, by automated test, that CVs differing only in name, gender or
  nationality score within a defined tolerance.
- **FR-025**: System MUST NOT permit customer data to be used for training third-party models.
- **FR-026**: System MUST enforce per-organisation processing limits and a spending ceiling.
- **FR-027**: System MUST present a complete interface in both Arabic and English, with correct
  right-to-left layout, and allow the user to switch between them.
- **FR-028**: System MUST purge candidate personal data automatically once the configured retention
  period elapses.
- **FR-029**: System MUST remove candidate personal data within 30 days of a deletion request.
- **FR-030**: System MUST write an immutable record of every access to and export of candidate data.

### Key Entities

- **Organisation**: The tenant boundary. Owns every other record. In Phase 1 it holds a single user.
- **User**: A person signed in to an organisation.
- **Job**: A role being filled, carrying the specification candidates are measured against.
- **Candidate**: A person who applied. Holds the extracted profile and links to their files.
- **CV file**: An original uploaded document, retained unchanged and always viewable.
- **Parsed profile**: The structured extraction derived from a CV file, versioned so that
  reprocessing does not destroy earlier results or user corrections.
- **Application**: The link between a candidate and a specific job.
- **Score**: An evaluation of one application, carrying components, justification, and the model and
  prompt identity that produced it.
- **Activity**: An immutable audit event recording who did what and when.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A recruiter goes from a folder of CVs to a ranked shortlist without typing any
  candidate data by hand.
- **SC-002**: Key fields are extracted correctly from at least 95 percent of native PDF CVs.
- **SC-003**: Key fields are extracted correctly from at least 85 percent of scanned and
  photographed CVs.
- **SC-004**: A recruiter agrees with the system's top ten ranking in at least 80 percent of cases.
- **SC-005**: Every score carries a written justification citing evidence, with no exceptions.
- **SC-006**: No submitted file is ever lost. Every one either produces a profile or appears in the
  review queue.
- **SC-007**: A single CV is parsed and scored within 30 seconds for 95 percent of submissions.
- **SC-008**: A batch of 100 CVs finishes within 10 minutes.
- **SC-009**: The candidate list opens within 2 seconds for accounts holding up to 50,000
  candidates.
- **SC-010**: Processing cost stays at or below 2.5 EGP per CV during Phase 1.
- **SC-011**: CVs identical except for name, gender or nationality score within the defined
  tolerance.
- **SC-012**: Every recruiter-facing screen is fully usable in both Arabic and English, and meets
  WCAG 2.1 Level AA.
- **SC-013**: Time from receiving a CV to a shortlist decision falls below 24 hours.
- **SC-014**: A pilot company processes 200 CVs and confirms the resulting ranking is defensible.
- **SC-015**: Every CV in a language other than Arabic or English is flagged as unsupported rather
  than parsed and presented as correct, and the recruiter can distinguish that from a poor scan.

## Assumptions

- **Phase 1 membership follows the requirements table, not the range shorthand.** BRD section 14
  lists Phase 1 as including FR-020 through FR-029, but the requirements table marks FR-025,
  FR-026 and FR-028 as Phase 2. The per-requirement column is the more specific statement, so those
  three are excluded here. Phase 1 therefore contains 19 BRD requirements rather than the 22 the
  range implies. **This discrepancy should be corrected in the BRD.**
- Weight adjustment and rescoring against a different job are out of scope, being Phase 2.
- Flagging gaps, contradictions and unverifiable claims is out of scope, being Phase 2.
- Deduplication across channels is out of scope, being Phase 2. The same person applying twice
  produces two records in Phase 1.
- Ingestion is by direct upload only. Forwarding address and WhatsApp intake are Phase 2.
- Billing, quotas and self-serve signup are out of scope, being Phase 3. The processing limit and
  spending ceiling in FR-026 are cost controls, not commercial metering.
- Each organisation has one user in Phase 1. Roles, invitations and permissions are Phase 2.
- Development and parser testing run on anonymised real Egyptian CVs supplied by the founder,
  covering Arabic and English.
- **Intake is Arabic and English only for version 1.0 (ADR 0005).** Other languages are out of
  scope. A CV in neither language is flagged as unsupported rather than parsed, which makes language
  detection a requirement rather than an optimisation. Widening the supported set is recorded as
  open in OQ-09, and each addition needs a labelled corpus before it can carry an accuracy gate.
- Language detection must tolerate a supported CV that contains a minority of third-language text,
  such as a French course title on an English CV, without flagging the whole document.
- The review queue now holds two distinguishable kinds of item: documents that parsed with low
  confidence, and documents in an unsupported language. They call for different user actions.
- Scoring justifications follow the reader's interface language, not the CV's.
- Real candidate data enters only through pilot validation, where the pilot company acts as data
  controller. This arrangement requires written legal confirmation before any pilot data is loaded,
  and the retention, deletion and audit requirements above exist in Phase 1 because of it.
- Retention defaults to 24 months, configurable.
- Recruiters work on modern desktop browsers, with the interface remaining usable down to 360
  pixels of width.

## Traceability to the BRD

Every Phase 1 requirement in the BRD is covered. The BRD column uses BRD identifiers; the
specification column uses the local numbering above.

| BRD | Requirement | Spec | Story |
|---|---|---|---|
| FR-001 | Drag and drop multiple CV files | FR-003 | US1 |
| FR-010 | Text extraction preserving reading order | FR-004 | US1 |
| FR-011 | OCR for scans and photographs | FR-005 | US2 |
| FR-012 | Arabic, English and mixed parsing; others flagged | FR-006 | US1 |
| FR-013 | Arabic name variant normalisation | FR-007 | US1 |
| FR-014 | Structured profile extraction | FR-008 | US1 |
| FR-015 | Hijri dates and Arabic-Indic numerals | FR-009 | US1 |
| FR-016 | Editable fields, corrections retained | FR-010 | US2 |
| FR-017 | Low-confidence review queue | FR-011 | US2 |
| FR-018 | Original file retained and viewable | FR-012 | US1 |
| FR-020 | Job creation | FR-001 | US1 |
| FR-021 | Job specification from free text | FR-002 | US1 |
| FR-022 | Score 0 to 100 | FR-013 | US1 |
| FR-023 | Weighted component breakdown | FR-014 | US1 |
| FR-024 | Written justification citing evidence | FR-015 | US1 |
| FR-027 | Candidate summary | FR-016 | US1 |
| FR-029 | Protected attributes excluded | FR-017 | US3 |
| FR-050 | Candidate list, sort, filter, search | FR-018 | US1 |
| FR-070 | Tenant isolation | FR-019 | US4 |

Cross-cutting requirements that bind Phase 1 because scoring ships in it:

| BRD | Requirement | Spec | Story |
|---|---|---|---|
| AI-01 | Structured output schemas | FR-020 | US3 |
| AI-02 | Score reproducibility | FR-021 | US3 |
| AI-03 | Cache by file content | FR-022 | US1 |
| AI-06 | Rate limits and spend ceiling | FR-026 | US3 |
| AI-07 | Advisory scores, human rejection | FR-023 | US3 |
| AI-08 | Bias testing | FR-024 | US3 |
| AI-09 | No third-party training | FR-025 | US3 |
| NFR-06 | Bilingual interface with RTL | FR-027 | US1 |
| NFR-07 | Tenant isolation at data layer | FR-019 | US4 |

Pulled forward from Phase 2 by the pilot data decision:

| BRD | Requirement | Spec | Story |
|---|---|---|---|
| NFR-10 | Retention with automatic purge | FR-028 | US4 |
| FR-076 | Deletion within 30 days | FR-029 | US4 |
| FR-074 | Audit log of access and export | FR-030 | US4 |
