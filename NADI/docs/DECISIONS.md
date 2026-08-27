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

## ADR-008 — Free OpenStreetMap tiles via MapLibre GL
**Date:** 2026-08-25 | **Session:** session-2026-08-25-b | **Status:** accepted
**Context:** Phase 1 requires a map of facilities. We need a map provider.
**Decision:** Use MapLibre GL with CartoDB dark_all tiles (OpenStreetMap).
**Rejected:** Mapbox GL JS (requires token/account), Google Maps (requires billing/key).
**Consequence:** No API keys required in .env for map functionality. Free and open.

## ADR-009 — Custom NumPy Forecasting Engine
**Date:** 2026-08-25 | **Session:** session-2026-08-25-d | **Status:** accepted
**Context:** Phase 2 requires SES and Croston SBA forecasting methods. Using statsforecast/Nixtla requires heavy C dependencies, complicating the Docker image and build process.
**Decision:** Implement SES and Croston SBA in pure Python using NumPy (ml/forecasting/engine.py).
**Rejected:** Adding statsforecast to requirements.txt. Too heavy, overkill for simple exponential smoothing and Croston SBA which can be implemented in ~150 lines of code.
**Consequence:** Forecasting logic must be maintained internally, but the deployment artifact remains lightweight.

## ADR-010 — 7-day lead time for reorder point
**Date:** 2026-08-25 | **Session:** session-2026-08-25-d | **Status:** accepted
**Context:** The reorder point formula (`burn_rate x lead_time`) needs a lead time assumption. Different facilities have different supply chain distances.
**Decision:** Default to 7 days for all facilities. Reasonable for intra-district transfers within Dhar.
**Rejected:** Per-facility configurable lead times. Adds schema complexity for no current Phase 2 benefit. Can be added in Phase 3 (Transfer) when actual transfer routing is implemented.
**Consequence:** Reorder point is conservative for nearby facilities and aggressive for remote ones. Acceptable for MVP.

## ADR-011 — Outbreak factor capped at 5x
**Date:** 2026-08-25 | **Session:** session-2026-08-25-d | **Status:** accepted
**Context:** The outbreak factor compares recent disease signal case counts to baseline. Extreme ratios (e.g., baseline near zero) can produce absurd forecasts.
**Decision:** Cap the outbreak factor at 5x and require a minimum baseline of 5 cases. Display the capped percentage in driver strings.
**Consequence:** Forecasts never inflate beyond 5x from outbreak alone. Combined with season factor, total inflation is bounded and human-readable.

## ADR-012 — Tailwind CSS for PHC app
**Date:** 2026-08-26 | **Session:** session-2026-08-26-b | **Status:** accepted
**Context:** Phase 4 requires building a React PWA for the PHC app. The command-web dashboard used custom CSS for glassmorphism. We need to style the new app rapidly.
**Decision:** Use Tailwind CSS for the PHC app, adhering to CONTEXT.md's stack choice.
**Rejected:** Custom CSS — too slow for rapid prototyping of complex mobile UIs.
**Consequence:** The PHC app will have Tailwind utilities, which may not share CSS classes with command-web, but speeds up development.

## ADR-013 — GenerateSW for Vite PWA
**Date:** 2026-08-26 | **Session:** session-2026-08-26-b | **Status:** accepted
**Context:** The PHC app must work offline. We need a service worker.
**Decision:** Use `vite-plugin-pwa` with `generateSW` strategy.
**Rejected:** Hand-rolling a service worker or using `injectManifest`. Hand-rolling is error-prone. `injectManifest` is more flexible but unnecessary for a simple app shell and API caching.
**Consequence:** Offline caching of static assets is handled automatically. API requests for sync will still require custom logic in IndexedDB (Dexie).

## ADR-014 — Upgrade to gemini-3.1-flash-lite
**Date:** 2026-08-26 | **Session:** session-2026-08-26-c | **Status:** accepted
**Context:** The `gemini-1.5-flash` model returned a 404 error because the older 1.5 strings were deprecated from the active SDK model availability list in the 2026 timeframe.
**Decision:** Upgrade the `POST /api/scan` endpoint to use `gemini-3.1-flash-lite`.
**Rejected:** Attempting to force-downgrade the `google-generativeai` SDK, which would re-introduce environment conflicts and instability.
**Consequence:** Better vision performance at slightly different latency metrics.

