# Business Requirements Document

## Masirah (مسيرة) — AI-Powered CV Screening & Hiring Platform for Egypt and MENA

| Field | Value |
|---|---|
| Document title | Business Requirements Document — Masirah |
| Version | 1.4 (Arabic and English scope confirmed) |
| Date | 11 September 2026 |
| Author | Amr Yousre Shalapy |
| Status | Direction confirmed — ready for Phase 1 build |
| Classification | Internal / Confidential |

### Revision history

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | 2026-09-09 | Amr Yousre Shalapy | Initial draft for feature review |
| 1.1 | 2026-09-11 | Amr Yousre Shalapy | Product renamed from Siirah to Masirah; OQ-01 to OQ-06 and OQ-08 resolved; OQ-07 deliberately deferred to Phase 3; hosting stack recorded |
| 1.2 | 2026-09-11 | Amr Yousre Shalapy | OQ-04 sequencing revised: Phase 1 validation runs on pilot-company data with the pilot as data controller (ADR 0003); written legal confirmation now required before Phase 1 validation rather than before Phase 2 |
| 1.3 | 2026-09-11 | Amr Yousre Shalapy | Intake broadened to CVs in any language with a tiered accuracy guarantee, Arabic and English measured and the rest best-effort; market expansion beyond Egypt recorded as OQ-09 and deferred |
| 1.4 | 2026-09-11 | Amr Yousre Shalapy | Intake narrowed back to Arabic and English only for v1.0, superseding 1.3 the same day. Unsupported languages are flagged rather than parsed, which makes language detection a requirement (ADR 0005). OQ-09 widened to cover both language and market expansion |


### Contents

1. Executive summary
2. Problem statement
3. Business objectives
4. Market analysis
5. Strategic positioning — decided
6. Target users and personas
7. Scope
8. Functional requirements
9. Non-functional requirements
10. Data model — core entities
11. Integrations
12. AI requirements and cost control
13. Proposed commercial model
14. Release plan
15. Success metrics
16. Risks
17. Open questions and decisions required
18. Assumptions
19. Glossary

---

## 1. Executive summary

Masirah is a bilingual (Arabic/English), AI-powered CV screening and applicant tracking platform built for the Egyptian and wider MENA market. It ingests CVs from every channel Egyptian candidates actually use — email, WhatsApp, job boards, direct upload — parses them regardless of language or format (including photographed and scanned CVs), scores them against a specific job using a large language model, and gives the hiring team a single ranked shortlist with an auditable explanation for every score.

The commercial thesis is **not** technical differentiation. Several competitors already offer AI scoring, Arabic interfaces and WhatsApp channels. The thesis is **pricing model and go-to-market**: every serious competitor in Egypt sells an annual contract between 40,000 and 96,000 EGP through a sales call. No credible player serves the company that hires five people a year and will not sign an annual contract. Masirah enters through a genuine free tier and self-serve monthly billing in EGP, and grows upward.

The secondary differentiator is **depth of screening rather than breadth of ATS**. Competitors race to add requisition management, offer letters and manpower planning. Masirah instead owns the part of hiring that is still manual and painful everywhere: turning a job description into a defensible technical screen, and turning a pile of CVs into a decision the hiring manager trusts.

> **Decision taken:** Section 5 presented three viable positioning options. Option A (self-serve SME wedge) is confirmed, with Option B (screening depth) as the feature strategy. Recorded in `Docs/adr/0001-self-serve-sme-positioning.md`.

---

## 2. Problem statement

### 2.1 The operational problem

An Egyptian SME posting a mid-level role receives between 150 and 800 applications. These arrive fragmented across:

- The Wuzzuf or Forasna inbox
- A generic `careers@` or `hr@` mailbox
- WhatsApp messages to whoever posted the role on LinkedIn
- Personal email to the hiring manager
- Referrals forwarded internally

The CVs themselves are inconsistent: Arabic, English, or mixed within one document; native PDF, Word, or a photograph of a printed page taken on a phone; formatted with tables, columns and graphics that defeat naive text extraction.

The result is that a hiring manager or a single HR generalist spends 6–12 hours per role manually opening files, and the decision quality is poor because fatigue sets in after roughly forty CVs. Strong candidates who applied late are systematically disadvantaged.

### 2.2 The commercial problem

The tools that solve this are priced for companies that do not have this problem. An Egyptian company hiring 5–20 people a year is asked to commit 40,000–96,000 EGP annually, up front, after a sales call. That company will keep using a spreadsheet.

### 2.3 Consequences

