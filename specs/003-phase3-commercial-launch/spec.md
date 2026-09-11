# Feature Specification: Phase 3 Commercial Launch

**Feature Branch**: `003-phase3-commercial-launch`

**Created**: 2026-09-11

**Status**: Draft, forward-looking

**Input**: Written as part of specifying all four phases up front, to give a clear picture of the
whole product before building begins.

Phases 1 and 2 built something pilot companies use. Phase 3 turns it into a business: a stranger
finds the product, signs up, uses a free tier, hits its limit and pays, all without speaking to
anyone. This is where the entire commercial thesis in the BRD is tested, since that thesis is
self-serve monthly pricing rather than technical differentiation.

**Exit criterion**: the first unassisted self-serve paid conversion.

> **This is a forward-looking specification.** It rests on two phases that do not exist yet and on
> at least one decision that is deliberately still open, namely which legal entity contracts with
> customers. Expect substantial revision before this phase starts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign up and start working without talking to anyone (Priority: P1)

A recruiter at a company nobody has heard of finds Masirah, creates an account, uploads thirty CVs
and gets a ranking, all before any human at Masirah knows they exist. When she hits the free limit
she enters a card and continues.

**Why this priority**: This story is the phase exit criterion and the business model in one. Every
competitor named in the BRD requires a sales call. This is the entire wedge.

**Independent Test**: From a clean browser with no prior contact, complete signup, process CVs to
the free limit, upgrade, and confirm no human intervention was required at any point.

**Acceptance Scenarios**:

1. **Given** a visitor with no account, **When** they sign up, **Then** they reach a working product
   with no sales contact, no approval step and no manual provisioning.
2. **Given** a free account, **When** CVs are processed, **Then** the usage meter shows consumption
   against the monthly quota, and warns at 80 and 100 percent.
3. **Given** a free account at its quota, **When** further CVs are submitted, **Then** processing
   stops cleanly with an explanation, and no data already in the account is lost or hidden.
4. **Given** a user deciding to pay, **When** they choose a plan, **Then** they can pay in Egyptian
   pounds by card, Fawry, Instapay or mobile wallet.
5. **Given** the checkout screen, **When** they compare billing periods, **Then** monthly and annual
   are both offered with the annual saving shown as two months free.
6. **Given** a paying customer, **When** they upgrade, downgrade or cancel, **Then** they do it
   themselves, and a mid-period billing change is settled prorata.

---

### User Story 2 - Run promotions and grant free time (Priority: P1)

The founder gives six free months to pilot companies, issues a launch code for the first fifty
signups, and can see exactly who was granted what and why.

**Why this priority**: The launch offers in the BRD depend on this, and a granted free period that
silently becomes a charge would damage the trust the self-serve model runs on.

**Independent Test**: Grant a free period from the internal console, confirm the account keeps full
plan features, receives both warnings, and lands on the free tier with data intact when it expires
without a stored card.

**Acceptance Scenarios**:

1. **Given** the internal console, **When** an administrator grants an organisation free months,
   **Then** the grant records who issued it, to whom, for how long and why.
2. **Given** a promotional code, **When** it is created, **Then** it carries an expiry, a redemption
   cap and optionally a plan restriction, and grants either a percentage discount or whole free
   months.
3. **Given** an account inside a granted free period, **When** the user opens billing, **Then** the
   remaining free time is visible, and warnings arrive 14 days and 3 days before it ends.
4. **Given** a granted period ending with a stored payment method, **When** it expires, **Then** the
   account converts to paid.
5. **Given** a granted period ending with no stored payment method, **When** it expires, **Then** the
   account downgrades to the free tier without losing any data.

---

### User Story 3 - Let the inbox and calendar do the work (Priority: P2)

The recruiter connects her Gmail and stops forwarding. She sends interview invitations with a
booking link instead of proposing times back and forth.

**Why this priority**: A genuine convenience, but explicitly never a dependency. Risk R-05 records
that Google's restricted-scope verification takes six to ten weeks and may be refused, which is why
the forwarding address from Phase 2 remains the primary channel.

**Independent Test**: Connect a mailbox, confirm CVs are detected and pulled. Then revoke the
connection and confirm intake continues unaffected through the forwarding address.

**Acceptance Scenarios**:

1. **Given** a Gmail or Outlook mailbox, **When** the user connects it by OAuth, **Then** CVs are
   detected and pulled automatically.
2. **Given** a revoked or failed mailbox connection, **When** it stops working, **Then** the user is
   told plainly and intake continues by forwarding address without interruption.
3. **Given** a shortlisted candidate, **When** the recruiter schedules an interview, **Then**
   calendar integration creates the event and the candidate can self-book from a link.
4. **Given** approved WhatsApp templates, **When** the recruiter messages a candidate, **Then** the
   message sends through the same thread the candidate applied on.

---

### User Story 4 - Give candidates and agencies what they need (Priority: P2)

A candidate follows a link and sees honestly where their application stands. An independent
recruiter runs eight clients from one login without their data touching.

