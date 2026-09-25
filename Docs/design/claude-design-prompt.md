# Design brief for Claude Design

Paste everything below the line into Claude Design. It is self-contained: the product, the people,
the visual system already decided, the decisions left open, and every surface in every release
phase. Sources: `PRODUCT.md`, `DESIGN.md`, `Docs/BRD_Masirah_EN.md` and `specs/00*/spec.md`.

---

# Masirah (مسيرة): design the product, the website and the admin console

You are designing Masirah, a bilingual Arabic and English CV screening platform for small and
medium companies in Egypt. It turns a pile of CVs into a ranked shortlist that a hiring manager
will actually trust. Please design its visual system and its screens across all four release
phases: the recruiter application, the public website, the customer's own administration, Masirah's
internal back-office console, and the few pages candidates see.

Read the whole brief before starting. The visual direction is already decided in detail. Your job
is to execute it with craft and to settle the values it leaves open, not to propose a new direction.

## 1. The product in one paragraph

A recruiter creates a job, drops CVs onto it up to 25 at a time (PDF, Word, or phone photos of
printed CVs, in Arabic, English or both; a role with 300 applicants takes several uploads), and
gets every candidate ranked against the job. Each candidate has a
0 to 100 score broken into six weighted components: skills match, experience relevance, education,
tenure stability, language, location. Every score comes with a written justification that quotes
the CV lines it relied on. The machine advises; a person decides. The real competitor is not
another hiring system but an inbox and a spreadsheet, which are free, familiar and need no
training. The product must feel like something a person starts using on a Tuesday afternoon with no
sales call, priced in Egyptian pounds with a genuine free tier.

## 2. The people

- **Nourhan, HR generalist at a 60-person company. The primary user.** Handles hiring alongside
  payroll and admin, receives about 300 CVs per role, works in Arabic, and today gives up opening
  CVs one by one around the fortieth. She needs speed, and something she can start today without
  asking anyone. Context: a small office, a laptop, time pressure, a manager waiting.
- **Tarek, engineering manager. Decides whether the product is believed.** He re-reads every CV
  himself because he does not trust shortlists. He wants evidence, not a number: a defensible
  reason for each ranking position.
- **Mahmoud, independent recruiter.** Runs eight to fifteen roles for several client companies at
  once. Price- and volume-sensitive. Needs client separation and throughput.
- **Sara, candidate.** Applies by WhatsApp from her phone and never hears back. Not a customer, but
  her experience is a deliberate differentiator.
- **The Masirah founder, internal administrator.** Grants free months to pilot companies, issues
  promotional codes, adjusts quotas and inspects accounts from an internal console.

## 3. Principles that decide every trade-off

1. **Evidence before verdict.** The justification and the CV text it cites are the primary content
   of a scored candidate. The number supports them and is never the headline.
2. **The machine advises, the human decides.** No screen presents a score as a decision.
   Rejecting a candidate is always a deliberate human action that records who did it. This is a
   product requirement (FR-023), not a styling preference, and it constrains layout, copy and
   interaction. Whether Egypt's data protection law (Law 151 of 2020) also requires it is still
   awaiting a legal opinion.
3. **Arabic is the original, not the translation.** Right-to-left is designed first, not mirrored
   afterwards.
4. **Density without noise.** Three hundred candidates must feel finishable. The answer is
   hierarchy and rhythm, not whitespace and pagination.
5. **Nothing is ever silently lost.** Every CV either produces a profile or appears somewhere
   visible: queued, processing, needs review, failed with a reason, or flagged as an unsupported
   language. Failures, including the product's own, are shown honestly.

Brand personality: **precise, calm, credible.** A serious instrument that does not shout. The voice
is specific, never congratulates, never celebrates, and never calls its own output intelligent.
Where the product is uncertain it says so plainly, because visible uncertainty is what makes the
confident cases believable.

