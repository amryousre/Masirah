# Masirah specifications

All four phases, specified up front to give a clear picture of the whole product before building
begins. Written 11 September 2026.

Business requirements live in [the BRD](../Docs/BRD_Masirah_EN.md). Decisions that are hard to
reverse live in [Docs/adr/](../Docs/adr/). These specifications turn the BRD's numbered requirements
into user stories, acceptance scenarios and measurable outcomes.

## The four phases

| Phase | Specification | Requirements | Exit criterion | Status |
|---|---|---|---|---|
| 1 | [Core screening](./001-phase1-core-screening/spec.md) | 21 | A pilot company processes 200 CVs and agrees the ranking is defensible | Planned, ready to build |
| 2 | [Channels and pipeline](./002-phase2-channels-pipeline/spec.md) | 21 | Pilot companies stop uploading manually | Forward-looking |
| 3 | [Commercial launch](./003-phase3-commercial-launch/spec.md) | 24 | First unassisted self-serve paid conversion | Forward-looking |
| 4 | [Expansion](./004-phase4-expansion/spec.md) | 4 | None. Ongoing by design | Forward-looking, thin |

Seventy requirements, every one assigned to exactly one phase and traced in that phase's
specification. Phase 1 also carries [plan.md](./001-phase1-core-screening/plan.md), research, a data
model, contracts and a quickstart. The others carry a specification only, because planning them now
would be planning against three phases that do not exist.

## What each phase is actually for

**Phase 1 proves the product is possible.** A pile of CVs becomes a defensible ranking. If Arabic
extraction cannot hit its accuracy targets, everything downstream is moot, which is why the accuracy
suite is built before the interface.

**Phase 2 removes the manual labour.** CVs arrive on their own, candidates move through a pipeline,
and the screening layer that is the actual differentiator arrives. Phase 1 without Phase 2 is a
better spreadsheet.

**Phase 3 turns it into a business.** A stranger signs up, uses a free tier, hits the limit and pays,
with nobody at Masirah involved. This is where the commercial thesis is tested, and that thesis is
pricing rather than technology.

**Phase 4 grows it.** More capacity, another currency, and customers bringing customers.

## Read the forward-looking label seriously

Only Phase 1 is written against something real. Phases 2 to 4 rest on assumptions that Phase 1 will
test, particularly about extraction quality and how recruiters behave once they have a ranking they
trust. Each should be revalidated before its phase begins, and Phase 4 should be expected to be
rewritten rather than followed.

That is not a weakness of writing them now. Seeing the whole shape early is how you avoid building
Phase 1 in a way that makes Phase 3 expensive. It just is not the same thing as knowing.

## Dependencies that cross phases

| Dependency | Blocks | State |
|---|---|---|
| PDPL legal confirmation for the pilot arrangement (ADR 0003) | Phase 1 validation on real CVs | **Open.** Fallback is anonymised CVs |
| PDPL legal opinion, OQ-04 | Phase 3, paying customers processing their own candidates | **Open** |
| Legal entity and invoicing, OQ-07 | Phase 3 entirely. No way to take money without it | **Open, deliberately deferred** |
| Hosting migration off Netlify (ADR 0002) | Phase 3 commercial traffic | Planned |
| Market expansion beyond Egypt, OQ-09 | Phase 4 dollar billing | **Open, deliberately deferred** |
| Google restricted-scope verification | Nothing. Deliberately never a dependency | Uncertain, by design |
| WhatsApp template approval | Nothing. Additive by design | Uncertain, by design |

The three open legal and commercial questions are the real schedule risk, not the engineering. Each
is owned by the founder or external counsel and none is resolved by writing more specification.

## A known inconsistency in the source BRD

Section 14 of the BRD lists phase membership as ranges, and those ranges disagree with the Phase
column in the requirements table itself.

| Where | Disagreement |
|---|---|
| Phase 1 | Section 14 says FR-020 to FR-029. The table puts FR-025, FR-026 and FR-028 in Phase 2 |
| Phase 2 | Section 14 omits FR-003, FR-025, FR-026, FR-028 and FR-065, which the table places there |
| Phase 4 | Section 14 names scorecard aggregation and talent pool. The table puts FR-042 to FR-045 and FR-056 in Phase 3 |

**These specifications follow the requirements table throughout**, since a per-requirement
assignment is more specific than a range shorthand. The BRD still contains both statements. Fixing
it means replacing the section 14 ranges with explicit lists in both languages, which changes what
each phase means and is therefore the founder's decision rather than a tidy-up.

## Two requirements moved deliberately

ADR 0003 brought real pilot data into Phase 1, which pulled three controls forward with it, since
the data they protect now exists earlier than planned.

| Requirement | Was | Now |
|---|---|---|
| FR-076, deletion within 30 days | Phase 2 | Phase 1 |
| FR-074, access and export audit log | Phase 3 | Phase 1 |
| NFR-10, retention with automatic purge | Phase 2 | Phase 1 |
