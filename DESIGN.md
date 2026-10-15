---
name: Masirah
description: CV screening for Egyptian SMEs, where the reasoning is the product and the score is a footnote.
---

<!-- Values come from the Claude Design handoff of 25 September 2026, in Docs/design/Figma export/
     (Foundations for tokens, Components for states). web/app/globals.css is the executable copy
     (T027). Re-run /impeccable document once screens exist, to capture what the code really does. -->

# Design System: Masirah

## 1. Overview

**Creative North Star: "The Reading Room"**

A quiet, well-lit room where a document lies open and someone works through it carefully. Light
comes from the window, not from the walls. Nothing on the table is decorative. The annotations sit
beside the text they refer to, and any claim can be traced back to the line that produced it.

This is a reading interface before it is a data interface. The recruiter's real activity is reading:
a CV on one side, the system's reasoning on the other, moving between them to check whether the
machine is right. Every visual decision follows from protecting that activity. The canvas is pure
white because CVs are white pages and a tinted surface fights the document it surrounds. Greys stay
truly grey so the single warm accent means something when it appears. Motion exists only to keep the
interface honest about work happening out of sight.

The system explicitly rejects three things, carried forward from PRODUCT.md. It is not **enterprise
applicant tracking heaviness**: no grey chrome, no configuration walls, no screens that assume a
full-time administrator. It is not **consumer app playfulness**: no illustrations, no celebratory
animation, no emoji, because the product decides things about people's livelihoods. It is not
**local job board clutter**: no competing calls to action and no density without hierarchy.

**Key Characteristics:**

- Pure white canvas. Warmth lives in the brand color and nowhere else.
- One typeface carrying Arabic and Latin as equals.
- Restrained color: a single amber accent on actions, selection and focus, nothing decorative.
- Flat at rest. Depth is a response to state, never an ornament.
- Dense but calm. Seventeen candidate rows in a 900 px laptop viewport, none of them shouting.
- Right-to-left is a primary reading direction, designed first, not mirrored afterwards. Arabic is
  the default locale everywhere except Masirah's internal console.

## 2. One System, Every Screen

Every screen, from the landing page to the internal console, is built from the same tokens and the
same components. Nothing is styled twice.

- **Tokens live in one file.** `web/app/globals.css` defines every color, type step, space,
  radius, border, shadow, duration and easing below as a CSS custom property. Nothing else in the
  codebase writes a raw color, a pixel font size or a shadow.
- **Components live in one library.** `web/components/` holds each component in section 7 with
  all seven states. A screen composes them; it does not restyle them. A need the library does not
  meet is solved by extending the component, so every screen gains it.
- **The build enforces it.** Lint fails on a color literal, or a physical `left`/`right`
  property, anywhere outside the token file.
- **The internal console and the website use the same tokens**, at different densities
  (section 7), and never a separate visual language.

## 3. Colors: The Isolated Amber Palette

Restrained, and severely so. One warm accent against a pure white canvas and a neutral grey ramp,
where the accent's rarity is what gives it meaning. Contrast ratios are against white.

### Primary: amber, hue 65

| Token | OKLCH | Contrast | Use |
|---|---|---|---|
| `amber-50` | `0.975 0.016 65` | 1.08 | Hover tint on the selected row |
| `amber-100` | `0.95 0.032 65` | 1.16 | Selected row fill (`--color-selected`) |
| `amber-200` | `0.9 0.068 65` | 1.36 | Selected row, pressed |
| `amber-300` | `0.84 0.116 65` | 1.67 | Selected row edge |
| `amber-400` | `0.774 0.174 65.1` | 2.13 | Unassigned since the mark moved to yellow on black (see The mark). Never text |
| `amber-500` | `0.66 0.148 65` | 3.23 | Unassigned. Not a focus ring: 2.96:1 on `grey-50` and 2.76:1 on `grey-100` fall under 3:1 |
| `amber-600` | `0.55 0.122 65` | 5.01 | Primary button, and the focus ring on every fill: 4.60:1 on `grey-50`, 4.28:1 on `grey-100` (`--color-primary`, `--color-focus`) |
| `amber-700` | `0.47 0.106 65` | 7.02 | Primary hover, links |
| `amber-800` | `0.39 0.087 65` | 9.83 | Primary pressed (`--color-primary-pressed`), text on amber tints |
| `amber-900` | `0.3 0.068 65` | 13.84 | Strong text on tints (12.85:1 on `amber-50`) |