| Consequence | Impact |
|---|---|
| Slow time-to-shortlist | Strong candidates accept other offers first |
| Inconsistent evaluation | Two recruiters rank the same CV differently; no audit trail |
| Lost applications | CVs arriving on WhatsApp never reach the pipeline |
| Manager burnout | Senior engineers spend billable time reading CVs |
| No data | Companies cannot answer "which channel gives us our best hires?" |

---

## 3. Business objectives

| ID | Objective | Measure of success |
|---|---|---|
| BO-01 | Reduce time from CV received to shortlist decision | ≥ 70% reduction vs. manual baseline |
| BO-02 | Capture applications from every channel, losing none | ≥ 95% of inbound CVs auto-ingested without manual upload |
| BO-03 | Make evaluation consistent and explainable | 100% of scores carry a written justification and evidence citations |
| BO-04 | Reach SMEs priced out of existing ATS products | ≥ 60% of paying accounts are companies with < 200 employees |
| BO-05 | Achieve self-serve conversion without a sales call | ≥ 40% of paid conversions complete with zero human sales contact |
| BO-06 | Operate at a defensible unit cost | AI processing cost per CV ≤ 1.5 EGP at scale |

---

## 4. Market analysis

### 4.1 Market context

Wuzzuf reports approximately 45,000 companies and 7 million+ candidate profiles in Egypt. Job-board spend for a single Egyptian SME runs 800–6,000 EGP per month on Wuzzuf, 500–4,000 EGP on Forasna, and 1,500–8,000 EGP on LinkedIn. This establishes the buyer's mental price anchor: **hiring software is a monthly, low-thousands-of-EGP expense.** Annual contracts in the tens of thousands sit outside that anchor and require a different, slower sale.

### 4.2 Competitive landscape

| Competitor | Status | Price (EGP/year) | Strengths | Weaknesses |
|---|---|---|---|---|
| **Wuzzuf (bundled ATS)** | Live, dominant | 9,600–72,000 (board subscription; ATS bundled) | Owns candidate supply; already paid for; 45k companies | Shallow screening; no AI scoring depth; locked to Wuzzuf applicants only |
| **Recruitera** | Live | 55,000 (5 users) / 96,000 (25 users) | Arabic-first UI, dedicated WhatsApp number per company, Egyptian job board integrations, EGP pricing | Annual contract, sales-led, priced above SME anchor |
| **RecDesk** | Waitlist / pre-launch | 40,000 / 70,000 | Clean AI-scoring positioning, undercuts Recruitera | Not shipped; OCR and WhatsApp both deferred to "coming soon" |
| **Talentera** | Live | USD-denominated | Gulf market presence, Bayt integration | Weak Egypt integrations, FX exposure |
| **Workable / Zoho Recruit** | Live, global | USD-denominated | Mature product, strong reporting | English-only UI, no MENA job boards, no Arabic CV handling |
| **Spreadsheet + inbox** | Universal | 0 | Free, familiar, zero onboarding | The actual incumbent, and the real competitor |

### 4.3 Critical competitive findings

> **Finding 1 — The dominant competitor is Wuzzuf, not another ATS.** 45,000 Egyptian companies already pay Wuzzuf and receive a bundled ATS. Masirah must be clearly better at screening than a tool the customer already owns, or it does not get bought.

> **Finding 2 — The "Arabic + WhatsApp" gap is already closing.** Recruitera has shipped Arabic-first UI, a dedicated WhatsApp Business number per company, and local job board integrations. This can no longer be treated as an unoccupied position; it is table stakes.

> **Finding 3 — The genuine gap is the price and purchase model.** Every named competitor sells annually, above 40,000 EGP, through a sales conversation. Nobody serves self-serve monthly SME demand. This is the opening.

> **Finding 4 — The real incumbent is free.** The most common alternative is an inbox and a spreadsheet. Product decisions must be benchmarked against that, not against Workable.

---

## 5. Strategic positioning — decided

| Option | Description | Pros | Cons | Recommendation |
|---|---|---|---|---|
| **A. Self-serve SME wedge** | Free tier + monthly EGP pricing, no sales call, land small and expand | Uncontested segment; fast feedback; low CAC; matches buyer's price anchor | Low ARPU; needs volume; support load | **Recommended** |
| **B. Technical screening depth** | Position as the screening and interview layer, not a full ATS; integrate with Wuzzuf/Workable rather than replace | Plays to founder's domain expertise; avoids head-on ATS fight; higher willingness to pay per seat | Narrower market; depends on integrations that partners control | Strong secondary — fold into A as the core feature bet |
| **C. Head-on ATS competitor** | Build feature parity with Recruitera at a lower annual price | Clear category, understood by buyers | Competing on price against a funded, live incumbent; long build; sales-led GTM the founder is not set up for | **Not recommended** |