## ADR-015 — Conic-gradient for circular progress in Tailwind
**Date:** 2026-08-26 | **Session:** session-2026-08-26-c | **Status:** accepted
**Context:** Needed a circular progress indicator (CBI score) in the PHC React app. Using `border-8` draws a solid circle (100% full regardless of value).
**Decision:** Use an inline `conic-gradient` style applied to a Tailwind `rounded-full` div.
**Rejected:** SVG with `stroke-dasharray` and `stroke-dashoffset`. SVG is technically more robust but significantly more verbose in a simple React component that doesn't need to scale dynamically.
**Consequence:** Simple, performant CSS-only circle fill that is easy to template dynamically in JSX.

## ADR-016 — Map unrecognized drugs to db.stock master list in UI
**Date:** 2026-08-26 | **Session:** session-2026-08-26-d | **Status:** accepted
**Context:** Gemini Vision API fuzzy matching sometimes fails to recognize a drug, returning `drugId: null`. The user needs to manually map these to a known drug before confirming.
**Decision:** Map unrecognized drugs to the local `db.stock` table (via Dexie) as the master list.
**Rejected:** Fetching a new `/api/drugs` master list from the backend. The PHC app is an offline-first PWA. Relying on an API call during the scan flow breaks offline functionality.
**Consequence:** Unrecognized drugs can only be mapped to drugs that are already known/stocked at the facility.

## ADR-017 — Complete removal of Batch Number parsing
**Date:** 2026-08-26 | **Session:** session-2026-08-26-e | **Status:** accepted
**Context:** The LLM was configured to extract batch numbers from scanned documents, but user found the UI cluttered and requested the feature be entirely removed.
**Decision:** Removed `batch_no` from the Gemini extraction prompt, the database insertion mapping, and the frontend ScanTab inputs.
**Rejected:** Just hiding it in the UI but keeping it in the prompt (wastes LLM tokens and latency).
**Consequence:** The `transactions` table fallback (`UNKNOWN`) handles the null constraints. This feature must not be restored in future phases.

## ADR-018 — Modal popup for mapping unrecognized drugs
**Date:** 2026-08-26 | **Session:** session-2026-08-26-e | **Status:** accepted
**Context:** Inline `<input list="datalist">` elements in the scanned rows were cluttering the UI and prone to accidental clicks/edits on mobile.
**Decision:** Replaced the inline input with a static clickable `div` that triggers a full-screen mobile modal (bottom sheet/overlay) for editing the medicine name. Added a prominent red `UNRECOGNIZED DRUG` tag when the drug doesn't match.
**Rejected:** Accordion rows or inline editing. A modal provides a focused, native-app-like experience for text entry and datalist selection on mobile screens.
**Consequence:** State management for `editingRowIndex` added to `ScanTab`.

## ADR-021 — FedProx over FedAvg for simulated state clients
**Date:** 2026-08-26 | **Session:** session-2026-08-26-i | **Status:** accepted
**Context:** The 5 state clients in Phase 6 have deliberately non-IID data distributions (e.g., varying disease prevalence).
**Decision:** Use the FedProx strategy for the Federated Learning simulation.
**Rejected:** Plain FedAvg. With genuinely non-IID clients, plain averaging degrades global model performance because local updates drift too far apart. FedProx adds a proximal term to constrain local updates, ensuring stable convergence.
**Consequence:** Proves a deeper understanding of real-world federated learning challenges in the hackathon presentation.

