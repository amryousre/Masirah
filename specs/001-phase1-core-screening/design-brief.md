# Design Brief: Core Screening Flow

**Date**: 2026-09-11
**Produced by**: `/impeccable shape`
**Status**: Awaiting confirmation
**Covers**: User Story 1 of [the Phase 1 spec](./spec.md), four screens

## 1. Feature Summary

The core screening flow is how a recruiter turns a folder of CVs into a shortlist she can defend.
Four screens: create a job, bring in a batch of CVs, read a ranked candidate list, and examine one
candidate in depth. It serves Nourhan, a solo HR generalist working in Arabic under time pressure,
and Tarek, an engineering manager who currently re-reads every CV because he does not believe
shortlists.

It must do one thing competitors do not: make a machine-produced ranking believable to the person
who distrusts it most.

## 2. Primary User Action

**Read the reason a candidate is ranked where they are, and verify it against their actual CV in one
motion.**

Not "see a score". The score is the least persuasive thing on the screen. The action that matters is
the one where a skeptical hiring manager reads a claim, clicks the evidence behind it, and sees that
sentence highlighted in the original document. That single interaction is the product.

## 3. Design Direction

**Color strategy: Restrained.** Asserted from PRODUCT.md rather than asked. It is the product
register's floor and the only strategy coherent with "precise, calm, credible". Accent carries
primary actions, current selection and focus. Nothing decorative.

**Scene sentence.** Nourhan works on a laptop in a shared Cairo office at two in the afternoon,
under overhead light and daylight from a window, with a white CV document open beside the ranking
and her manager expecting a shortlist by end of day.

That forces **light**, and the document is the stronger argument. Candidate detail places the
original CV beside the extracted data, and CVs are white pages. A dark interface wrapped around a
white document is a poor pairing for the sustained reading this product exists to support.

**Palette direction.** Pure white canvas, exactly `oklch(1 0 0)`, with no hidden warmth. The brand
hue is amber at 65 degrees, from the seed `oklch(0.774 0.174 65.1)`. Warmth lives in the brand color
and the typography, never in the surface, which is the distinction between Stripe and every AI
product that tints its background cream.

Amber is a deliberate choice against three reflexes. Blue is the category default here, worn by
Workable, LinkedIn and the local job boards. Green belongs to Greenhouse. Purple is the generic AI
product tell. Amber also carries the name, since مسيرة means journey, and it has regional resonance
without costume.

One caution for implementation: the seed at lightness 0.774 will not carry white text at WCAG AA.
The shipping primary needs the same hue at roughly 0.55 lightness. The seed is the identity anchor,
not the button fill.

**Anchor references**, from PRODUCT.md, each for a specific reason:

- **Perplexity and Elicit** for the citation model. Evidence sits beside the claim and traces back to
  its source. Structurally the same problem as score, justification and quoted CV evidence.
- **Linear** for the candidate list. Dense information that stays calm, no decorative chrome.
- **Stripe Dashboard** for the score breakdown. Consequential data made legible, where clarity is
  what produces trust.

## 4. Scope

| | |
|---|---|
| Fidelity | Production-ready |
| Breadth | Four screens, one flow |
| Interactivity | Shipped-quality components with real states |
| Time intent | Polish until it ships |

This flow sets the vocabulary every later screen inherits, which is why it is worth finishing rather
than sketching.

## 5. Layout Strategy

### Create a job

**Paste first, structure second.** The primary input is a single large field for pasting a job
description, because writing a structured specification is work nobody wants to do. The system
derives title, skills, experience, location and language requirement, then presents them as editable
fields for confirmation.

The manual field-by-field path exists but is secondary. A ten-field form as the front door is the
enterprise pattern the product is positioned against.

### Bring in CVs

**Upload is not a destination.** Dropping files should not navigate anywhere. The drop target lives
on the job screen, and the candidate list fills in as files are processed. The user watches work
happen rather than waiting on a progress screen and then being delivered somewhere else.

Per-file state is visible and honest: queued, reading, done, needs review, failed. Twenty-five files
per batch is the ceiling, which is small enough to show every one.

### Ranked candidate list

**Rows, not cards.** Three hundred cards is unusable, and cards are the lazy answer besides. Each row
carries name, score, and a fragment of the reasoning. That fragment is what separates this from a
spreadsheet with a number column.

Two ideas do the real work here:

**Show where quality falls off.** Ranked lists have a cliff, and Nourhan does not know where it is,
so she either stops too early or scrolls all three hundred. A visible break at the point where scores
drop materially tells her she can stop at fifteen. This is the single highest-value idea for the
phase's stated goal of eliminating fatigue.

**The score is never a colored number.** Color must not be the only channel carrying meaning, and
hue-graded scores exclude colorblind users on the product's core output. Use a neutral ramp plus
length or position, so the comparison survives in greyscale.

### Candidate detail

**Two panes: document and reasoning.** The original CV on one side, the extracted profile, score
breakdown and written justification on the other. In Arabic the document sits on the left and the
reasoning on the right, since the reading eye starts at the right edge and the reasoning is primary.