**Confirmed direction for the remainder of this document: Option A, with Option B as the feature strategy.** Decided 11 September 2026; see `Docs/adr/0001-self-serve-sme-positioning.md`.

---

## 6. Target users and personas

### 6.1 Primary persona — "Nourhan", HR Generalist at a 60-person company

Handles all hiring alongside payroll and admin. Posts on Wuzzuf, receives 300 CVs per role, has no budget authority above a few thousand EGP per month. Measures success by filling the role without her manager complaining. **Needs:** speed, and something she can start using today without asking permission.

### 6.2 Primary persona — "Tarek", Engineering Manager

Receives a shortlist he does not trust and re-reads all the CVs himself. Wants evidence, not a score. **Needs:** a defensible reason each candidate is ranked where they are, and screening questions he did not have to write.

### 6.3 Secondary persona — "Mahmoud", Independent Recruiter / small agency

Runs 8–15 roles simultaneously across multiple client companies. Highly price-sensitive, highly volume-sensitive. **Needs:** multi-client separation, fast throughput, export to client formats.

### 6.4 Secondary persona — "Sara", Candidate

Applies via WhatsApp from her phone. Never hears back. **Needs:** confirmation of receipt and an honest status. *(Candidate experience is a deliberate differentiator; see FR-072.)*

---

## 7. Scope

### 7.1 In scope (v1.0)

- Multi-channel CV ingestion (upload, forwarding address, WhatsApp, Gmail/Outlook sync)
- Bilingual CV parsing, Arabic and English, including scanned and photographed documents
- AI scoring against a specific job with written justification
- Candidate management, pipeline, notes, tags, bulk actions
- AI-generated screening questions and structured interview scorecards
- Templated and bulk candidate communication
- Multi-tenant accounts, roles and permissions
- Self-serve subscription billing in EGP
- Arabic and English user interface with full RTL support

### 7.2 Out of scope (v1.0)

- Payroll, attendance, leave management or any core HRMS function
- Offer letter generation and e-signature
- Manpower planning and requisition approval workflows
- Background verification services
- Video interviewing (integration only, not native)
- Candidate-facing job board or public careers marketplace

### 7.3 Explicitly deferred to v2.0

- Public branded careers page
- Native Wuzzuf / Forasna API integration (pending partner access)
- Business intelligence connector
- Mobile applications (responsive web only in v1.0)

---

## 8. Functional requirements

Priority key: **M** = Must have (v1.0 blocker) · **S** = Should have · **C** = Could have · **W** = Won't have this release

### 8.1 Intake and ingestion

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-001 | User can drag and drop multiple CV files (PDF, DOCX, DOC, JPG, PNG) up to 25 files per batch | M | 1 |
| FR-002 | Each account is issued a unique forwarding address (e.g. `jobs-{org}@masirah.online`); CVs emailed or forwarded there are ingested automatically | M | 2 |
| FR-003 | System extracts CVs from email attachments and from links to Google Drive / Dropbox in the message body | S | 2 |
| FR-004 | User can connect a Gmail or Outlook mailbox via OAuth and have CVs detected and pulled automatically | S | 3 |
| FR-005 | Account can connect a WhatsApp Business number; CVs sent as documents or images by candidates are ingested and linked to the sender's phone number | M | 2 |
| FR-006 | System deduplicates candidates across channels using email, phone number and content hash, and merges records rather than creating duplicates | M | 2 |
| FR-007 | User can paste a public LinkedIn or Wuzzuf profile URL to create a candidate record | C | 3 |
| FR-008 | System records the source channel for every application and reports on channel quality | S | 3 |

### 8.2 Parsing and extraction

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-010 | System extracts text from native PDF and DOCX files preserving reading order in multi-column layouts | M | 1 |
| FR-011 | System performs OCR on scanned PDFs and photographed CVs, including skewed and low-light phone photos | M | 1 |
| FR-012 | System parses Arabic, English and mixed Arabic/English CVs within a single document without language pre-selection. Other languages are out of scope for v1.0 and are flagged as unsupported rather than parsed and presented as understood (ADR 0005) | M | 1 |
| FR-013 | System normalises Arabic names across spelling variants (e.g. محمد / Mohamed / Mohammed / Muhammad) for search and deduplication | M | 1 |
| FR-014 | System extracts a structured profile: name, contact details, location, years of experience, employment history with dates, education, skills, languages, certifications | M | 1 |
| FR-015 | System normalises Hijri and Gregorian dates and handles Arabic-Indic numerals (٠١٢٣٤٥٦٧٨٩) | S | 1 |
| FR-016 | Parsed fields are editable by the user, and corrections are retained | M | 1 |
| FR-017 | System flags CVs it could not parse confidently and routes them to a manual review queue rather than discarding them | M | 1 |
| FR-018 | Original file is always retained and viewable in an embedded viewer alongside the parsed data | M | 1 |