References, for specific reasons: **Perplexity and Elicit** (evidence sits beside the claim and
traces to its source, which is exactly the score, justification and quoted-CV problem), **Linear**
(dense, calm, fast, color only where it means something; the model for the candidate list), and
**Stripe Dashboard** (consequential data made legible; the model for the score breakdown).

Anti-references: **enterprise applicant tracking systems** (Workable, Greenhouse, SuccessFactors:
grey chrome, configuration walls, screens that assume a full-time administrator), **consumer app
playfulness** (illustrations, rounded friendliness, celebratory animation, emoji), and **local job
board clutter** (Wuzzuf and peers: ads, competing calls to action, density with no hierarchy).

## 4. The visual system: "The Reading Room"

A quiet, well-lit room where a document lies open and someone works through it carefully. The
recruiter's real activity is reading: a CV on one side, the system's reasoning on the other, moving
between them to check whether the machine is right.

**Color: the isolated amber palette.**

- Canvas is exactly `oklch(1 0 0)`, pure white, everywhere. Panels match the page. No cream, sand,
  beige or any warm tint.
- Greys have zero chroma, so amber is the only accent on screen.
- **Amber** (identity anchor `oklch(0.774 0.174 65.1)`, hue 65) is the single accent color. The
  only other hues are the error, warning and success colors in section 7, which stay dark and low
  in chroma, appear only inside their own messages, and always come with an icon and words. Amber
  marks primary actions, the selected row and focus rings, and nothing else: not headings, icons,
  borders, scores or empty states. It covers well under ten percent of any screen. The anchor cannot
  carry white text at WCAG AA, so the interactive primary is the same hue at roughly 0.55
  lightness. Amber was chosen because blue belongs to LinkedIn and the job boards, green to
  Greenhouse, and purple is the generic AI tell. It also carries the name: مسيرة means journey.
- **No information by hue alone.** Screenshot any screen, convert it to greyscale, and nothing may
  be lost. This applies hardest to scores: never grade red to green. Use position, bars, numerals,
  text and pattern.

**Type.** One family carrying Arabic and Latin as equals, no display face anywhere in the
interface. Personality comes from weight and spacing. The same sentence in both scripts at the same
size must look equally substantial. Fixed rem steps, never fluid `clamp()` sizes inside the
product. Prose caps at 65 to 75 characters; data rows may run wider. The hierarchy has four roles:
headline (screen titles, the largest type and still not large), title, body (the justification
text, the product's main content), and label (column headers and the six component names, legible
in both scripts at small sizes).

**Elevation.** Flat at rest. Separation is a one pixel hairline or a tonal step. A shadow appears
only in response to state (a dropdown or dialog opens, a card lifts during a drag) and then leaves.
Side-stripe borders thicker than one pixel are banned.

**Motion.** 150 to 250 ms, only to convey state, with a reduced-motion alternative for every
transition. No page-load choreography: the user arrives in a task, not at a performance.

**Components.** Rows, not cards: three hundred candidates in cards is unusable, and nested cards
are always wrong. Standard controls, not reinvented ones. Every interactive component has seven
states: default, hover, focus, active, disabled, loading and error. Buttons are labelled verb plus
object, such as "Reject candidate", never "OK". Empty states teach the next step.

## 5. Language and direction

- Every screen exists in Arabic (right to left, the primary design) and English (left to right).
  Routes are `/ar/...` and `/en/...`. Direction flips with the locale; layout uses logical
  properties only, never physical left and right.
- Mixed-direction text is everyday content: an Arabic justification quoting an English CV line, an
  English job title inside an Arabic sentence, emails and phone numbers in Arabic paragraphs. Show
  these cases, correctly isolated.
- Numerals: show how scores, dates and counts read in each locale. Candidates' CVs may contain
  Arabic-Indic digits (٠١٢٣٤٥٦٧٨٩) and Hijri dates.
- A visible language switch on every screen.

## 6. Accessibility

WCAG 2.1 AA on every recruiter-facing screen. Usable from 360 px wide; primary use is a laptop.
Visible focus everywhere (amber focus ring). Color never carries meaning alone, including for
score components, confidence levels and review-queue states. Users are not technical and never
need to understand AI to use this.