**The justification leads. The score follows.** Principle one from PRODUCT.md, expressed as layout.
The written explanation and its cited evidence occupy the primary column. The six-component
breakdown is a supporting rail, not a header.

## 6. Key States

### Create a job
- Empty, no jobs yet. Teach the paste-a-description path rather than saying "no jobs".
- Pasting, structure being derived.
- Derived structure awaiting confirmation, every field editable.
- Saved.

### Upload and processing
- Idle drop target.
- Files queued, per-file progress.
- Partial completion: some scored, some still processing, list already useful.
- Per-file failure: unreadable, corrupt, encrypted, unsupported language. Visible, never silent.

### Candidate list
- Empty: job exists, no candidates yet.
- Processing: some candidates scored, others pending, sorting honest about what is incomplete.
- Scored and ranked, with the drop-off marker.
- Filtered to zero results, which is different from empty and must say so.
- Large: fifty thousand candidates, per the performance requirement.

### Candidate detail
- Extracted and scored, the normal case.
- Low confidence, flagged for review, extraction shown but not trusted.
- Unsupported language, visibly distinct from a bad scan since the two need different actions.
- Extraction failed entirely, original still viewable, manual entry possible.
- Fields corrected by the user, correction visible as such rather than silently overwriting.

## 7. Interaction Model

**Evidence linking is the centrepiece.** Every claim in the justification that cites the CV is
interactive. Activating it scrolls the document pane to that passage and highlights it. This is the
Perplexity model applied to hiring, and it is what converts a skeptical manager, because he stops
taking the system's word for anything and starts checking it in one click.

It must work by keyboard and be announced to screen readers, not be a hover affordance.

**Rejection is deliberate, never adjacent.** No reject control appears in a row hover position where
it can be hit by accident. Rejecting requires an explicit action that records the acting user. This
is a legal requirement carrying discrimination-claim exposure, not a preference.

**Corrections persist.** Editing an extracted field saves the correction and survives reprocessing.
The interface must show that a value was corrected by a person rather than extracted.

**Motion conveys state only.** Rows appearing as they are scored, progress advancing, the document
scrolling to a citation. 150 to 250 milliseconds. No orchestrated page-load sequence. Every animation
needs a reduced-motion alternative.

**Keyboard throughout.** Moving between candidates, opening detail, following a citation. Nourhan
processes three hundred of these, and reaching for a mouse each time is the fatigue the product
exists to remove.

## 8. Content Requirements

All copy in Arabic first, held in translation files, with English parity. No hard-coded display
strings anywhere.

**Voice**, from PRODUCT.md: specific rather than aphoristic. Name what happened and why. Never
congratulate the user, never celebrate a completed batch, never describe the output as intelligent.

**Copy that needs writing:**

- Empty states that teach the interface. "No jobs yet" is a wasted screen; it should show how a
  pasted description becomes a job.
- The five per-file states, worded so a non-technical user knows what to do about each.
- The difference between a badly scanned document and an unsupported language, in plain words.
- Score component labels: skills match, experience relevance, education, tenure stability, language,
  location. Six labels that must read clearly in both languages at small sizes.
- A standing line making clear the score is advisory and the decision is the user's. Present without
  nagging.
- Rejection confirmation, which must state the consequence rather than asking "are you sure".
- Button labels as verb plus object throughout.

**Realistic ranges**: 0 to 300 candidates per job, up to 50,000 per account, 25 files per batch,
scores 0 to 100 across six components, justifications of roughly two to four sentences, summaries of
three to five lines.

**No imagery.** No illustrations, no stock photography, no decorative iconography. The only visual
content is the candidate's own document. Consumer app playfulness is a recorded anti-reference, and
illustration is how it arrives.

## 9. Recommended References

During implementation, these impeccable references earn their weight:

- `product.md`, already loaded. The register governing everything here.
- `layout.md` for the two-pane document-and-reasoning composition and the dense list.
- `interaction-design.md` for the job creation form and field correction.
- `harden.md` for the failure states, which are unusually load-bearing in this product.
- `clarify.md` for the copy, especially the five per-file states and the advisory framing.
- `adapt.md` for the 360 pixel requirement, where the two-pane layout must become something else.

## 10. Open Questions

Defaults asserted rather than asked, per the shape discipline. Override any of these.

**The two-pane layout below 700 pixels.** Asserting: the panes become tabs, reasoning first, with the
citation link switching tabs and highlighting. A stacked layout would put the document below the
fold and break the verification motion that is the entire point.

**Score display.** Asserting: a compact six-segment bar showing relative contribution, with the total
as a number beside it in text rather than as a large display figure. Satisfies the second-channel
accessibility requirement and keeps the number subordinate to the reasoning.

**Where the drop-off marker sits.** Asserting: computed from the score distribution rather than a
fixed rank, so it lands where the data actually breaks rather than always at ten.

**Density.** Asserting: single-line rows with the reasoning fragment truncated, expandable in place.
Fitting roughly fifteen candidates on a laptop screen without scrolling.

**Typography.** Asserting: one family across the whole interface, carrying Arabic and Latin with
genuine weight range. Product register says a single well-tuned sans is usually right, and a product
that is Arabic-first cannot pair two families without the Arabic looking like an afterthought.