### 8.3 Jobs and scoring

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-020 | User can create a job with title, description, required and preferred skills, minimum experience, location and language requirement | M | 1 |
| FR-021 | System can generate a structured job specification from a pasted free-text job description | S | 1 |
| FR-022 | System scores each candidate against a selected job on a 0–100 scale | M | 1 |
| FR-023 | Score is broken down into weighted components: skills match, experience relevance, education, tenure stability, language, location | M | 1 |
| FR-024 | Every score carries a written justification in the user's interface language, citing specific evidence from the CV | M | 1 |
| FR-025 | User can adjust component weights per job and rescore without re-parsing | S | 2 |
| FR-026 | User can rescore any candidate against any other job in the account | S | 2 |
| FR-027 | System generates a concise candidate summary (3–5 lines) in Arabic or English | M | 1 |
| FR-028 | System explicitly flags gaps, contradictions and unverifiable claims (e.g. overlapping employment dates, degree without institution) | S | 2 |
| FR-029 | Scoring excludes name, gender, age, photograph, nationality and marital status from the evaluation inputs, and this exclusion is documented and testable | M | 1 |
| FR-030 | User can enable "blind screening" mode which additionally hides these fields in the interface until shortlisting | C | 3 |

### 8.4 Screening and interview layer *(primary differentiator)*

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-040 | System generates role-specific screening questions from the job specification, with expected answer indicators | M | 2 |
| FR-041 | System generates a structured interview scorecard with weighted competencies and a rating scale | M | 2 |
| FR-042 | Interviewers can complete a scorecard in-app; scores from multiple interviewers are aggregated | S | 3 |
| FR-043 | System generates candidate-specific probing questions based on gaps or ambiguities found in that individual CV | S | 2 |
| FR-044 | User can send a short asynchronous screening questionnaire to candidates and have responses scored | C | 3 |
| FR-045 | System produces an interview summary and hire/no-hire recommendation from aggregated scorecards, clearly marked as advisory | C | 3 |

### 8.5 Candidate and pipeline management

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-050 | Candidate list view with sorting, filtering and full-text search across parsed fields, in both languages | M | 1 |
| FR-051 | Configurable pipeline stages per job, with a board view and drag-to-move | M | 2 |
| FR-052 | Bulk actions: shortlist, reject, tag, move stage, email — on a filtered selection | M | 2 |
| FR-053 | Free-text notes and @mentions on a candidate, visible to the team | S | 2 |
| FR-054 | Tags and saved filters, reusable across jobs | S | 2 |
| FR-055 | Full activity timeline per candidate, showing every status change, email and note with actor and timestamp | M | 2 |
| FR-056 | Talent pool: rejected or unplaced candidates remain searchable and can be matched against future jobs | S | 3 |
| FR-057 | Side-by-side comparison of up to four candidates | C | 3 |

### 8.6 Communication

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-060 | Bilingual email templates with merge variables, per account | M | 2 |
| FR-061 | Bulk email sending to a filtered candidate selection, with rate limiting and deliverability safeguards | M | 2 |
| FR-062 | WhatsApp message sending to candidates using approved message templates | S | 3 |
| FR-063 | Interview scheduling with calendar integration (Google Calendar, Outlook) and candidate self-booking links | S | 3 |
| FR-064 | Automatic acknowledgement to every candidate on application receipt | M | 2 |
| FR-065 | Automatic rejection notification triggered by stage change, with a configurable delay | S | 2 |

### 8.7 Accounts, permissions and administration

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-070 | Multi-tenant organisations with strict data isolation | M | 1 |
| FR-071 | Roles: Owner, Recruiter/Admin, Hiring Manager (job-scoped, read and comment), Interviewer (scorecard only) | M | 2 |
| FR-072 | Candidate status portal — a tokenised link letting a candidate see their application status without an account | C | 3 |
| FR-073 | Agency mode: one login managing multiple isolated client workspaces | S | 3 |
| FR-074 | Full audit log of data access and export, retained for 12 months | S | 3 |
| FR-075 | Data export: CSV, Excel, and formats importable by Workable and Greenhouse | M | 2 |
| FR-076 | Account-level data deletion that removes candidate personal data within 30 days of request | M | 2 |