## 7. Decisions for you to make

`DESIGN.md` leaves these open. Propose values, show them in use, and deliver them as tokens:

1. **The typeface.** Evaluate at least IBM Plex Sans Arabic and Readex Pro against the equal-weight
   test (same sentence, both scripts, side by side) and small-label legibility. Recommend one, with
   the reason. An optional mono for identifiers and file names only if clearly needed.
2. **The amber ramp** in OKLCH around the anchor, including the roughly 0.55 lightness interactive
   primary, with contrast ratios stated.
3. **The zero-chroma grey ramp** for text, borders, dividers, disabled states and the score scale.
4. **Semantic colors** for error, warning and success that stay legible on white without becoming a
   second accent, each paired with an icon or text.
5. **The type scale** (rem steps, weights, line heights) for headline, title, body and label, in
   both scripts.
6. **Spacing, radius and border tokens**, and the two permitted shadows.
7. **How a score is drawn** without color grading: numeral, bar, position, or a combination.

## 8. Surfaces to design, by release phase

For each screen, design Arabic first and then English, at 1440 px desktop and 360 px mobile. Where
relevant, include the empty, loading, error and partial states, because rule 5 lives in those
states. Use realistic content: Egyptian names written in Arabic and in English (محمد عبد الله /
Mohamed Abdallah), real-sounding Egyptian employers and universities, EGP prices, and
justifications that quote CV lines.

### Phase 0: public website (validation)

- **Landing page** with a waitlist signup. This is the brand register, not the product register:
  more expressive layout and fluid type are allowed, but the identity stays the same (white canvas,
  one typeface, amber reserved for the call to action). Explain the product through the real
  interface, one screen showing a ranked shortlist with a quoted justification, not through
  illustrations or a hero metric. Lead with the problem Nourhan recognises: 300 CVs, a manager
  waiting, strong late applicants never read. Arabic first.

### Phase 1: core screening (single user, no billing)

1. **Sign in.** Email sign-in and **"Continue with Google"**. Phase 1 has no self-signup, so a
   Google account that has not been invited sees a clear, polite "this account has no access yet"
   state rather than an empty product.
2. **Jobs list.** Every job with candidate counts and processing progress. The empty state teaches:
   create a job, then drop CVs on it.
3. **Create job.** Title, description, required and preferred skills, minimum experience,
   location, language requirement. Or paste a free-text job description and review the structured
   specification the system proposes before saving. The proposal is editable and clearly marked as
   a suggestion.
4. **Upload to a job.** Drag and drop up to 25 files (PDF, DOCX, DOC, JPG, PNG). Per-file status
   that stays honest: queued, processing, parsed, needs review, failed (with the reason, such as
   password-protected, corrupt or empty file), unsupported language. Uploading returns immediately;
   processing continues in the background and the user can leave.
5. **Job detail: the ranked candidate list.** The heart of the product, modelled on Linear. At
   least fifteen rows visible without scrolling on a laptop. Each row: rank, name, the first line
   of the justification, the score as supporting information, a confidence signal, and status.
   Sorting, filtering and full-text search in both languages. Candidates still processing, needing
   review or failed appear in the list or beside it, never hidden. The selected row uses amber.
6. **Candidate detail.** The Reading Room itself: the original document in an embedded viewer on
   one side, the extracted profile and the reasoning on the other. It shows:
   - the justification, with every claim linked to the quoted CV text it relies on, which
     highlights in the document when chosen;
   - a three-to-five line summary;
   - the six-component breakdown with each weight, modelled on Stripe (sample weights: skills 30,
     experience 25, education 15, tenure 10, language 10, location 10, totalling 100);
   - the profile: name, contact, location, experience, dated employment history, education,
     skills, languages, certifications;
   - "Shortlist candidate" and "Reject candidate" as deliberate actions. Rejection sits where no
     hover or mistimed click reaches it and asks for confirmation, and the record shows who decided
     and when.

   Note that the name, gender, age, photo, nationality and marital status were excluded from
   scoring, and say so on screen in plain words.
