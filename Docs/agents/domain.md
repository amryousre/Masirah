# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This is a single-context repo.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root. It is the domain glossary (for example, a *CV* is the document and a *parsed_profile* is its extraction).
- **`Docs/adr/`** — read the ADRs that touch the area you're about to work in. Note the capital `D`: the path is case-sensitive in git and CI.
- For feature work, also read `specs/001-phase1-core-screening/` (`spec.md`, `plan.md`, `research.md`) and `.specify/memory/constitution.md`, which is binding.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates them lazily when terms or decisions actually get resolved. New ADRs go in `Docs/adr/`, numbered after the last one.

## File structure

```
/
├── CONTEXT.md
├── Docs/adr/
│   ├── 0001-self-serve-sme-positioning.md
│   └── ...
├── specs/001-phase1-core-screening/
├── web/
├── pipeline/
└── supabase/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0004 (application architecture) — but worth reopening because…_