**Why this priority**: Candidate experience is a named differentiator in the BRD, and agency mode
opens a second customer segment that the persona work already identifies.

**Independent Test**: Open a candidate status link with no account and confirm it shows status and
nothing else. Separately, confirm two client workspaces under one agency login cannot see each
other.

**Acceptance Scenarios**:

1. **Given** a candidate with a tokenised link, **When** they open it, **Then** they see their own
   application status without creating an account, and nothing about any other candidate.
2. **Given** an expired or tampered token, **When** it is used, **Then** access is refused.
3. **Given** an agency login, **When** the user switches between client workspaces, **Then** each
   workspace is fully isolated, enforced at the data layer.
4. **Given** an agency exporting for a client, **When** the export runs, **Then** it can be produced
   in that client's format.

---

### User Story 5 - Deepen the interview layer (Priority: P3)

Interviewers fill scorecards in the product rather than in their heads. Several interviewers on one
candidate aggregate into a comparable picture. Rejected candidates stay findable for future roles.

**Why this priority**: Valuable and differentiating, but nothing here blocks the first paid
conversion, which is what this phase is judged on.

**Independent Test**: Have two interviewers complete scorecards on one candidate and confirm the
aggregate presents both without averaging away disagreement.

**Acceptance Scenarios**:

1. **Given** an interviewer, **When** they complete a scorecard in the product, **Then** it is stored
   against that application.
2. **Given** several completed scorecards, **When** they are aggregated, **Then** disagreement
   between interviewers is visible rather than hidden behind a mean.
3. **Given** aggregated scorecards, **When** a summary and hire recommendation are produced, **Then**
   both are clearly marked advisory and never presented as a decision.
4. **Given** a candidate rejected for an earlier role, **When** a new job is created, **Then** they
   remain searchable and can be matched against it.
5. **Given** up to four candidates, **When** the recruiter compares them, **Then** they appear side
   by side on comparable fields.
6. **Given** blind screening enabled, **When** the recruiter reviews candidates, **Then** name,
   gender, age, photograph, nationality and marital status are hidden in the interface until
   shortlisting.

---

### Edge Cases

- A Paymob payment succeeds at the bank but the confirmation callback never arrives.
- A card is declined at renewal on an account holding 40,000 candidates. Data must not be destroyed
  while the customer sorts out payment.
- A user redeems a promotional code that expired one minute ago.
- Two users in the same organisation attempt to upgrade simultaneously.
- A customer downgrades to a plan whose quota is below what they have already consumed this month.
- A granted free period and a promotional code apply to the same account at once.
- Google refuses restricted-scope verification outright, which risk R-05 rates as likely.
- An agency user is removed from one client workspace while holding notes in another.
- A candidate opens their status link after the account that created it was deleted.
- Quota is consumed by re-processing the same CV, which caching should already prevent.
- A customer requests a VAT invoice, which depends on the still-open entity question.

## Requirements *(mandatory)*

Numbering is local to this specification.

- **FR-001**: Users MUST be able to sign up and reach a working product with no sales contact.
- **FR-002**: System MUST enforce a free tier bounded by a monthly CV quota.
- **FR-003**: System MUST collect monthly and annual subscriptions in Egyptian pounds by card,
  Fawry, Instapay and mobile wallets.
- **FR-004**: System MUST show an in-product usage meter with warnings at 80 and 100 percent of
  quota.
- **FR-005**: Users MUST be able to upgrade, downgrade and cancel without assistance.
- **FR-006**: Checkout MUST offer monthly and annual with the annual saving shown, and a mid-period
  change MUST be settled prorata.
- **FR-007**: System MUST support promotional codes granting a percentage discount or whole free
  months, each bounded by expiry, redemption cap and optional plan restriction.
- **FR-008**: An internal administrator MUST be able to grant an organisation free months directly,
  with reason and actor recorded in the audit log.
- **FR-009**: An account in a granted free period MUST retain full plan features, see remaining time,
  and be warned 14 days and 3 days before expiry.
- **FR-010**: At the end of a granted period the account MUST convert to paid if a payment method is
  stored, and otherwise downgrade to free without data loss.
- **FR-011**: System MUST provide an internal back-office console for grants, promotional codes,
  quota adjustment and account inspection.
- **FR-012**: Users MUST be able to connect a Gmail or Outlook mailbox by OAuth and have CVs
  detected and pulled.
- **FR-013**: System MUST report on the quality of each source channel.
- **FR-014**: Users MUST be able to create a candidate from a pasted public LinkedIn or Wuzzuf
  profile URL.
- **FR-015**: System MUST support interview scheduling with calendar integration and candidate
  self-booking links.
- **FR-016**: System MUST send WhatsApp messages to candidates using approved templates.
- **FR-017**: Candidates MUST be able to see their application status through a tokenised link
  without an account.
- **FR-018**: System MUST support agency mode, one login managing isolated client workspaces.
- **FR-019**: Interviewers MUST be able to complete scorecards in the product, and multiple
  scorecards MUST aggregate with disagreement visible.