### 8.8 Billing

| ID | Requirement | Priority | Phase |
|---|---|---|---|
| FR-080 | Self-serve signup with no sales contact required | M | 3 |
| FR-081 | Free tier enforced by monthly CV quota | M | 3 |
| FR-082 | Monthly and annual subscription in EGP via Paymob (card, Fawry, Instapay, mobile wallets) | M | 3 |
| FR-083 | USD subscription for Gulf and international customers via Stripe | S | 4 |
| FR-084 | In-app usage meter showing CVs processed against quota, with warnings at 80% and 100% | M | 3 |
| FR-085 | Self-serve plan upgrade, downgrade and cancellation | M | 3 |
| FR-086 | Add-on purchase of additional CV volume blocks | S | 4 |
| FR-087 | Subscription checkout offers a monthly / annual toggle with the annual saving shown; the user can switch billing period mid-subscription with a prorated adjustment | M | 3 |
| FR-088 | Promotional codes grant either a percentage discount or a defined number of free months; each code carries an expiry date, a maximum redemption count and an optional plan restriction | M | 3 |
| FR-089 | An internal administrator can grant a specific organisation N free months directly, with the reason and actor recorded in the audit log | M | 3 |
| FR-090 | An account inside a granted free period retains full plan features, sees the remaining free time on its billing screen, and is notified 14 days and 3 days before it ends | M | 3 |
| FR-091 | At the end of a granted free period the account converts to paid if a payment method is stored, and otherwise downgrades to the Free tier without data loss | M | 3 |
| FR-092 | Referral programme: an existing customer and the customer they refer each receive one free month, credited on the referred account's first payment | S | 4 |
| FR-093 | An early-adopter flag locks an account's price for a defined period regardless of later list-price changes | S | 4 |
| FR-094 | Internal back-office console for granting free periods, issuing promotional codes, adjusting quotas and inspecting account state | M | 3 |

---

## 9. Non-functional requirements

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | A single CV is parsed and scored within 30 seconds at p95 |
| NFR-02 | Performance | A batch of 100 CVs completes within 10 minutes |
| NFR-03 | Performance | Candidate list loads within 2 seconds for accounts holding up to 50,000 candidates |
| NFR-04 | Availability | 99.5% monthly uptime for paid tiers |
| NFR-05 | Scalability | Architecture supports 1,000 organisations and 5 million stored CVs without redesign |
| NFR-06 | Localisation | Complete Arabic and English UI with correct RTL layout, including mixed-direction text, forms, tables and PDF export |
| NFR-07 | Security | Encryption in transit (TLS 1.2+) and at rest; row-level security enforcing tenant isolation at the database layer |
| NFR-08 | Security | Passwords hashed with a modern KDF; optional two-factor authentication; SSO for Enterprise |
| NFR-09 | Privacy | Compliance with Egypt's Personal Data Protection Law (Law No. 151 of 2020) — *legal review required, see OQ-04* |
| NFR-10 | Privacy | Configurable candidate data retention with automatic purge; default 24 months |
| NFR-11 | Accessibility | WCAG 2.1 Level AA for all recruiter-facing screens |
| NFR-12 | Compatibility | Latest two versions of Chrome, Edge, Safari and Firefox; fully responsive from 360px width |
| NFR-13 | Cost | AI inference cost per CV ≤ 1.5 EGP at expected volume; results cached by file hash to prevent duplicate spend |
| NFR-14 | Observability | Structured logging, error tracking, and per-tenant usage metrics; alerting on parse failure rate above 5% |
| NFR-15 | Recoverability | Daily automated backups with a tested 24-hour recovery point objective |

---

## 10. Data model — core entities

