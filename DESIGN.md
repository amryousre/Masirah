---
name: Masirah
description: CV screening for Egyptian SMEs, where the reasoning is the product and the score is a footnote.
---

<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->

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
- Dense but calm. Fifteen candidates visible without scrolling, none of them shouting.
- Right-to-left is a primary reading direction, designed first, not mirrored afterwards.

## 2. Colors: The Isolated Amber Palette

Restrained, and severely so. One warm accent against a pure white canvas and a neutral grey ramp,
where the accent's rarity is what gives it meaning.

### Primary

- **Amber** (anchor `oklch(0.774 0.174 65.1)`, hue 65, exact ramp values `[to be resolved during
  implementation]`): the only chromatic color in the system. Reserved for primary actions, the
  currently selected row, and focus rings. It appears on well under ten percent of any screen.

  The hue is a deliberate rejection of three reflexes: blue belongs to Workable, LinkedIn and the
  local job boards; green belongs to Greenhouse; purple is the generic AI product tell. Amber also
  carries the name, since مسيرة means journey.

  **The anchor is not the button.** At lightness 0.774 this color cannot carry white text at WCAG
  AA. The shipping interactive primary needs the same hue at roughly 0.55 lightness. The anchor
  defines identity; the ramp defines usability.

### Neutral

- **Canvas** (`oklch(1 0 0)`, exactly white): the page. Not 0.99, not a trace of chroma.
- **Greys** (chroma 0, ramp `[to be resolved during implementation]`): panels, borders, dividers,
  secondary text, disabled states, and the score ramp. Zero chroma throughout, so that amber is the
  only thing on screen that is a color.

Semantic states for error, warning and success are `[to be resolved during implementation]`. They
must be legible against the white canvas without becoming a second accent.

### Named Rules

**The White Canvas Rule.** The page background is exactly `oklch(1 0 0)` and never anything else. No
warmth, no tint, no "barely perceptible" chroma. The audit test: if a panel background is not
identical to the page background, it has drifted, and the warm near-white it drifted toward is the
single most saturated cliché in current interface design.

**The Isolation Rule.** Amber marks action, selection and focus. Nothing else. Not headings, not
icons, not borders, not scores, not empty states. Its rarity is the entire point, and every
decorative use spends it.

**The Greyscale Rule.** No information may be carried by hue alone. The audit test: screenshot any
screen, convert to greyscale, and confirm nothing has been lost. This applies hardest to the score,
which is the product's core output and must therefore never be graded by color.

## 3. Typography

**Display Font:** none. This system has no display face.
**Body Font:** `[one family carrying Arabic and Latin, to be chosen at implementation]`. Candidates
worth evaluating: IBM Plex Sans Arabic, Readex Pro.
**Label/Mono Font:** `[optional mono for identifiers and file names, to be decided]`.

**Character:** one voice for the whole interface, carrying both scripts with equal conviction. The
personality comes from weight contrast and spacing, not from a second typeface. In a product where
Arabic is the original rather than the translation, a pairing that treats the two scripts as
separate problems will always render one of them as the afterthought.

### Hierarchy

Sizes and weights are `[to be resolved during implementation]`, but the shape of the scale is
already decided.

- **Headline**: screen titles. The largest type in the system, and not large.
- **Title**: section and panel headings.
- **Body**: the justification text, which is the primary content of the product. Prose caps at 65 to
  75 characters; dense data rows may run considerably wider.
- **Label**: field labels, column headers, the six score component names. Must stay legible in both
  scripts at small sizes, which is the real constraint on the whole type choice.

### Named Rules

**The One Voice Rule.** One family, both scripts, no exceptions. A second family enters this system
only if a genuine typographic need is demonstrated, never for flavour.

**The Fixed Scale Rule.** Rem steps, never `clamp()`. Product interfaces are viewed at consistent
device pixel ratios, and a heading that shrinks inside a narrow panel looks worse, not responsive.
Fluid type belongs to the landing page, which is a different register entirely.

**The Equal Weight Rule.** Arabic and Latin must appear equally substantial at the same size and
weight. The audit test: set the same sentence in both scripts side by side. If the Arabic looks
lighter, smaller or more delicate than the Latin, the family is wrong, regardless of how good the
Latin looks alone.

**No display type in the interface.** Headings, buttons, labels and data all use the body family.
Display faces in UI labels are a product register ban.

## 4. Elevation

Flat. This system conveys depth through tonal layering and hairline borders rather than shadow.
Motion energy is Responsive, which means depth is something that appears in answer to a state change
and then leaves, not a permanent property of a surface.

### Shadow Vocabulary

Exact values are `[to be resolved during implementation]`. Two roles are anticipated and no more:
one for genuinely floating layers such as dropdowns and dialogs, and one for a transient lift on an
active drag. Anything else uses a border or a tonal step.

### Named Rules

**The Flat-By-Default Rule.** Surfaces are flat at rest. A shadow appears only as a response to
state: something opened, something lifted, something focused. A resting card with a shadow is
decoration, and decoration is not permitted here.

**The Hairline Rule.** Separation is a one pixel border or a tonal step, never a stripe. Side-stripe
borders greater than one pixel are banned outright.

## 5. Do's and Don'ts

### Do:

- **Do** keep the canvas at exactly `oklch(1 0 0)`, with warmth confined to the amber accent.
- **Do** darken the amber anchor to roughly 0.55 lightness before putting white text on it. The seed
  value fails contrast as a button fill.
- **Do** carry every score with a second channel beyond hue, so the ranking survives greyscale and
  colorblind users are not excluded from the product's core output.
- **Do** use logical CSS properties throughout. Physical left and right values are forbidden in
  layout code, because right-to-left is a primary direction here rather than a variant.
- **Do** give every interactive component all seven states: default, hover, focus, active, disabled,
  loading, error. Shipping half of them is shipping an unfinished component.
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
  Nested cards are always wrong.
- **Don't** place a reject control where a hover or a mistimed click can reach it. Rejection is a
  deliberate act that records a human actor, and that is a legal requirement rather than a
  preference.
- **Don't** animate anything that does not convey state. No orchestrated page-load sequence. The
  user arrives in a task, not at a performance.
- **Don't** invent new affordances for standard tasks. Custom scrollbars, non-standard modals and
  reinvented form controls read as strangeness without purpose, which is the product register's
  actual failure mode.
