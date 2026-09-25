# Phase 0 Research: Phase 1 Core Screening

**Date**: 2026-09-11

The Technical Context in [plan.md](./plan.md) contains no NEEDS CLARIFICATION markers. Every stack
decision was settled before planning, in a structured decision session recorded in
[phase1-open-decisions.md](../../Docs/phase1-open-decisions.md) and formalised in
[ADR 0004](../../Docs/adr/0004-application-architecture.md). This document records those decisions
with their rationale and rejected alternatives, and adds the two points verified against current
vendor documentation during planning.

## Settled before planning

### Application framework

**Decision**: Next.js with the App Router.

**Rationale**: Phase 2 brings inbound email and WhatsApp webhooks, which need server-side HTTP
endpoints. Model API keys need a server-side home from Phase 1. Supabase documents Next.js as a
first-class target with a dedicated authentication quickstart.

**Alternatives considered**: A static Vite and React single page app, which would migrate off
Netlify more easily since there is no runtime to port, but needs a separate service for secrets and
webhooks. Angular, rejected because Supabase publishes no official Angular quickstart, leaving a
solo part-time builder translating React examples throughout.

### Pipeline language

**Decision**: Python for the processing pipeline, TypeScript for the application.

**Rationale**: Multi-column reading order, Arabic name variant normalisation and Hijri date
conversion have materially stronger library support in Python. Arabic parsing quality is the
highest rated risk in the BRD.

**Alternatives considered**: All TypeScript with a vision model performing extraction and OCR in
one pass on every CV, rejected because a vision inference per document breaks the cost ceiling and
the latency target. All TypeScript with JavaScript PDF libraries, rejected for weak reading-order
handling and near-absent Arabic tooling.

### Where heavy processing runs

**Decision**: A long-lived Python worker consuming a job queue. The web application enqueues and
returns immediately.

**Rationale**: The batch target is 100 CVs within 10 minutes. No serverless request handler stays
alive long enough, so the work must be detached from the request.

**Alternatives considered**: Synchronous calls from route handlers, rejected on timeouts. Supabase
Edge Functions orchestrating the work, rejected because it adds a third runtime and carries its own
execution limits.

### Model provider

**Decision**: Both Anthropic and OpenAI implemented from the start, behind one provider port.
Cheaper tier for extraction and summarising, stronger tier for scoring and justification.

**Rationale**: Arabic output quality and cost per CV are the two riskiest unknowns. Comparing them
needs both providers running against the same real CVs, early.

**Alternatives considered**: One provider behind an interface, with the second added later. This was
the recommendation, and was rejected deliberately in favour of early comparison. The added cost is
double prompt maintenance, recorded in the plan's Complexity Tracking.

### OCR strategy

**Decision**: A vision model as the primary path, Tesseract as fallback.

**Rationale**: Tesseract is weak on Arabic and weaker still on photographs of printed pages, which
is precisely the 85 percent accuracy target for scanned and photographed CVs.

**Alternatives considered**: Tesseract first with escalation to a vision model on low confidence,
which would be cheaper but risks most Arabic documents escalating anyway, incurring both costs. A
dedicated cloud OCR service, rejected to avoid another vendor.

### Repository structure and hosting

**Decision**: One repository containing `web/`, `pipeline/` and `supabase/`, no monorepo tooling.
The web application on Netlify, the worker on a managed background-worker host.

**Rationale**: Simplest arrangement for one developer. The worker cannot run on Netlify, so a second
hosting target is needed from Phase 1 rather than Phase 3 as the hosting decision originally
assumed.

**Alternatives considered**: Two repositories, rejected because every change spanning both would
mean two branches and hand-synchronised contracts. A self-managed virtual machine, which is cheaper
and removes a later migration, but adds operational burden to a part-time builder.

### Tenancy and interface languages

**Decision**: Tenant column and row level security policies in the first migration, with no
organisation management screens. Both Arabic and English shipping in Phase 1 with a working
switcher.

**Rationale**: Retrofitting tenancy into a schema holding live data is among the worst migrations
available. Layout direction is similarly expensive to retrofit, and shipping Arabic early forces
evaluation of Arabic justification quality while there is still time to react.

### Test corpus

**Decision**: Real Egyptian CVs, anonymised before entering the system, committed as fixtures.

**Rationale**: Synthetic CVs do not reproduce what actually breaks parsers: skewed photographs,
mixed-direction text, and multi-column templates. Anonymising preserves those properties while
keeping development clear of personal data.

**Amended 11 September 2026**: broadening intake to any language was considered and rejected the
same day. Version 1.0 supports Arabic and English only, and a CV in neither is flagged as
unsupported rather than parsed (ADR 0005). The corpus is unchanged. The consequence worth carrying
forward is that language detection became a requirement, since flagging depends on it, which is
work the broader option would not have needed.

**Amended 25 September 2026**: synthetic CVs admitted alongside the real ones, at the project
owner's request, to cover Arabic, mixed, French and captured documents before real examples
arrive. The rationale above still holds, so they are marked in their labels (`origin`,
`simulated`). The gate is measured on real documents alone, and Phase 1 does not exit on
synthetic results. Building them surfaced one fact the real corpus had not: a browser-printed
Arabic PDF stores its text in visual order, reversing Arabic-Indic numbers.

## Verified against current documentation during planning

### Queue mechanism

**Decision**: Supabase Queues, built on the `pgmq` Postgres extension, rather than a separate Redis
or hosted queue service.

**Finding**: Supabase exposes queue operations through a `pgmq_public` schema callable as RPC, with
`send`, `send_batch`, `read`, `pop` and `delete`. The documentation includes a Python client example
calling `supabase.schema("pgmq_public").rpc(...)`, which is exactly the access path the worker
needs. Messages left undeleted after a failure return to the queue for retry.

**Rationale**: No second datastore to operate, and jobs stay in the same database as the data they
act on. A plain jobs table using `select ... for update skip locked` remains a viable fallback and
is also documented by Supabase.

**Alternatives considered**: Managed Redis alongside Postgres, rejected as an unnecessary second
datastore for one developer at this scale.

### Locale routing and direction

**Decision**: A `[lang]` root parameter segment in the App Router, with locale detection in
`proxy.ts`, and the document direction set from the locale in the root layout.

**Finding**: The current App Router internationalisation pattern uses a root parameter shared by all
routes beneath it, with the locale available through `params` in pages and layouts, and redirection
handled by a proxy rather than the older Pages Router `i18n` configuration block.

**Rationale**: Direction can then be set once, at the layout that owns the locale, rather than
being threaded through components.

## Still genuinely unknown

One thing is not resolvable by research and is not a design gap.

**Whether the accuracy targets are reachable at all.** Section 15 of the BRD requires 95 percent
field accuracy on native PDFs and 85 percent on photographed and scanned CVs, and no one has yet
run a real Egyptian CV through any extraction pipeline. PyMuPDF is the starting choice for
layout-aware extraction because of its reading-order handling, but it is a starting choice rather
than a validated one.

This resolves by building the accuracy suite against the anonymised corpus early, as the first
substantial task, rather than by further reading. If the numbers fall short, the extraction
approach changes while almost nothing is built on top of it. That ordering is a deliberate
consequence of the release gate in requirement FR-012.