| Entity | Purpose | Key relationships |
|---|---|---|
| `organisation` | Tenant root; owns all other records | 1→N users, jobs, candidates |
| `user` | Account member with a role | N→1 organisation |
| `job` | A role being hired for, with its specification | N→1 organisation; 1→N applications |
| `candidate` | A person, deduplicated across applications | N→1 organisation; 1→N applications |
| `cv_file` | The original uploaded artefact and its storage reference | N→1 candidate |
| `parsed_profile` | Structured extraction from a `cv_file`, versioned | 1→1 cv_file |
| `application` | A candidate's link to a specific job, carrying stage | N→1 candidate, N→1 job |
| `score` | An AI evaluation of an application, versioned by model and prompt | N→1 application |
| `pipeline_stage` | Configurable stage definition per job | N→1 job |
| `scorecard` | Structured interview evaluation | N→1 application |
| `message` | Email or WhatsApp sent to a candidate | N→1 candidate |
| `template` | Reusable message body, per language | N→1 organisation |
| `activity` | Immutable audit event | Polymorphic |
| `subscription` | Plan, quota and billing state | 1→1 organisation |
| `usage_event` | Metered CV processing record | N→1 organisation |
| `promo_code` | Redeemable code granting a discount or free months, with expiry and redemption cap | N→1 organisation (issuer scope) |
| `subscription_credit` | A granted free period or discount applied to an organisation, with grantor, reason and expiry | N→1 organisation |
| `referral` | Link between referring and referred organisation, and the credits issued to each | N→1 organisation |

---

## 11. Integrations

| Integration | Purpose | Priority | Dependency risk |
|---|---|---|---|
| Email inbound (Resend / Postmark webhook) | Forwarding-address ingestion | M | Low |
| WhatsApp Business Cloud API (Meta) | Candidate CV intake and messaging | M | Medium — template approval and per-message cost |
| Gmail / Outlook OAuth | Direct mailbox sync | S | High — Google restricted-scope verification takes 6–10 weeks |
| Paymob | EGP payment collection | M | Low |
| Stripe | USD payment collection | S | Low |
| Google Calendar / Outlook Calendar | Interview scheduling | S | Low |
| Wuzzuf / Forasna | Job posting and applicant sync | C (v2) | High — requires partner agreement; no public API assumed |
| LLM provider (Anthropic / OpenAI) | Parsing assistance, scoring, generation | M | Medium — cost and rate limits; abstract behind a provider interface |
| OCR engine | Scanned and photographed CVs | M | Low — vision LLM primary, Tesseract fallback |

---

## 12. AI requirements and cost control

| ID | Requirement |
|---|---|
| AI-01 | All model interactions use structured output schemas; free-text model responses are never parsed heuristically |
| AI-02 | Every score record stores the model identifier, prompt version and input hash, so any result is reproducible and auditable |
| AI-03 | Parsing results are cached by file content hash; re-uploading an identical CV incurs no inference cost |
| AI-04 | Scoring is cached per (candidate, job, weighting) tuple; changing weights triggers a cheap recomputation, not a re-parse |
| AI-05 | A cheaper model handles extraction and summarisation; a stronger model handles scoring and justification |
| AI-06 | Per-organisation rate limits and a hard monthly spend ceiling prevent runaway cost from a single tenant |
| AI-07 | Model outputs are advisory. The interface must never present a score as an automated hiring decision, and must require a human action to reject a candidate |
| AI-08 | Bias testing: a documented test suite verifies that identical CVs differing only in name, gender or nationality receive scores within a defined tolerance |
| AI-09 | Customer data is never used to train third-party models; this must be contractually confirmed with the provider and stated in the privacy policy |

---

## 13. Proposed commercial model

> Positioned deliberately below the competitor band (Recruitera 55,000–96,000 EGP/yr; RecDesk 40,000–70,000 EGP/yr) and inside the buyer's existing monthly job-board anchor.

| Plan | Price | Users | CVs / month | Purpose |
|---|---|---|---|---|
| **Free** | 0 EGP | 1 | 30 | Acquisition; no card required; full scoring, no branding removal |
| **Starter** | 900 EGP / month · 9,000 EGP / year | 3 | 300 | The uncontested SME segment |
| **Growth** | 2,500 EGP / month · 25,000 EGP / year | 8 | 1,500 | Scaling companies; adds WhatsApp channel, scheduling, scorecards |
| **Agency** | 4,500 EGP / month · 45,000 EGP / year | 15 | 4,000 | Multi-client workspaces, white-label export |
| **Enterprise** | Custom | Unlimited | Negotiated | SSO, API, SLA, security review |

Annual pricing offers roughly two months free. All prices exclusive of VAT.


### 13.1 Billing periods, promotions and granted free periods

- Every paid plan is purchasable **monthly or annually**. Annual billing is presented as "two months free" rather than a percentage, which tests better against a monthly price anchor.
- A customer can move between monthly and annual at any time; the change is prorated against the unused portion of the current period (FR-087).
- **Promotional codes** (FR-088) support two forms: a percentage discount for a number of billing cycles, or a number of entirely free months. Each code is bounded by an expiry date, a redemption cap and optionally a specific plan.
- **Granted free periods** (FR-089) are issued manually from the internal console, not by code, and are the mechanism for pilot companies, design partners, early adopters and goodwill credits. The grant is auditable — who granted it, to whom, for how long and why.
- A granted period never silently becomes a charge. The account is warned twice before expiry and, absent a stored payment method, lands on the Free tier with its data intact (FR-090, FR-091).