- **FR-020**: System MUST produce an interview summary and hire recommendation from aggregated
  scorecards, clearly marked advisory.
- **FR-021**: Users MUST be able to send candidates a short asynchronous screening questionnaire and
  have responses scored.
- **FR-022**: Rejected and unplaced candidates MUST remain searchable and matchable against future
  jobs.
- **FR-023**: Users MUST be able to compare up to four candidates side by side.
- **FR-024**: Users MUST be able to enable blind screening, hiding protected attributes in the
  interface until shortlisting.

### Key Entities

Phases 1 and 2 entities continue. New in this phase:

- **Subscription**: Plan, quota and billing state for an organisation.
- **Usage event**: A metered CV processing record, the basis of quota enforcement.
- **Promo code**: A redeemable code with expiry, cap and optional plan restriction.
- **Subscription credit**: A granted free period or discount, with grantor, reason and expiry.
- **Scorecard**: A completed interview evaluation against an application.
- **Client workspace**: An isolated tenant inside an agency account.

## Success Criteria *(mandatory)*

- **SC-001**: A paying customer completes signup, usage, and payment with zero human contact. This
  is the phase exit criterion.
- **SC-002**: At least 40 percent of paid conversions complete with no human sales contact.
- **SC-003**: Free-to-paid conversion reaches at least 5 percent.
- **SC-004**: A granted free period never becomes a charge without the account having been warned
  twice.
- **SC-005**: No account loses data as a result of a failed payment, downgrade or expiry.
- **SC-006**: Quota enforcement is exact. No account processes more than its plan allows, and no
  cached re-processing consumes quota.
- **SC-007**: Intake continues uninterrupted when a mailbox connection fails or is revoked.
- **SC-008**: A candidate status link discloses only that candidate's own status.
- **SC-009**: Two client workspaces in one agency account cannot reach each other by any route.
- **SC-010**: Processing cost falls to 1.5 EGP or less per CV at expected volume.

## Assumptions

- Phases 1 and 2 have shipped and pilot companies are using the product daily.
- **The legal entity question, OQ-07, is resolved before this phase starts.** It is currently open
  and deliberately deferred. Nothing in this phase can ship without knowing who contracts with
  customers and how Egyptian pound revenue is invoiced and taxed. This is the single hardest
  dependency in the specification.
- Hosting has migrated off Netlify to a separate server, per ADR 0002, before commercial traffic
  arrives.
- The PDPL legal opinion, OQ-04, has been obtained, since paying customers processing their own
  candidates cannot rest on the pilot arrangement in ADR 0003.
- Paymob is the Egyptian pound processor. Stripe and dollar billing are Phase 4.
- Google restricted-scope verification may be refused. Every requirement here treats mailbox sync as
  additive, never as a dependency.
- Pricing follows BRD section 13 unless the free tier quota is revised after observing real
  consumption, which OQ-08 anticipates.

## Traceability to the BRD

| BRD | Requirement | Spec | Story |
|---|---|---|---|
| FR-080 | Self-serve signup | FR-001 | US1 |
| FR-081 | Free tier quota | FR-002 | US1 |
| FR-082 | EGP billing via Paymob | FR-003 | US1 |
| FR-084 | Usage meter with warnings | FR-004 | US1 |
| FR-085 | Self-serve plan changes | FR-005 | US1 |
| FR-087 | Billing period toggle and proration | FR-006 | US1 |
| FR-088 | Promotional codes | FR-007 | US2 |
| FR-089 | Administrator-granted free months | FR-008 | US2 |
| FR-090 | Free period visibility and warnings | FR-009 | US2 |
| FR-091 | Conversion or downgrade at expiry | FR-010 | US2 |
| FR-094 | Internal back-office console | FR-011 | US2 |
| FR-004 | Gmail and Outlook OAuth sync | FR-012 | US3 |
| FR-008 | Channel quality reporting | FR-013 | US3 |
| FR-007 | Candidate from a profile URL | FR-014 | US3 |
| FR-063 | Interview scheduling and self-booking | FR-015 | US3 |
| FR-062 | WhatsApp messaging with templates | FR-016 | US3 |
| FR-072 | Candidate status portal | FR-017 | US4 |
| FR-073 | Agency mode | FR-018 | US4 |
| FR-042 | Scorecard completion and aggregation | FR-019 | US5 |
| FR-045 | Interview summary and recommendation | FR-020 | US5 |
| FR-044 | Asynchronous screening questionnaire | FR-021 | US5 |
| FR-056 | Talent pool matching | FR-022 | US5 |
| FR-057 | Side-by-side comparison | FR-023 | US5 |
| FR-030 | Blind screening mode | FR-024 | US5 |

All twenty-four Phase 3 requirements are covered.

**FR-074, the access audit log, is absent** because ADR 0003 moved it into Phase 1 when real pilot
data was brought forward. The console grant in FR-008 above writes to that existing log rather than
introducing a new one.
