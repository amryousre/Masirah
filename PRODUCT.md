# Product

## Register

product

## Users

**Nourhan, HR generalist at a 60-person company.** The primary user. She handles all hiring
alongside payroll and admin, posts on Wuzzuf, and receives around 300 CVs per role. She has no
budget authority above a few thousand Egyptian pounds a month and no permission to request new
software. She works in Arabic. Her measure of success is filling the role without her manager
complaining. Today she opens CVs one at a time and gives up around the fortieth, which means strong
late applicants are systematically lost. She needs speed, and something she can start using today
without asking anyone.

**Tarek, engineering manager.** The user who decides whether the product is believed. He receives
shortlists he does not trust and re-reads every CV himself, which destroys the value of the
shortlist entirely. He wants evidence, not a number. He needs a defensible reason for each ranking
position, and screening questions he did not have to write.

**Mahmoud, independent recruiter.** Secondary. Runs eight to fifteen roles across several client
companies at once. Highly sensitive to both price and volume. Needs client separation and
throughput.

**Sara, candidate.** Applies by WhatsApp from her phone and never hears back. She is not a customer,
but her experience is a deliberate differentiator rather than an afterthought.

The context of use is a small office, on a laptop, under time pressure, in Arabic, with a manager
waiting.

## Product Purpose

Masirah turns a pile of CVs into a ranked shortlist that a hiring manager will actually trust,
for Egyptian small and medium companies priced out of every existing tool.

The real competitor is not another applicant tracking system. It is an inbox and a spreadsheet,
which are free, familiar and require no training. Every design decision is measured against that,
not against Workable.

The commercial thesis is access rather than technology. Competitors sell annual contracts from
40,000 EGP through a sales call. Masirah is a genuine free tier and monthly billing in Egyptian
pounds with no salesperson involved. The product must therefore look and feel like something a
person starts using on a Tuesday afternoon without a procurement conversation.

Success looks like: time from CV received to shortlist decision falling below 24 hours, a recruiter
agreeing with the top ten ranking at least 80 percent of the time, and 40 percent of paid
conversions completing with zero human contact.

## Brand Personality

**Precise, calm, credible.**

A serious instrument that does not shout. Restraint is the point: it reads as competence to a
manager whose default assumption is that the machine got it wrong. The product is asking for trust
in a judgement about people's livelihoods, and loud design undermines that faster than anything
else.

Voice is specific rather than aphoristic. It names what happened and why. It never congratulates
the user, never celebrates, and never describes its own output as intelligent. Where the product is
uncertain it says so plainly, because visible uncertainty is what makes the confident cases
believable.

References, chosen for specific reasons rather than general mood:

- **Citation-style AI tools such as Perplexity and Elicit.** The evidence sits immediately beside
  the claim and every assertion traces back to its source. This is structurally identical to the
  score, justification and quoted CV evidence problem, making it the most directly transferable
  reference available.
- **Linear.** Dense information that still feels calm and fast, with no decorative chrome and color
  used only where it carries meaning. The model for the candidate list.
- **Stripe Dashboard.** Consequential data made legible, where clarity itself produces trust. The
  model for the six-component score breakdown.

## Anti-references

- **Enterprise applicant tracking heaviness.** Workable, Greenhouse, SAP SuccessFactors. Grey
  chrome, endless configuration, screens that assume a full-time administrator exists. The product
  competes by being usable the day it is opened.
- **Consumer app playfulness.** Illustrations, rounded friendliness, celebratory animation, emoji.
  Wrong register for a tool making decisions about people's livelihoods. A misjudged moment of
  delight reads as not taking the work seriously.
- **Local job board clutter.** Wuzzuf and its peers. Advertising, competing calls to action, and
  density with no hierarchy. Users see these daily, and resembling them assigns the product to the
  same mental category.

Cross-register bans apply regardless: no gradient text, no decorative glassmorphism, no hero-metric
template, no uppercase tracked eyebrow above every section, no identical card grids.

## Design Principles

**1. Evidence before verdict.** The written justification and the CV text it cites are the primary
content of any scored candidate. The number is supporting information, never the headline. A screen
that leads with a score and buries the reasoning has failed, because the user who matters most does
not believe numbers.

**2. The machine advises, the human decides.** No screen may present a score as a decision, and
rejecting a candidate always requires a deliberate human action. This is a hard product requirement
carrying legal weight, not a stylistic preference, and it constrains layout, copy and interaction
equally.

**3. Arabic is the original, not the translation.** Right-to-left is a primary reading direction
designed from the start, not a mirrored afterthought. Every competitor either ignores Arabic or
bolts it on, and being genuinely Arabic-first is a position none of them currently occupy.

**4. Density without noise.** Three hundred candidates must feel finishable rather than
overwhelming. The answer is hierarchy and rhythm, not whitespace and pagination. Fatigue is the
failure mode the product exists to eliminate, so a design that tires the user has lost regardless
of how it looks.

**5. Nothing is ever silently lost.** Every CV either produces a profile or appears somewhere the
user can see it. Failures are surfaced honestly, including the product's own. This principle is
what makes the other four credible: a system that quietly drops documents cannot be trusted about
anything else.

## Accessibility & Inclusion

- **WCAG 2.1 Level AA** for every recruiter-facing screen. This is a stated requirement in the
  business requirements document, not an aspiration.
- **Full right-to-left support**, including mixed-direction text, forms, tables and PDF export.
  Direction-sensitive styling uses logical properties exclusively.
- **Usable from 360 pixels of width.** Latest two versions of Chrome, Edge, Safari and Firefox.
- **Color never carries meaning alone.** Score components, confidence levels and review-queue states
  each need a second channel, since the product's core output is a set of graded judgements and
  grading by hue alone excludes colorblind users.
- **Reduced motion is honoured** with a crossfade or instant alternative for every animation.
- Users are not necessarily technical. The primary persona did not ask for an artificial
  intelligence tool and should never need to understand one to use this.
