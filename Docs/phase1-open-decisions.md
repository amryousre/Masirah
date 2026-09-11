# Phase 1 decisions

Twelve technical and process decisions, asked and answered 11 September 2026. **Status: all
answered.** Superseded questions are kept with their answers so the reasoning survives.

Business decisions live in BRD section 17. Architectural decisions that are hard to reverse are
recorded as ADRs in `adr/`.

## Context these decisions sit on

- Product is **Masirah**, domain `masirah.online` owned.
- Positioning is the self-serve SME wedge with screening depth as the feature bet (ADR 0001).
- Solo build, part-time.
- **Supabase** for database and auth (project `skgetonknlshzrvykrpf`, PostgreSQL 17, Frankfurt),
  **Netlify** for the site, migrating to a separate server before Phase 3 (ADR 0002).
- Free tier is 30 CVs per month.
- Jira project **MAS** at `https://amryousre.atlassian.net/browse/MAS`.
- Phase 1 covers FR-001, FR-010 to FR-018, FR-020 to FR-029, FR-050 and FR-070: twenty-two
  requirements covering upload, parsing, OCR, extraction, job creation, scoring, justification,
  candidate list and tenant isolation.

---

## Answers

| # | Decision | Answer |
|---|---|---|
| Q1 | Jira backlog depth | All four phases populated now |
| Q2 | Spec Kit or Jira | Both: Jira tracks status, Spec Kit writes the technical plan |
| Q3 | Frontend framework | Next.js |
| Q4 | CV pipeline language | Python pipeline, TypeScript app |
| Q5 | Model provider | Both Anthropic and OpenAI from day one |
| Q6 | Multi-tenancy in Phase 1 | Schema only: tenant column and RLS, no org screens |
| Q7 | Phase 1 interface language | Both Arabic and English with a working switcher |
| Q8 | Parser test corpus | Real Egyptian CVs, anonymised before entering the system |
| Q9 | Phase 1 exit criterion | Pilot company acts as data controller for their own real CVs |
| Q10 | Where heavy processing runs | Python worker consuming a queue; Next.js enqueues |
| Q11 | OCR approach | Vision model primary, Tesseract fallback |
| Q12 | Repository structure | One repository, a web folder and a pipeline folder |
| Q13 | Worker and queue hosting | Managed background-worker host, queue in Supabase Postgres |
| Q14 | Does "accept any CV" change parsing or market? | Market expansion deferred as OQ-09 |
| Q15 | Which languages does v1.0 support? | Arabic and English only; others flagged as unsupported |

---

## Notes on the answers that went against the recommendation

Recording these so the tradeoff is visible later, not to relitigate them.

**Q1, all four phases.** Recommendation was Phase 1 only. Roughly ninety tickets now exist or will,
most describing work months away. Expect to rewrite the Phase 3 and Phase 4 tickets when you reach
them, and treat their current contents as a sketch rather than a specification.

**Q2, both tools.** Recommendation was Jira alone. Every piece of work now gets written twice, once
as a Jira ticket and once as a Spec Kit spec or plan. The risk is the two drifting apart. Decide
which one wins when they disagree, and prefer keeping the Spec Kit artifact thin where the BRD
already says the same thing.

**Q5, both providers.** Recommendation was Anthropic alone behind an interface. Building for both
immediately doubles prompt maintenance before there is a user, but it does give real cost and
quality comparison on Arabic CVs early, which is defensible given Arabic output quality is the
core risk. Principle II of the constitution already requires the provider interface, so the second
implementation is additive rather than structural.

**Q7, both languages with a switcher.** Recommendation was Arabic only with right-to-left-safe
layout. Shipping both in Phase 1 doubles the copywriting and testing surface in the tightest
phase. The upside is that NFR-06 is satisfied from the start rather than revisited.

**Q9, pilot company as data controller.** Recommendation was to exit Phase 1 on anonymised CVs.
This answer is faster to real signal but rests on a legal position neither of us is qualified to
confirm. See ADR 0003, which records it together with the confirmation it depends on.

---

## What these answers changed elsewhere

Q9 contradicted three documents written earlier the same day, all of which stated that Phase 1
runs on test or anonymised data only. All three were corrected:

- BRD section 17, the OQ-04 resolution, in both languages.
- `adr/0002-managed-hosting-phases-1-2.md`, the paragraph on Frankfurt hosting.
- `.specify/memory/constitution.md`, the Phase 1 data constraint.

New decision records created from these answers:

- `adr/0003-pilot-company-as-data-controller.md`
- `adr/0004-application-architecture.md`
