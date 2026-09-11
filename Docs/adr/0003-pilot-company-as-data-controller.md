# Pilot company acts as data controller for Phase 1 validation

Phase 1 exits on a pilot company processing 200 real CVs and agreeing the ranking is defensible
(BRD section 14), but the Egypt PDPL legal opinion (OQ-04) is not scheduled until before Phase 2,
and real CVs are real personal data. Rather than weaken the exit criterion to anonymised CVs or
pull the legal opinion forward, the pilot company processes CVs from its own applicants under the
consent it already holds, acting as data controller with Masirah processing on its behalf.
Development and parser testing continue to run on the founder's own corpus with names, phone
numbers and email addresses replaced, so real candidate data appears only in pilot validation and
never in day-to-day development.

## Status

**Accepted, conditional.** This rests on a legal position that nobody qualified has confirmed.
Before any pilot company loads real CVs, written confirmation is required on three points: that
the controller and processor split is valid under Law 151 of 2020, that the pilot's existing
candidate consent extends to processing by a third-party tool, and that transfer to EU
infrastructure is permitted. If that confirmation does not arrive, the fallback is the option
rejected here: exit Phase 1 on anonymised CVs and leave the legal opinion on its original
schedule.

## Consequences

Real candidate data reaches the Frankfurt Supabase instance during Phase 1, earlier than the
original plan assumed. Several controls scheduled for Phase 2 therefore become Phase 1
obligations in practice, because the data they exist to protect will already be present:
retention limits with automatic purge (NFR-10), deletion on request within 30 days (FR-076), and
the audit trail of data access and export (FR-074). A written processing agreement with each
pilot company is also needed before their first upload.