7. **Correct extracted fields.** Edit any field. The correction is kept and visibly marked as a
   human correction, distinct from the machine's value.
8. **Review queue.** Low-confidence and failed documents, each with its reason, the original
   viewable, and a path to fix or dismiss. Nothing leaves without a decision.
9. **Settings.** Interface language, the organisation's data retention period, and a request to
   delete a candidate's personal data, with honest wording about what deletion removes and what the
   audit trail keeps.
10. **Limit reached.** When the organisation hits its processing limit, processing stops with a
    plain explanation and nothing already in the account is hidden.

### Phase 2: channels and pipeline

1. **Intake channels setup.** The organisation's forwarding address (for example
   `jobs-acme@masirah.online`) with copy and instructions; connecting a WhatsApp Business number.
   Every candidate shows the channel it arrived by.
2. **Duplicate candidates.** When email, phone or content match, records merge; show what was
   merged and from where.
3. **Pipeline board.** Configurable stages per job, a board view with drag-to-move (the one
   permitted lift shadow), and the list view kept alongside.
4. **Bulk actions.** On a filtered selection: shortlist, tag, move stage, email. Bulk reject still
   needs a deliberate, confirmed human action and records the actor.
5. **Collaboration.** Notes with @mentions, tags, saved filters reused across jobs, and a full
   activity timeline per candidate showing every status change, email and note with actor and
   time.
6. **Screening questions and interview scorecard.** Generated from the job: questions with
   expected-answer indicators, a scorecard with weighted competencies and a rating scale, and
   candidate-specific probing questions drawn from gaps in that CV. Everything editable, and
   clearly marked as generated.
7. **Flags.** Gaps, contradictions and unverifiable claims (overlapping employment dates, a degree
   with no institution) shown as neutral observations, not accusations.
8. **Tune the ranking.** Adjust the six component weights per job and rescore without re-parsing;
   rescore a candidate against another job. Show the before and after order.
9. **Email.** Bilingual templates with merge variables; bulk sending with rate-limit and
   deliverability safeguards shown before sending; automatic acknowledgement on receipt; automatic
   rejection notice after a configurable delay.
10. **Team and roles.** Owner, Recruiter/Admin, Hiring Manager (read and comment on assigned jobs
    only) and Interviewer (their scorecards only). Design the invite flow, and what the Hiring
    Manager and Interviewer each see, since their views are deliberately narrower.
11. **Data.** Export to CSV and Excel, and account-level deletion of candidate data.
12. **Notifications.** An in-app notification centre, plus browser push notifications delivered
    through Firebase, with a permission prompt that explains the value before the browser asks.
    Events: a batch finished processing, documents need review, a team @mention, quota at 80 and
    100 percent, and a free period ending. Per-user notification preferences.

### Phase 3: commercial launch

1. **Website: pricing and signup.** Plans in EGP, excluding VAT:
   - Free: 0, 1 user, 30 CVs a month.
   - Starter: 900 a month or 9,000 a year, 3 users, 300 CVs.
   - Growth: 2,500 a month or 25,000 a year, 8 users, 1,500 CVs.
   - Agency: 4,500 a month or 45,000 a year, 15 users, 4,000 CVs.
   - Enterprise: custom.

   A monthly and annual toggle presents annual as "two months free". Signup by email or Google
   leads straight into a working product with no approval step.
2. **First run.** From signup to a first ranked list in minutes: create a job, drop CVs, see the
   ranking. Teach through the interface itself, with no tour carousel.
3. **Usage meter.** CVs processed against the monthly quota, always visible where it matters, with
   warnings at 80 and 100 percent. At the quota, processing stops cleanly with an explanation and
   an upgrade path. Nothing is lost or hidden.