The hue is a deliberate rejection of three reflexes: blue belongs to Workable, LinkedIn and the
local job boards; green belongs to Greenhouse; purple is the generic AI product tell. Amber also
carries the name, since مسيرة means journey.

**The anchor is not the button.** White on the 0.774 anchor fails WCAG AA. White on `amber-600` is
5.01:1, and that is the interactive primary.

**The mark.** The M-tick from the Masirah logo: an M whose tick rises out of its valley past the
right leg, for a shortlist. Since 15 October 2026 it is yellow `#ffc72c` on black `#0b0b0b`, at the
owner's request, and it lives in `web/app/[lang]/icon.svg`. A black gap sets the tick apart from the
legs, as the full-colour logo does by shade, and a faint `#3d3d3d` edge keeps the tile visible on
dark browser chrome. The yellow belongs to the mark alone: it never appears in the interface, so it
can't be mistaken for the warning hue nearby.

### Neutral: greys at chroma 0

| Token | OKLCH | Contrast | Use |
|---|---|---|---|
| `grey-0` | `1 0 0` | 1.00 | Canvas and panels. Everywhere |
| `grey-25` | `0.985 0 0` | 1.04 | Row hover |
| `grey-50` | `0.97 0 0` | 1.09 | Code, subtle fills, disabled field |
| `grey-100` | `0.945 0 0` | 1.17 | Pressed row, skeleton |
| `grey-200` | `0.91 0 0` | 1.31 | Divider (row separators), score bar track |
| `grey-300` | `0.85 0 0` | 1.58 | Hairline: panels, tables, dialog edge |
| `grey-400` | `0.76 0 0` | 2.15 | Disabled icons and borders. Never text |
| `grey-500` | `0.64 0 0` | 3.36 | Input border and other non-text UI (at least 3:1) |
| `grey-600` | `0.54 0 0` | 5.06 | Tertiary text, placeholders |
| `grey-700` | `0.45 0 0` | 7.44 | Secondary text, metadata |
| `grey-800` | `0.34 0 0` | 11.76 | Score bars, strong icons |
| `grey-900` | `0.22 0 0` | 17.31 | Primary text, headings |

### Semantic

Low chroma, always paired with an icon and words. Tinted backgrounds are L 0.97 and appear only
inside the message itself.

| State | Foreground | Background | Foreground on white |
|---|---|---|---|
| Error, "failed to read" | `oklch(0.52 0.18 27)` | `oklch(0.97 0.014 27)` | 6.04:1 |
| Warning, "needs review" | `oklch(0.5 0.1 90)` | `oklch(0.97 0.025 90)` | 6.02:1 |
| Success, "parsed" | `oklch(0.5 0.11 150)` | `oklch(0.97 0.025 150)` | 5.70:1 |

Chroma 0.10 to 0.18 at L 0.50 keeps each hue readable as text but too dark to compete with amber.
Warning sits at hue 90, olive ochre, far enough from amber's 65 that a warning never reads as a
primary action.

### Named Rules

**The White Canvas Rule.** The page background is exactly `oklch(1 0 0)` and never anything else. No
warmth, no tint, no "barely perceptible" chroma. The audit test: if a panel background is not
identical to the page background, it has drifted, and the warm near-white it drifted toward is the
single most saturated cliché in current interface design.