**Suggested launch offers:**

| Offer | Mechanism | Rationale |
|---|---|---|
| Pilot companies — 6 months free on Growth | Manual grant (FR-089) | Buys real CV volume and honest feedback during Phases 1–2 |
| First 50 self-serve signups — 3 months free | Promotional code (FR-088) | Creates urgency at launch without discounting the list price permanently |
| Early-adopter price lock — 12 months | Account flag (FR-093) | Rewards early risk without eroding future pricing power |
| Referral — 1 free month each side | Referral programme (FR-092) | The cheapest acquisition channel available to a bootstrapped product |

---

## 14. Release plan

| Phase | Scope | Requirements | Target duration | Exit criterion |
|---|---|---|---|---|
| **Phase 0 — Validation** | Landing page, waitlist, 8 structured customer interviews | — | 2 weeks | 5 companies commit to piloting with real CV volume |
| **Phase 1 — Core screening** | Upload, parse, OCR, score, justify, candidate list. Single user, no billing | FR-001, FR-010–018, FR-020–029, FR-050, FR-070 | 4 weeks | A pilot company processes 200 real CVs and agrees the ranking is defensible |
| **Phase 2 — Channels and pipeline** | Forwarding address, WhatsApp intake, deduplication, pipeline, bulk actions, templates, screening questions | FR-002, FR-005, FR-006, FR-040–041, FR-051–055, FR-060–061, FR-064, FR-071, FR-075–076 | 5 weeks | Pilot companies stop uploading manually |
| **Phase 3 — Commercial launch** | Self-serve signup, Paymob billing, quotas, Gmail/Outlook OAuth, scheduling, agency mode | FR-004, FR-062–063, FR-072–074, FR-080–085 | 5 weeks | First unassisted self-serve paid conversion |
| **Phase 4 — Expansion** | Scorecard aggregation, talent pool matching, USD billing, careers page, job board integrations | FR-042–045, FR-056, FR-083, FR-086 | Ongoing | — |

---

## 15. Success metrics

| Metric | Phase 1 target | 12-month target |
|---|---|---|
| Parse accuracy on native PDFs (key fields correct) | ≥ 95% | ≥ 98% |
| Parse accuracy on photographed / scanned CVs | ≥ 85% | ≥ 92% |
| Unsupported-language CVs flagged rather than mis-parsed | 100% | 100% |
| Recruiter agreement with top-10 AI ranking | ≥ 80% | ≥ 90% |
| Median time from CV received to shortlist decision | < 24 hours | < 4 hours |
| Free-to-paid conversion | — | ≥ 5% |
| Monthly logo churn | — | ≤ 3% |
| AI cost per CV | ≤ 2.5 EGP | ≤ 1.5 EGP |
| Paying organisations | — | 150 |

---

## 16. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Wuzzuf improves its bundled ATS and removes the reason to buy | Medium | High | Compete on screening depth and multi-channel intake, which Wuzzuf structurally cannot offer for non-Wuzzuf applicants |
| R-02 | Recruitera or RecDesk launches a free tier first | Medium | High | Speed to a genuine free tier; treat it as a launch requirement, not a later addition |
| R-03 | Arabic parsing quality is materially worse than English | High | High | Build a labelled Arabic CV test set in Phase 1; make FR-012 accuracy an explicit release gate |
| R-04 | WhatsApp Business API cost or template approval blocks the channel | Medium | Medium | Design intake to work with the forwarding address alone; treat WhatsApp as additive |
| R-05 | Google OAuth restricted-scope verification is delayed or refused | High | Medium | Forwarding address is the primary mechanism (FR-002); Gmail sync is a convenience, never a dependency |
| R-06 | AI cost per CV exceeds the unit economics of the Starter plan | Medium | High | Caching (AI-03/04), tiered models (AI-05), hard quotas (FR-081), spend ceilings (AI-06) |
| R-07 | Low ARPU makes the self-serve segment unprofitable to support | Medium | Medium | Support must be documentation- and in-product-led; no human onboarding below Growth tier |
| R-08 | Egyptian PDPL obligations impose licensing or localisation requirements | Medium | High | Obtain legal opinion before processing production candidate data (OQ-04) |
| R-09 | Founder capacity — this is being built alongside a full-time role | High | High | Ruthless Phase 1 scope; no feature enters v1.0 that is not required to prove the core loop |
| R-10 | A customer treats an AI score as an automated hiring decision and faces a discrimination claim | Low | High | AI-07 human-in-the-loop enforcement, AI-08 bias testing, FR-029 protected-attribute exclusion, clear terms of service |

