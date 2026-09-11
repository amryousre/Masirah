# Feature Specification: Phase 4 Expansion

**Feature Branch**: `004-phase4-expansion`

**Created**: 2026-09-11

**Status**: Draft, forward-looking and deliberately thin

**Input**: Written as part of specifying all four phases up front, to give a clear picture of the
whole product before building begins.

Phases 1 to 3 build a product and turn it into a business. Phase 4 grows that business: reach
customers outside Egypt's currency, let existing customers buy more, and make growth cheaper by
paying customers to bring other customers.

The BRD marks this phase **ongoing with no exit criterion**, which is correct. It is not a release
so much as the point at which the roadmap gives way to whatever the market actually asks for.

> **This specification is intentionally the thinnest of the four.** It sits behind three phases and
> at least a year of learning. Writing it in the detail of Phase 1 would be false precision.
> Its purpose is to show where the product is heading, not to be built from.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buy more without changing plan (Priority: P1)

A customer on Starter has an unusually heavy hiring month. Rather than jumping to a plan they do not
need year-round, they buy a block of extra CV capacity and carry on.

**Why this priority**: It is the cheapest revenue in the phase, it removes a reason to churn, and it
answers a complaint that will arrive the first time a customer hits a quota mid-shortlist.

**Independent Test**: From an account at its quota, purchase an add-on block and confirm processing
resumes immediately without a plan change.

**Acceptance Scenarios**:

1. **Given** an account at or near its monthly quota, **When** the user buys an add-on block of CV
   capacity, **Then** processing resumes immediately without changing their plan.
2. **Given** a purchased add-on, **When** the billing period rolls over, **Then** the treatment of
   unused capacity is stated plainly at the point of purchase rather than discovered afterwards.

---

### User Story 2 - Pay in dollars (Priority: P2)

A company in the Gulf wants the product. They cannot pay in Egyptian pounds and will not try.

**Why this priority**: It opens a segment with materially higher willingness to pay, and the BRD
already names Gulf presence as a competitor strength. It sits below add-ons because it is more work
and because it depends on a market decision that is still open.

**Independent Test**: Complete a subscription in dollars from outside Egypt and confirm the account
behaves identically to an Egyptian pound account in every respect other than currency.

**Acceptance Scenarios**:

1. **Given** a customer outside Egypt, **When** they subscribe, **Then** they can pay in dollars.
2. **Given** a dollar-billed account, **When** it is used, **Then** quotas, features and behaviour are
   identical to an Egyptian pound account.
3. **Given** an existing Egyptian pound customer, **When** dollar billing launches, **Then** their
   billing is untouched.

---

### User Story 3 - Grow through customers rather than advertising (Priority: P2)

A happy customer refers another company. Both get a free month, credited only once the referred
company actually pays.

**Why this priority**: The BRD names referral as the cheapest acquisition channel available to a
bootstrapped product. It is P2 because it is worth little until there are enough happy customers to
refer anyone.

**Independent Test**: Complete a referral end to end and confirm neither side is credited until the
referred account's first payment clears.

**Acceptance Scenarios**:

1. **Given** an existing customer, **When** they refer a company that subscribes, **Then** both
   receive one free month, credited at the referred account's first payment.
2. **Given** a referral that never converts to payment, **When** time passes, **Then** no credit is
   issued to either party.
3. **Given** attempted self-referral or circular referral, **When** detected, **Then** no credit is
   issued.

---

### User Story 4 - Reward the customers who took the early risk (Priority: P3)

The companies that paid before the product was proven keep their original price when the list price
rises.

**Why this priority**: Cheap to honour, disproportionately valuable to the relationship, and it
costs nothing until prices actually change.

**Acceptance Scenarios**:

1. **Given** an account flagged as an early adopter, **When** list prices rise, **Then** their price
   holds for the defined period.
2. **Given** the lock period ending, **When** it expires, **Then** the customer is told before the
   price changes rather than after.

---

### Edge Cases

- A customer holds both an add-on block and a granted free period.
- Egyptian pound to dollar exchange movement makes one currency's pricing inconsistent with the
  other, which the BRD notes as a competitor weakness worth not repeating.
- A referred company signs up, pays, and refunds within the same month.
- An early-adopter price lock survives a plan upgrade, or does not, and which of those happens must
  be decided rather than discovered.
- A customer wants to move from Egyptian pound billing to dollar billing mid-subscription.

## Requirements *(mandatory)*

- **FR-001**: Users MUST be able to purchase add-on blocks of CV capacity without changing plan.
- **FR-002**: System MUST collect subscriptions in dollars from customers outside Egypt.
- **FR-003**: System MUST operate a referral programme granting one free month to each side, credited
  at the referred account's first payment.
- **FR-004**: System MUST support an early-adopter flag locking an account's price for a defined
  period regardless of later list-price changes.

### Key Entities

Earlier entities continue. New in this phase:

- **Referral**: The link between referring and referred organisation, and the credits issued to each.
- **Add-on purchase**: A block of additional capacity bought against a subscription.
- **Price lock**: An account-level flag fixing price for a period.

## Success Criteria *(mandatory)*

- **SC-001**: A customer at their quota can buy capacity and resume work in under two minutes.
- **SC-002**: Referral becomes a measurable acquisition channel rather than a feature nobody uses.
- **SC-003**: No early-adopter price changes without advance notice.
- **SC-004**: Dollar-billed and Egyptian pound-billed accounts behave identically apart from
  currency.
- **SC-005**: Twelve-month targets from the BRD are met: 150 paying organisations, monthly churn at
  or below 3 percent, and processing cost at or below 1.5 EGP per CV.

## Assumptions

- Phase 3 has shipped and self-serve conversion works. Everything here assumes paying customers
  already exist.
- **OQ-09 is resolved before dollar billing.** Selling outside Egypt is currently open and deferred.
  Dollar billing is the implementation of a market decision that has not been taken, so User Story 2
  cannot start until it has been.
- Stripe handles dollar collection, alongside rather than replacing Paymob.
- Pricing in dollars is set deliberately rather than converted from the Egyptian pound list, to avoid
  the exchange-rate exposure the BRD identifies in a competitor.

## Explicitly beyond this phase

BRD section 7.3 defers these to version 2.0, and none is specified here:

- A public branded careers page.
- Native Wuzzuf and Forasna API integration, which OQ-06 settled as non-cooperative and deferred.
- A business intelligence connector.
- Mobile applications. Version 1.0 is responsive web only.

## Traceability to the BRD

| BRD | Requirement | Spec | Story |
|---|---|---|---|
| FR-086 | Add-on CV volume blocks | FR-001 | US1 |
| FR-083 | USD subscription via Stripe | FR-002 | US2 |
| FR-092 | Referral programme | FR-003 | US3 |
| FR-093 | Early-adopter price lock | FR-004 | US4 |

All four Phase 4 requirements are covered.

**BRD section 14 lists more in this phase than the requirements table does.** Section 14 names
scorecard aggregation, talent pool matching and the careers page here, but the table assigns
FR-042 to FR-045 and FR-056 to Phase 3, which is where this specification set places them. This is
the same disagreement between section 14 and the requirements table already flagged for Phases 1 and
2, and it is recorded rather than resolved silently.