**The Isolation Rule.** Amber marks the primary button, the selected row, the selected citation and
focus rings. Nothing else. Not headings, not icons, not borders, not scores, not charts, not empty
states, not the selected tab. Its budget is under ten percent of any screen, and every decorative
use spends it. The only other hues are the three semantic colors, which are dark, low in chroma,
confined to the message they belong to, and never without an icon and words.

**The Greyscale Rule.** No information may be carried by hue alone. The audit test: screenshot any
screen, convert to greyscale, and confirm nothing has been lost. This applies hardest to the score,
which is the product's core output and must therefore never be graded by color. Every status is
shape plus word, with hue a third, redundant channel.

## 4. Typography

**Display Font:** none. This system has no display face.
**Body Font:** IBM Plex Sans Arabic with IBM Plex Sans (`--font-sans`). Weights 400, 500 and 600.
**Mono Font:** IBM Plex Mono (`--font-mono`), for file names, forwarding addresses and IDs only,
where character-level reading matters.

Plex Sans Arabic won the equal-weight test against Readex Pro. Its Arabic and Latin were drawn as
one system: stroke weight, x-height and counters match, so the same sentence in both scripts reads
equally heavy. Readex Pro's Latin comes from Lexend, which is wide and rounded, looks larger and
friendlier beside its Arabic, and costs about 8 percent more width per candidate row. Plex keeps
Arabic letterforms open and dots distinct at 13 px, and its tabular figures align scores in a
column.

### Hierarchy

Arabic runs at the same size as Latin with more leading, since its ascenders, descenders and dots
need the room.

| Role | Size | Weight | Line height, Latin / Arabic | Used for |
|---|---|---|---|---|
| Headline | 1.5rem | 600 | 1.3 / 1.5 | Screen titles. The largest type in the product, and not large |
| Title | 1.125rem | 600 | 1.4 / 1.6 | Panels, dialogs, sections |
| Body | 1rem | 400 | 1.6 / 1.75 | The justification, which is the product's main content |
| Body small | 0.875rem | 400 | 1.55 / 1.7 | Rows, controls, metadata |
| Label | 0.8125rem | 500 | 1.4 / 1.5 | Column headers, the six component names, form labels |
| Caption | 0.75rem | 400 | 1.4 / 1.5 | Timestamps, helper text |

Prose caps at 68 characters; data rows may run full width.

**Numerals.** The interface uses Western digits in both locales, the common Egyptian product
convention: `78`, `1,500 CVs`, `900 EGP`. Numerals are tabular wherever a number sits in a column.
Quoted CV text keeps Arabic-Indic digits and Hijri dates exactly as written, with the normalised
value beside them: «تخرّج ١٤٤٢هـ» (≈ 2021).

Two rules keep numbers right in Arabic, and both are enforced in code:

- A numeric expression such as `26 / 30`, `78 / 100` or `240 KB` is set left to right
  (`dir="ltr"`). In a right-to-left line the slash or the Latin unit would otherwise let its parts
  swap places, so `78 / 100` would read `100 / 78`.
- A count inside a translated plural uses its named argument (`{count}`), never ICU's `#`, which
  formats with the locale's digits and would print Arabic-Indic digits in Arabic. A test fails on
  any `#` in a plural.

Quotation marks follow the quote's own language, “like this” for Latin and «هكذا» for Arabic,
whatever the language of the page around it.

### Named Rules

**The One Voice Rule.** One family, both scripts, no exceptions. Plex Mono is the only second
family, and only for identifiers.

**The Fixed Scale Rule.** Rem steps, never `clamp()`, inside the product. Fluid type belongs to the
website, which is a different register (section 7).

**The Equal Weight Rule.** Arabic and Latin must appear equally substantial at the same size and
weight. The audit test: set the same sentence in both scripts side by side. If the Arabic looks
lighter, smaller or more delicate than the Latin, something is wrong.

**No display type in the interface.** Headings, buttons, labels and data all use the body family.

## 5. Elevation

Flat. Depth is conveyed through hairline borders and tonal steps rather than shadow, and appears in
answer to a state change, then leaves.

### Shadow Vocabulary

Two, and no more:

- **Overlay** (`--shadow-overlay`): `0 0 0 1px grey-300, 0 8px 24px -4px oklch(0.22 0 0 / 0.14)`.
  Menus, dialogs, toasts.
- **Lift** (`--shadow-lift`): `0 0 0 1px grey-300, 0 2px 6px oklch(0.22 0 0 / 0.10)`. A board card
  while it is dragged, and nothing else.

### Named Rules

**The Flat-By-Default Rule.** Surfaces are flat at rest. A shadow appears only as a response to
state: something opened, something lifted. A resting card with a shadow is decoration, and
decoration is not permitted here.

**The Hairline Rule.** Separation is a one pixel border or a tonal step, never a stripe. Side-stripe
borders greater than one pixel are banned outright.

## 6. Space, Edges and Motion

- **Spacing**, 4 px base: `space-0_5` 2, `space-1` 4, `space-2` 8, `space-3` 12, `space-4` 16,
  `space-5` 20, `space-6` 24, `space-8` 32, `space-10` 40, `space-12` 48, `space-16` 64.
- **Rows**: 36 px, or 32 px compact (the internal console).
- **Radius**, small and firm: `xs` 2 px for tags, `sm` 4 px for rows, `md` 6 px for controls, `lg`
  8 px for dialogs.
- **Borders**, 1 px only: divider `grey-200` between rows, hairline `grey-300` around panels and
  tables, control `grey-500` around inputs.
- **Motion**, for state only: fast 150 ms for hover, press and focus; base 200 ms for menus, row
  selection and toasts; slow 250 ms for dialogs, panels and the citation highlight. Easing
  `cubic-bezier(0.2, 0, 0, 1)`. With reduced motion: opacity only, no movement.

## 7. Components

Every interactive component has seven states: default, hover, focus, active, disabled, loading and
error. Specimens and every state live in `Docs/design/Figma export/Masirah Components.html`.

- **Buttons.** 36 px high, 6 px radius, labelled verb plus object. One primary per view. Loading
  keeps the width and swaps the label for a progress verb ("جارٍ الحفظ…"). The destructive variant
  is outlined red at rest and never filled there; a trailing ellipsis ("رفض المرشح…") means a
  confirmation follows.
- **Inputs and selects.** Native elements, 36 px, label above, helper below, border `grey-500`. An
  error changes the border, adds an icon and says what to do, replacing the helper so the field
  height stays the same. A value the system proposed has a dashed border and a "Suggested" tag
  until it is saved.
- **Candidate row.** The first line of the justification takes the widest column. The score comes
  after it at 13 px, never bold or large. Selection is the only amber in the list. Processing,
  needs-review and failed documents sit in a labelled block below the ranking, never hidden.
  Rejected rows dim but keep their evidence and name who decided.
- **Evidence citation.** Each claim is underlined and numbered. Choosing it selects its quote and
  highlights the source line in the document. Quotes keep the CV's own language and direction,
  isolated inside the sentence. A claim about something missing is marked as an absence, with a
  dashed line and what was searched for, never a made-up quote.
- **Score.** A numeral and a neutral bar (`grey-800` on `grey-200`), never a color grade. The
  breakdown shows points earned out of each component's weight on equal-length tracks ("26 / 30"),
  sits below the reasoning, never above it, and says in words which attributes were not used.
  Bars grow from the inline start, so in Arabic they fill right to left.
- **Status and confidence.** Shape plus word. Document states have distinct glyphs: queued (dashed
  ring), processing (spinner), parsed (check), needs review (alert), failed (cross), unsupported
  language (globe). Confidence is a three-step meter with a word; low confidence adds a dashed
  outline in the list. A decision always names the person and the time.
- **File upload.** One row per file, the file name in mono, the reason in plain words, and one
  action that fixes it. An unsupported language is kept and listed, never dropped. At the
  processing limit the drop zone is disabled and existing work stays in view.
- **Tabs.** The selected tab has a heavier weight and a 2 px ink underline, keeping amber free for
  actions.