---

## 17. Open questions and decisions required

Decisions confirmed 11 September 2026 are struck through with their resolution. OQ-04 and OQ-07 remain genuinely open.

| ID | Question | Owner | Needed by |
|---|---|---|---|
| OQ-01 | ~~Confirm strategic option A, B or C (Section 5)~~ **Resolved** — Option A (self-serve SME wedge) combined with Option B (screening depth as the feature bet); ADR 0001 | Amr | Before Phase 1 |
| OQ-02 | ~~Is this a solo build, or will there be a co-founder or contractor? This determines realistic phase durations~~ **Resolved** — solo build, part-time alongside another commitment; phase durations in Section 14 should be read as optimistic and roughly doubled in planning | Amr | Before Phase 1 |
| OQ-03 | ~~Is the "Masirah" name and domain available in the required TLDs, and is it registrable as a trademark in Egypt?~~ **Resolved** — domain `masirah.online` purchased; founder chose not to pursue further TLD/trademark research | Amr | Before Phase 0 ends |
| OQ-04 | **Still open, and now needed earlier** — legal opinion on Egypt PDPL Law 151/2020: registration, licensing and cross-border transfer obligations when processing candidate data on non-Egyptian infrastructure. *Sequencing revised 11 Sep 2026: development and parser testing use anonymised CVs, but Phase 1 validation runs on pilot-company data with the pilot acting as data controller (ADR 0003). Written confirmation of that arrangement is required before Phase 1 validation begins.* | External counsel | **Before Phase 1 validation** |
| OQ-05 | ~~Hosting decision: managed platform (Vercel/Supabase) versus self-hosted (Hetzner/Coolify)~~ **Resolved** — Supabase for backend and database, Netlify for the site through Phases 1-2, then migration to a separate server before Phase 3; ADR 0002 | Amr | Before Phase 1 |
| OQ-06 | ~~Is there any commercial relationship possible with Wuzzuf or Forasna, or must integration be assumed hostile?~~ **Resolved** — no relationship exists; integration is assumed non-cooperative and any partnership question is deferred to Phase 4 | Amr | Before Phase 4 |
| OQ-07 | **Still open — deliberately deferred.** Which entity will contract with customers, and how will EGP revenue be invoiced and taxed? Does not block Phases 1-2; must be settled before Phase 3 commercial launch | Amr | Before Phase 3 |
| OQ-08 | ~~Confirm the free tier quota (30 CVs/month) is generous enough to be useful but small enough to convert~~ **Resolved** — 30 CVs/month stands for launch; revisit after observing real consumption in the first month of live use | Amr | Before Phase 3 |
| OQ-09 | **Open, deliberately deferred.** Two expansions, both out of scope for v1.0 and neither blocking it. First, which languages beyond Arabic and English to support (ADR 0005); each addition needs a labelled corpus before it can carry an accuracy gate. Second, whether to sell to employers outside Egypt, which would reopen the competitive analysis, the EGP-only pricing, the personas and the positioning in ADR 0001 | Amr | Before Phase 4 |

---

## 18. Assumptions

- The founder has direct hiring-domain experience and access to real Egyptian CV samples and pilot companies.
- No external funding is assumed; the build is bootstrapped and phase durations reflect part-time capacity.
- Job board integrations are assumed unavailable until a partner agreement exists; no v1.0 requirement depends on them.
- Candidate volumes cited (150–800 per role) are based on the founder's own hiring experience and require validation across pilot accounts.

---

## 19. Glossary

| Term | Definition |
|---|---|
| ATS | Applicant Tracking System — software managing candidates through hiring stages |
| BRD | Business Requirements Document — this document |
| CAC | Customer Acquisition Cost |
| KDF | Key Derivation Function, used for password hashing |
| MoSCoW | Prioritisation method: Must / Should / Could / Won't |
| OCR | Optical Character Recognition — extracting text from images |
| PDPL | Personal Data Protection Law (Egypt, Law No. 151 of 2020) |
| RTL | Right-to-left text direction, required for Arabic |
| RLS | Row-Level Security — database-enforced tenant isolation |
| SME | Small and Medium Enterprise |
