# Implementation Plan: Phase 1 Core Screening

**Branch**: `001-phase1-core-screening` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-phase1-core-screening/spec.md`

## Summary

Phase 1 delivers the core screening loop: a recruiter creates a job, uploads a batch of CVs, and
receives a ranked shortlist where every candidate carries a component-level score and a written
justification citing evidence from their own CV. It must work on Arabic, English and mixed-language
documents, including photographs of printed CVs, flag anything in another language as unsupported
rather than mis-parsing it (ADR 0005), and be demonstrably free of scoring bias on protected
attributes.

The technical approach was settled before planning and is recorded in
[ADR 0004](../../Docs/adr/0004-application-architecture.md). A Next.js application handles the
interface, authentication and uploads, then places a job on a queue. A long-lived Python worker
consumes that queue and does the expensive work: text extraction, OCR, structured extraction and
scoring. The split exists because the batch target of 100 CVs in 10 minutes cannot be met inside
request handlers, and because the parsing libraries that matter for multi-column layouts, Arabic
name variants and Hijri dates are markedly stronger in Python.

## Technical Context

**Language/Version**: TypeScript 5.x on Node 24 LTS for the web application. Python 3.12 for the
processing pipeline.

**Primary Dependencies**: Next.js App Router for the interface and server routes. Supabase client
libraries in both languages for data, auth, storage and queue access. PyMuPDF for layout-aware text
extraction. Anthropic and OpenAI SDKs behind a single provider port. Tesseract as OCR fallback
behind an OCR port.

**Storage**: Supabase PostgreSQL 17 in `eu-central-1` (project `skgetonknlshzrvykrpf`) for
relational data, Supabase Storage for original CV files, and Supabase Queues, which are built on
the `pgmq` extension and exposed through the `pgmq_public` schema, for job handoff. No separate
queue service is introduced.

**Testing**: Vitest for web unit tests, Playwright for end-to-end flows including right-to-left
layout. pytest for the pipeline, including a dedicated accuracy suite that is a release gate rather
than an ordinary test.

**Target Platform**: Netlify for the web application. A managed background-worker host for the
Python worker, with Render the marginal preference. Both browsers and the worker run against the
same Supabase project.

**Project Type**: Web application with an asynchronous processing worker.

**Performance Goals**: A single CV parsed and scored within 30 seconds at p95. A batch of 100
finishing within 10 minutes. Candidate list opening within 2 seconds for accounts holding up to
50,000 candidates.

**Constraints**: Processing cost at or below 2.5 EGP per CV during Phase 1. Complete Arabic and
English interface with correct right-to-left layout and a switcher. WCAG 2.1 Level AA. Usable from
360 pixels of width. Tenant isolation enforced by row level security rather than application code.
Protected attributes excluded from scoring inputs and proven so by test.

**Scale/Scope**: Phase 1 serves one pilot organisation processing 200 CVs for validation. The
architecture must not preclude the stated ceiling of 1,000 organisations and 5 million stored CVs,
but nothing is built for that scale now.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates derive from [the project constitution](../../.specify/memory/constitution.md), version 1.1.0.

| Principle | Gate | Pre-design | Post-design |
|---|---|---|---|
| I. Test-First | Every behaviour has a failing test written before implementation. The Arabic accuracy suite exists as executable tests, not a manual check. | PASS | PASS |
| II. Clean Architecture | Domain logic imports no framework, database or provider code. Model provider, OCR engine, storage and queue each sit behind a port the domain owns. | PASS | PASS |
| III. Code Quality | Strict TypeScript and typed Python, lint and format enforced before merge, model responses consumed through declared schemas, no secrets reaching the browser. | PASS | PASS |
| IV. Bilingual UX | Logical CSS properties only, all text in translation files, WCAG 2.1 AA, usable at 360px. | PASS | PASS |
| V. Performance and Cost | The four numeric budgets asserted by tests or monitoring. Parse cached by file hash, scores cached by candidate-job-weights. Cheaper model for extraction, stronger for scoring. Spend ceiling enforced. | PASS | PASS |
| VI. Fairness and Auditability | Protected attributes excluded with a test proving it. Model identity, prompt version and input hash stored per score. Scores advisory, rejection requires human action. Bias suite runs in the pipeline. | PASS | PASS |

Two design choices deserve explicit note rather than silent acceptance. Both are recorded in
Complexity Tracking below.

## Project Structure

### Documentation (this feature)

```text
specs/001-phase1-core-screening/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── queue-message.md
│   ├── model-provider-port.md
│   └── web-routes.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Created later by /speckit.tasks
```

### Source Code (repository root)

```text
web/                                 # Next.js application
├── app/
│   └── [lang]/                      # locale root parameter: ar, en
│       ├── layout.tsx               # sets dir from locale
│       ├── jobs/
│       └── candidates/
├── components/
├── lib/
│   ├── domain/                      # ranking, presentation rules; no framework imports
│   ├── ports/                       # interfaces the domain owns
│   └── adapters/                    # supabase, storage, queue implementations
├── messages/                        # ar.json, en.json
├── proxy.ts                         # locale detection and redirect
└── tests/
    ├── unit/
    └── e2e/                         # includes RTL layout assertions

pipeline/                            # Python worker
├── src/masirah_pipeline/
│   ├── domain/                      # extraction rules, normalisation, score composition
│   │   ├── arabic.py                # name variants, Arabic-Indic numerals
│   │   ├── dates.py                 # Hijri and Gregorian normalisation
│   │   ├── profile.py               # structured profile model
│   │   └── scoring.py               # component weights, redaction of protected fields
│   ├── ports/                       # ModelProvider, OcrEngine, Storage, Queue protocols
│   ├── adapters/
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   ├── vision_ocr.py
│   │   ├── tesseract_ocr.py
│   │   └── supabase_queue.py
│   └── worker.py                    # consume loop
└── tests/
    ├── unit/
    ├── fixtures/cvs/                # anonymised corpus, committed
    └── accuracy/                    # release gate: FR-012 field accuracy, bias suite

supabase/
└── migrations/                      # tenant column and RLS from the first migration
```

**Structure Decision**: One repository containing `web/`, `pipeline/` and `supabase/`, with no
monorepo tooling. This follows the repository decision in ADR 0004 and is the simplest arrangement
that works for a single part-time developer. The two runtimes share no code; they share the
database schema and the queue message contract, both of which are documented in `contracts/`.

Note that both `web/lib/` and `pipeline/src/masirah_pipeline/` carry the same three-layer shape of
domain, ports and adapters. That repetition is deliberate. It is what lets the domain rules in
either runtime be tested without a database, a network or a model provider.

## Complexity Tracking

> Filled because two choices add complexity that a reviewer would otherwise question.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Two model providers implemented from day one rather than one behind an interface | Decision Q5. Arabic output quality and cost per CV are the two riskiest unknowns in the project, and comparing them needs both providers running against the same real CVs early, before there are users to disrupt | Shipping one provider first would defer the comparison until a switch is expensive and until pilot data already depends on the incumbent's output quality |
| Two languages in one project | ADR 0004. Multi-column reading order, Arabic name normalisation and Hijri dates have materially stronger Python libraries, and parsing quality is the highest rated risk in the BRD | An all-TypeScript pipeline would either accept weaker extraction or push every CV through a vision model, which breaks the cost ceiling in NFR-13 |