4. **Checkout and billing.** Plan choice; payment through Paymob by card, Fawry, Instapay or
   mobile wallet; promotional code entry; self-serve upgrade, downgrade and cancel, with proration
   explained in plain numbers; remaining time in a granted free period, with the 14-day and 3-day
   warnings; what happens when a free period ends (converts to paid if a card is stored, otherwise
   drops to Free with all data intact).
5. **Mailbox and calendar.** Connect Gmail or Outlook, with an honest state when a connection
   fails; intake continues by forwarding address regardless. Interview scheduling with calendar
   integration and a candidate self-booking link. WhatsApp messaging with approved templates in
   the thread the candidate applied on.
6. **Agency mode.** One login, several fully isolated client workspaces, with an unmistakable
   workspace switcher, since acting in the wrong client's workspace is the costly error here.
   Export in a client's format.
7. **Audit log.** Data access and export history, retained for 12 months, filterable.
8. **Internal back-office console (Masirah staff only).** A separate, plainly internal surface
   using the same system at higher density:
   - an organisations list with plan, usage, status and flags;
   - an organisation detail page with its plan, quota, usage history, grants, codes redeemed and
     billing state;
   - grant free months, with a required reason, recording who granted what, to whom, for how long
     and why;
   - create and manage promotional codes (percentage discount or free months, expiry, redemption
     cap, optional plan restriction, redemptions so far);
   - adjust an organisation's quota;
   - an audit trail of every staff action.

   Make it impossible to confuse with the customer product: a distinct frame or marker, not a
   different visual language.

### Phase 4: expansion

1. **Buy more CVs.** Add-on volume blocks without changing plan.
2. **Pay in dollars.** A USD subscription through Stripe for Gulf and international customers, with
   currency shown unambiguously everywhere.
3. **Referrals.** Refer a company and both sides get one free month, credited on the referred
   account's first payment. Show status of each referral.
4. **Early-adopter price lock.** A quiet marker on billing showing the locked price and until when.
5. **Interview layer, deepened.** Scorecards completed in-app by several interviewers, aggregated
   into one comparable view, and an interview summary with a hire or no-hire recommendation that is
   plainly labelled advisory.
6. **Talent pool.** Rejected and unplaced candidates stay searchable and are matched against new
   jobs.
7. **Compare candidates.** Side by side, up to four.

### Candidate-facing pages (Phases 2 and 3)

- **Application status page.** Opened from a tokenised link with no account. It shows that one
  application's status and nothing else, plus clear states for an expired or invalid link. Written
  for Sara on a phone, in her language, with the honesty the product owes her.
- **Self-booking page** for an interview slot.
- **Acknowledgement message** by email and WhatsApp, confirming receipt.

## 9. What not to do

- No gradient text, no decorative glassmorphism, no big-number hero metric, no identical card
  grids, no uppercase tracked eyebrow above every section.
- No red-to-green scores, and no score shown as a verdict.
- No illustrations, emoji, confetti or celebratory motion.
- No warm-tinted backgrounds, and no amber used for decoration.
- No reject control within reach of a hover or a stray click.
- No mirrored-afterwards Arabic: design RTL first, then check English.
- No reinvented scrollbars, modals or form controls.
- No copy that praises the user or the product ("Great job!", "Our powerful AI").

## 10. Deliverables, in this order

1. **Foundations:** the decisions in section 7, as a token sheet (OKLCH colors, type scale,
   spacing, radii, borders, shadows, motion) with contrast ratios, shown in Arabic and English.
2. **Components** with all seven states: buttons, inputs, selects, the candidate row, the score
   breakdown, the evidence citation, status and confidence indicators, the file upload item, tabs,
   the table and board, dialogs (including reject confirmation), toasts, the notification item,
   the usage meter, the language switch and the workspace switcher.
3. **Phase 1 screens in full fidelity**, Arabic and English, desktop and mobile, with their empty,
   loading, error and partial states. These are built first.
4. **The Phase 0 landing page** and the **Phase 3 pricing page** (brand register).
5. **Phase 2 to 4 key screens**, and the internal back-office console.
6. A short note for each screen on the decisions you made and why, so they can be written back into
   the design system.