## ADR-019 — Compute capacity scores dynamically on read
**Date:** 2026-08-26 | **Session:** session-2026-08-26-g | **Status:** accepted
**Context:** Phase 5 requires computing a Capacity Bottleneck Index (CBI) which is the minimum of medicine, bed, and staff scores.
**Decision:** Compute the scores dynamically in SQL within `GET /api/capacity`, relying on current `transactions`, `stock`, `bed_events`, and `staff_daily` tables, then upserting the result to `capacity_scores`.
**Rejected:** Running a background cron job to compute scores every hour. This adds infrastructure complexity and could serve stale data during a demo.
**Consequence:** The `/api/capacity` endpoint executes multiple heavy aggregate queries per facility. Acceptable for Phase 5 scale (26 facilities), but would need materialization at state scale.

## ADR-020 — Hover tooltips for counterintuitive domain metrics
**Date:** 2026-08-26 | **Session:** session-2026-08-26-h | **Status:** accepted
**Context:** Domain-specific metrics, such as "Medicine: 0%" meaning "0% of essential drugs are safely stocked" rather than "0 physical pills exist," routinely confuse users. 
**Decision:** Always include an info hover icon (`ⓘ`) next to confusing or derived metrics in the UI, which displays a simple-language explanation on hover and disappears otherwise.
**Rejected:** Explaining it in an external user manual or assuming domain knowledge. Users need inline context exactly where the confusion happens.
**Consequence:** Future UI additions displaying complex/derived metrics must include a tooltip explaining the calculation basis in plain English.

## ADR-022 — Dynamic anomaly detection and hashing for demo
**Date:** 2026-08-26 | **Session:** session-2026-08-26-h | **Status:** accepted
**Context:** Phase 7 (Trust) requires append-only hash chains and statistical anomaly detection (Benford's law). Applying this continuously on insert would slow down initial data seeding or require complex background workers not suited for a hackathon demo.
**Decision:** Compute hashes and run detection dynamically via a dedicated demo trigger endpoint (`/api/demo/trust/run`), similar to federation.
**Rejected:** In-flight trigger/middleware hash chaining and cron-based anomaly detection. Adds unnecessary moving parts and deployment risks for a constrained demo environment.
**Consequence:** The "hash" column on transactions remains null until the trust demo script is manually triggered, proving the capability without the overhead.

## ADR-023 — Skip Phase 8 (War room) to prioritize Phase 9 (Ship)
**Date:** 2026-08-27 | **Session:** session-2026-08-27-a | **Status:** superseded by ADR-024
**Context:** Phase 8 (War Room) is listed as droppable. To ensure a stable and ship-ready final product within time constraints, a choice must be made between building Phase 8 or proceeding to ship.
**Decision:** Skip Phase 8 entirely and proceed to Phase 9 (Ship), finalizing the repository for submission.
**Rejected:** Attempting a rushed implementation of Phase 8, which could break the existing stable Phase 1-7 demo flow.
**Consequence:** The final product will not include the outbreak counterfactual simulation or national choropleth.

## ADR-024 — Reverse ADR-023 and implement Phase 8
**Date:** 2026-08-27 | **Session:** session-2026-08-27-a | **Status:** superseded by ADR-025
**Context:** The user explicitly requested to proceed with Phase 8 despite the initial decision to skip it for time constraints.
**Decision:** Build the Phase 8 War Room feature using a simplified deterministic vectorised simulation instead of a complex Monte Carlo to ensure it fits within performance constraints.
**Rejected:** Leaving the product without the "preparedness" module.
**Consequence:** Adds `WarRoom.tsx` to the dashboard, providing fragility rankings and counterfactual impact metrics.

## ADR-025 — Merge War Room (Macro) and Dashboard (Micro)
**Date:** 2026-08-27 | **Session:** session-2026-08-27-a | **Status:** accepted
**Context:** Having a separate War Room tab created a disconnect between predicting a macro-level emergency and drilling down into micro-level facility management.
**Decision:** Merge the War Room simulation directly into the main Dashboard's Scenario Runner via a "Predict (Macro)" vs "Inject (Micro)" toggle. The Macro mode runs the twin simulation without modifying the database, lighting up the unified map and Risk Queue.
**Rejected:** Keeping them in separate tabs.
**Consequence:** `WarRoom.tsx` is deleted, simplifying navigation. The Dashboard now seamlessly supports both predicting counterfactuals (War Room) and injecting them into the live database (Phase 2).
