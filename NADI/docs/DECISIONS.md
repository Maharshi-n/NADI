# DECISIONS.md — architecture decision log

Append-only. Never edit or delete a past entry; supersede it with a new
one that references it.

Write an entry when you chose between real alternatives. Not for
obvious calls.

Template:

```
## ADR-00N — title
**Date:** | **Session:** | **Status:** accepted | superseded by ADR-00X
**Context:** what forced a choice
**Decision:** what we chose
**Rejected:** the alternatives and why they lost
**Consequence:** what this now constrains
```

---

## ADR-001 — Public health facilities, not retail pharmacies
**Date:** (project start) | **Status:** accepted
**Context:** The problem statement concerns PHC supply chains, beds, and
staff attendance across states. An earlier concept targeted private
medical shops and consumers.
**Decision:** Build exclusively for public health facilities with a
state health department as buyer.
**Rejected:** Consumer marketplace — no live inventory data exists from
private shops, the regulatory position on e-pharmacy remains unsettled,
and it addresses none of the beds, staff, or federation requirements.
**Consequence:** No citizen-facing surface. Ever.

## ADR-002 — Capacity as the minimum of three constraints
**Date:** (project start) | **Status:** accepted
**Context:** Stock, beds, and staff could each be a separate dashboard.
**Decision:** Collapse into one score per facility — the minimum of the
three — and always surface the binding constraint by name.
**Rejected:** Three parallel dashboards. They would not have explained
each other, and a facility with stock but no pharmacist would have
looked healthy.
**Consequence:** Every screen must show the bottleneck label, not just
a number. Beds and staff must feed the medicine forecast.

## ADR-003 — Recommend, never execute
**Date:** (project start) | **Status:** accepted
**Context:** Auto-ordering and auto-transfer are tempting demo features.
**Decision:** Every consequential action requires human approval.
**Rejected:** Autonomous transfer, even behind a flag. Accountability
for stock movement sits with a named officer; software cannot hold it.
**Consequence:** Approval UI in every workflow. Stated in the product
copy, not buried in docs.

## ADR-004 — No patient-level data
**Date:** (project start) | **Status:** accepted
**Context:** Footfall and bed occupancy could be modelled per patient.
**Decision:** Facility-level aggregates only. No names, no IDs, no
individual records — including for staff.
**Rejected:** Per-patient modelling. Marginal forecast gain, large
regulatory and ethical cost.
**Consequence:** Hard architectural boundary. Any proposal to store
individual records is rejected without further discussion.

## ADR-005 — Classical forecasting over deep learning
**Date:** (Phase 2) | **Status:** accepted
**Context:** Per-facility per-drug demand is sparse, lumpy, and short.
**Decision:** Classify each series and route to Croston/SBA/TSB for
intermittent demand, smoothing or gradient boosting for smooth demand.
**Rejected:** LSTM/transformer forecasting. Deep models underperform on
sparse short series, are unexplainable to a health officer, and the
highest-accuracy model is not the one that minimises inventory cost.
**Consequence:** Report service-level outcomes, not accuracy metrics.

## ADR-006 — Optimisation is called optimisation
**Date:** (Phase 3) | **Status:** accepted
**Context:** The transfer planner could be marketed as AI.
**Decision:** Call it a min-cost flow optimiser in all copy.
**Rejected:** Labelling it AI. Reviewers who know the field discount the
whole project when a solver is mislabelled.
**Consequence:** Slides and UI copy must be precise about which parts
are learned and which are solved.

## ADR-007 — JSON files as intermediate format between generator and seeder
**Date:** 2026-08-24 | **Session:** session-2026-08-24-a | **Status:** accepted
**Context:** `data/generator.py` could either output JSON files that
`data/seed.py` loads, or produce Python objects that seed.py calls
directly via import.
**Decision:** Generator writes JSON files to `data/generated/`. Seed
reads them and inserts into Postgres.
**Rejected:** Direct Python object coupling. It would make inspection
harder, tie the generator to the seeder's runtime, and prevent running
the generator on a different machine from the database.
**Consequence:** Generator is a standalone deliverable. Generated data
is inspectable. `data/generated/` is gitignored (45 MB). Two-step
workflow: generate then seed.