- **Table and bulk bar.** The bulk bar keeps "Reject…" apart at the far end, behind a divider.
- **Board.** Board cards are the only cards in the product, and the only element allowed the lift
  shadow. Dropping on Rejected is refused with an explanation, because rejection is never a drag.
- **Reject dialog.** Focus starts on "Keep candidate". The reject button stays disabled until a
  reason is chosen, and the dialog states who will be recorded. The only filled red in the product
  lives here. Bulk reject also requires typing the number of candidates.
- **Toasts.** Report a fact and offer one action. The rejection toast offers Undo for 10 seconds.
- **Usage meter.** Marks 80 percent with a tick and changes its words and icon. At 100 percent it
  explains that processing is paused and how many files are waiting. The bar stays grey, then ink;
  never red.
- **Language switch.** Names the other language in its own script: "English" in Arabic, "العربية"
  in English. Present on every screen.
- **Workspace switcher.** In agency mode a full-width ink band names the client above everything
  else, so the active workspace reads at a glance and in greyscale.
- **Internal console frame.** A hatched ink band labelled INTERNAL and a 2 px dashed outer frame,
  the same tokens at 32 px rows. Every grant or quota change requires a written reason.
- **Website register.** The landing and pricing pages allow fluid type and wider spacing, with the
  same white page, typeface and single amber call to action. Plans are columns divided by
  hairlines, not cards.

## 8. Do's and Don'ts

### Do:

- **Do** keep the canvas at exactly `oklch(1 0 0)`, with warmth confined to the amber accent.
- **Do** use `amber-600` for anything carrying white text. The anchor is for the logo.
- **Do** take every value from a token and every control from `web/components/`.
- **Do** carry every score with a second channel beyond hue, so the ranking survives greyscale and
  colorblind users are not excluded from the product's core output.
- **Do** use logical CSS properties throughout. Physical left and right values are forbidden in
  layout code, because right-to-left is a primary direction here rather than a variant.
- **Do** give every interactive component all seven states. Shipping half of them is shipping an
  unfinished component.
- **Do** keep transitions between 150 and 250 milliseconds, and give every one a reduced-motion
  alternative.
- **Do** write empty states that teach the interface. "No jobs yet" is a wasted screen.
- **Do** label buttons as verb plus object. "Reject candidate", never "OK".

### Don't:

- **Don't** build **enterprise applicant tracking heaviness**. No grey chrome, no configuration
  walls, no screen that assumes a full-time administrator exists. Named anti-reference.
- **Don't** introduce **consumer app playfulness**. No illustrations, no rounded friendliness, no
  celebratory animation, no emoji. Named anti-reference, and the fastest way to signal that the
  product does not take hiring decisions seriously.
- **Don't** reproduce **local job board clutter**. No competing calls to action, no density without
  hierarchy. Named anti-reference.
- **Don't** tint the background warm. The cream, sand, beige and parchment family is the saturated
  default of current AI design, and token names like `--paper` or `--linen` are tells in themselves.
- **Don't** grade scores by color. Red-to-green ranking is the obvious move and it is forbidden here.
- **Don't** use gradient text, decorative glassmorphism, the big-number hero metric, or identical
  card grids. Cross-register bans.
- **Don't** reach for cards. Three hundred candidates in cards is unusable; rows are the answer.
  Board cards are the single exception. Nested cards are always wrong.
- **Don't** place a reject control where a hover or a mistimed click can reach it. Rejection is a
  deliberate act that records a human actor, and that is a product requirement (FR-023 in the
  Phase 1 spec) rather than a preference.
- **Don't** animate anything that does not convey state. No orchestrated page-load sequence. The
  user arrives in a task, not at a performance.
- **Don't** invent new affordances for standard tasks. Custom scrollbars, non-standard modals and
  reinvented form controls read as strangeness without purpose, which is the product register's
  actual failure mode.
- **Don't** style a component inside a screen. Fix or extend the component instead.
