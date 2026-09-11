<!--
SYNC IMPACT REPORT
==================
Version change: (unpopulated template) -> 1.0.0
Rationale: First ratification. The file previously contained only placeholder
tokens, so this is an initial adoption rather than an amendment.

Modified principles (placeholder -> populated):
  [PRINCIPLE_1_NAME] -> I. Test-First Development (NON-NEGOTIABLE)
  [PRINCIPLE_2_NAME] -> II. Clean Architecture with Enforced Boundaries
  [PRINCIPLE_3_NAME] -> III. Code Quality Gates
  [PRINCIPLE_4_NAME] -> IV. Bilingual User Experience Consistency
  [PRINCIPLE_5_NAME] -> V. Performance and Cost Budgets
  (added, beyond template's five) -> VI. Fairness and Auditability of Automated Decisions

Added sections:
  Technology and Security Constraints (was [SECTION_2_NAME])
  Development Workflow and Quality Gates (was [SECTION_3_NAME])
  Governance (populated from [GOVERNANCE_RULES])

Removed sections: none

Deferred items / TODOs: none. All placeholder tokens resolved.

Review notes for the project owner:
  1. Principle VI was NOT part of the amendment request. It was added because
     FR-029, AI-02, AI-07, AI-08 and AI-09 are Must-have requirements in the BRD
     and risk R-10 records legal exposure if they are unenforced. Governance
     silence on the highest-liability area of the product seemed wrong. Delete
     it if you disagree.
  2. Frontend framework and CV-pipeline language are deliberately NOT fixed
     here. They remain open as Q3 and Q4 in Docs/phase1-open-decisions.md.
     Principle II is written so that any of the candidate answers satisfies it.

This report is scratch material for reviewing the amendment. Delete it before
committing the file.
-->

# Masirah Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

Tests MUST be written before the implementation they describe, and MUST be observed failing for
the intended reason before any code is written to satisfy them. The red-green-refactor cycle is
mandatory, not aspirational.

Every parsing, extraction and scoring behaviour MUST be covered by an automated test backed by a
fixture committed to the repository. The Arabic and mixed-language parsing accuracy gate (FR-012,
with the targets in BRD section 15) MUST exist as an executable suite rather than a manual
inspection, and Phase 1 does not exit until it runs green. Every bug fix MUST begin with a failing
test that reproduces the defect.

Rationale: the product's entire value is extraction and ranking quality on documents that are
hostile to parsing. A quality claim that is not measured is a guess, and R-03 rates Arabic parsing
quality as the highest combined likelihood and impact risk in the project.

### II. Clean Architecture with Enforced Boundaries

Domain logic (scoring, weighting, deduplication, profile normalisation) MUST NOT import framework,
database, HTTP or model-provider code. Dependencies point inward.

Every external dependency MUST sit behind an interface the domain layer owns: model provider, OCR
engine, file storage, email delivery, payment collection. Each module MUST have one reason to
change. New capability SHOULD arrive as a new implementation of an existing interface rather than
as a modification of a working one. Implementations MUST be substitutable without the caller
knowing which one it holds, and interfaces MUST stay narrow enough that no implementer is forced
to stub methods it does not use.

Rationale: two migrations are already planned. Hosting moves off Netlify before Phase 3 (ADR
0002), and the model provider is explicitly to be abstracted (BRD section 11). Boundaries drawn
now are the difference between those being configuration changes and being rewrites.

### III. Code Quality Gates

All code MUST be statically typed with the strictest practical compiler settings enabled. Linting
and formatting MUST run automatically and MUST pass before anything merges to the main branch.

Model responses MUST be parsed through declared output schemas. Heuristic or regular-expression
parsing of free-text model output is forbidden (AI-01). Secrets MUST NOT appear in source control,
client bundles or logs. Functions SHOULD be small enough to understand without scrolling, and a
function needing a comment to explain what it does SHOULD be renamed or split instead. Dead code,
commented-out code and unused dependencies MUST be deleted rather than kept for later.

Rationale: a solo part-time builder has no second reviewer to catch drift. Automated gates are the
only reviewer guaranteed to be present on every change.

### IV. Bilingual User Experience Consistency

Every recruiter-facing screen MUST render correctly in both right-to-left and left-to-right
layouts. Direction-sensitive styling MUST use logical properties; physical left and right values
are forbidden in layout code.

All user-visible text MUST live in translation files, never hard-coded at the point of display.
Arabic MUST be treated as a first-class language rather than a layer added afterwards, covering
mixed-direction text, forms, tables and PDF export (NFR-06). Screens MUST meet WCAG 2.1 Level AA
(NFR-11) and MUST remain usable from 360 pixels of width (NFR-12). A given action MUST behave
identically wherever it appears: same wording, same placement, same confirmation pattern.

Rationale: the primary user is an Egyptian HR generalist working in Arabic. Direction is cheap to
build in once and expensive to retrofit into a finished layout.

### V. Performance and Cost Budgets

The following are budgets, and a change that breaches one is a defect rather than a tradeoff:

- A single CV MUST parse and score within 30 seconds at the 95th percentile (NFR-01).
- A batch of 100 CVs MUST complete within 10 minutes (NFR-02).
- The candidate list MUST load within 2 seconds for accounts holding up to 50,000 candidates
  (NFR-03).
- Model inference cost per CV MUST stay at or below 2.5 EGP through Phase 1 and 1.5 EGP at
  expected volume (NFR-13).

Parse results MUST be cached by file content hash and scores by candidate, job and weighting tuple
(AI-03, AI-04), so that reprocessing identical input incurs no new inference cost. Extraction and
summarisation MUST use the cheaper model tier, reserving the stronger tier for scoring and
justification (AI-05). Per-organisation rate limits and a hard monthly spend ceiling MUST be in
place before any external user is admitted (AI-06). Budgets MUST be asserted by automated tests or
monitoring rather than assumed.

Rationale: the commercial thesis is a price point beneath every competitor. Unit cost is therefore
a product constraint, not an optimisation to revisit after launch.

### VI. Fairness and Auditability of Automated Decisions

Name, gender, age, photograph, nationality and marital status MUST be excluded from scoring
inputs, and the exclusion MUST be proven by an automated test rather than asserted (FR-029).

Every score record MUST store the model identifier, prompt version and input hash so that any
result can be reproduced and audited later (AI-02). The interface MUST NOT present a score as an
automated hiring decision, and rejecting a candidate MUST require a deliberate human action
(AI-07). A bias suite MUST verify that CVs differing only in name, gender or nationality score
within a defined tolerance, and MUST run as part of the pipeline (AI-08). Customer data MUST NOT
be used to train third-party models (AI-09).

Rationale: R-10 records the risk of a customer treating a score as an automated decision and
facing a discrimination claim. These controls are the recorded mitigation, and a mitigation that
is not enforced in code is not a mitigation.

## Technology and Security Constraints

Settled, and recorded in `Docs/adr/`:

- Supabase provides database, authentication and storage. PostgreSQL row level security MUST
  enforce tenant isolation at the database layer, not in application code alone (NFR-07).
- Netlify hosts the site through Phases 1 and 2, with a migration to a separate server planned
  before Phase 3 (ADR 0002). No code may depend on Netlify-specific behaviour in a way that would
  obstruct that move.
- Data MUST be encrypted in transit using TLS 1.2 or higher, and at rest (NFR-07). Passwords MUST
  be hashed with a modern key derivation function (NFR-08).
- Development and parser testing MUST run on anonymised data only. Real candidate data enters the
  system solely through Phase 1 pilot validation, where the pilot company acts as data controller
  (ADR 0003), and MUST NOT be loaded before that arrangement is confirmed in writing by counsel.
  Because real data is therefore present from Phase 1, retention limits (NFR-10), deletion on
  request (FR-076) and the access audit trail (FR-074) are Phase 1 obligations rather than
  Phase 2 features.
- Structured logging, error tracking and per-tenant usage metrics MUST exist, with alerting when
  the parse failure rate exceeds five percent (NFR-14).
- Backups MUST run daily with a tested recovery point objective of 24 hours or better (NFR-15).

Deliberately left open: the frontend framework and the CV pipeline language are not fixed by this
constitution. They are Q3 and Q4 in `Docs/phase1-open-decisions.md`. Any of the candidate answers
is acceptable provided it satisfies Principle II.

## Development Workflow and Quality Gates

- Every piece of work MUST trace to a numbered BRD requirement or a recorded decision. Work with
  no such anchor MUST be challenged before it is started, not after it is built.
- The main branch MUST always build and pass its tests. Feature work happens on branches.
- A change is complete when all of the following hold: its tests were written first and pass, types
  and linting are clean, the budgets in Principle V still hold, and any user-visible text is in a
  translation file.
- Decisions that are hard to reverse MUST be recorded as an ADR in `Docs/adr/` before
  implementation begins, continuing the existing sequential numbering.
- The phase exit criteria in BRD section 14 are gates, not targets. A phase does not end because
  its time box expired.
- Scope added mid-phase MUST be justified against the Phase 1 scope discipline demanded by R-09,
  or deferred to a later phase.

## Governance

This constitution supersedes ad hoc practice. Where it conflicts with habit or convenience, it
wins.

It governs how the product is built; the BRD governs what is built. Where the two conflict, the
conflict MUST be surfaced and one of the two amended. Silently ignoring either is forbidden.

Amendments MUST be recorded in this file with a version increment and the amendment date.
Versioning follows semantic rules: MAJOR for removing or redefining a principle in a
backward-incompatible way, MINOR for adding a principle or materially expanding guidance, PATCH
for clarifications and wording that do not change meaning.

Compliance MUST be checked against these principles before any merge. Complexity that violates a
principle MUST be justified in writing in the commit or pull request, or removed. A principle that
is routinely violated MUST be either enforced or formally amended, because leaving a dead rule in
place devalues every rule beside it.

**Version**: 1.1.0 | **Ratified**: 2026-09-11 | **Last Amended**: 2026-09-11
