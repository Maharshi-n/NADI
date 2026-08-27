# HANDOFF.md — living state

**The most important file in the repo.** Overwrite "Current state" every
session. Append to the log. Never let this drift from reality.

---

## Current state

**Phase:** 8 - War Room / 9 - Ship
**Status:** Phase 8 implemented and successfully merged into the main Dashboard as a "Macro (Predict)" mode. The standalone `WarRoom.tsx` tab was removed to unify the command center.
**Last updated:** 2026-08-27 by session-2026-08-27-a

**Works right now:**
- Docker compose environment runs properly (`postgres` and `api` working together).
- Phase 1 endpoints (`/api/facilities`, `/api/stock`, `/api/risk`, `/api/kpis`) unchanged and working.
- **Phase 2 forecasting engine** (`ml/forecasting/engine.py`): SES for smooth/erratic, Croston SBA for intermittent/lumpy. Season + outbreak factors applied. Driver attribution and confidence scoring working.
- **`GET /api/forecast?facilityId=&drugId=`** returns 90 days history + 30 days forecast with confidence band, stockout projection, driver string, and method used.
- **`POST /api/demo/scenario`** injects outbreak signals (3 weeks of inflated case counts) and invalidates forecast cache. Returns affected facility count.
- **`POST /api/demo/reset`** restores seed state from `data/generated/*.json` files.
- **Frontend ForecastPanel** — Recharts ComposedChart showing history line, forecast band, reorder line, stockout marker. Shows driver chip and method badge.
- **Frontend ScenarioRunner** — condition dropdown, multiplier slider, fire/reset buttons.
- **RiskQueue** shows confidence and driver from Phase 2 data when available.
- **Phase 3 Transfer Planner** (`TransferPlanner.tsx`): MapLibre integration showing directional transfer lines (`TransferMap`), an interactive impact panel (`ImpactPanel`), and a transfer approval list (`TransferTable`).
- **Phase 3 Backend API**: `POST /api/plan` runs the OR-Tools optimizer, and `POST /api/transfers/approve` persists transfers into PostgreSQL. `test_phase3.py` passes all verification checks.
- **Phase 4 PHC App**: Vite React PWA setup (`apps/phc-app`) with TailwindCSS, Lucide icons, Dexie for offline IndexedDB storage.
- **Phase 4 Scanning**: Gemini Vision integration via `/api/scan` for register ingestion and fuzzy matching, with offline mutation queueing logic.
- **Phase 4 UI Polish**: App explicitly listens on 0.0.0.0. "Batch Number" parsing completely removed. Unrecognized drugs display an explicit tag and can be mapped using a mobile-friendly modal popup.
- **Phase 5 Capacity**: `/api/capacity` computes a Capacity Bottleneck Index (CBI) dynamically in SQL (min of medicine, beds, staff scores). Staff inferences (no dispensing = no pharmacist) implemented.
- **Phase 5 UI**: `CapacityPanel` overlays the map to show CBI ring, constraint bars, bed spillover info, and staff roster. RiskQueue flags facilities with staff/bed bottlenecks instead of just medicines.
- **Phase 6 Federation API**: Added `/api/federation/status` (fetches `fl_rounds` and `fl_clients`) and `/api/demo/federation/run` (triggers `simulation.py`).
- **Phase 6 Federation UI**: Built `FederationDashboard.tsx` in `apps/command-web`. Features 5 state cards showing training status and sample size, an accuracy line chart (FedProx vs Baseline), a mono-font transfer log proving zero raw records were transferred, and a cold-start callout for Chhattisgarh.
- **Phase 7 Trust API**: Added `/api/trust/anomalies` to fetch anomalies and `/api/demo/trust/run` to trigger anomaly detection and ledger hashing. `ml/anomaly/detector.py` handles Benford's law, impossible consumption rates, and backdated edit checks.
- **Phase 7 Trust UI**: Created `DataTrust.tsx` in `apps/command-web` for viewing detected data anomalies with confidence and rule triggers.
- TypeScript compiles with zero errors.

**Broken / needs fixing first:**
- None.

**Next task, precisely:**
1. Submit the hackathon project or perform real deployment if GCP credentials become available.

---

## In flight (claim before you start)

Format: `- [session-id] area — paths you will touch`

- (none)

---

## Known issues

Things noticed but deliberately not fixed. Do not drive-by fix these;
pick one up as a task.

| # | Issue | Where | Severity |
|---|---|---|---|
| 1 | Docs reference `docs/` paths but were at root — now moved | docs/ | resolved |
| 2 | transactions.json is 45 MB — may want binary/parquet for speed | data/generated | low |
| 3 | Batch number OCR parsing deliberately removed per user request. DO NOT RESTORE. | apps/api/routes.py | intentional |

---

## Blocked / waiting

| Item | Blocked on | Who |
|---|---|---|
| (none) | | |

---

## Environment notes

Anything a new session needs that is not in CONTEXT.md — a flaky
dependency, a version pin, a workaround.

- Python 3.14 is installed on this machine
- Docker is now verified to be working.
- DB mapped to port 5433 to avoid local conflicts.
- Generator runs standalone without Postgres: `python data/generator.py`
- Generated data lands in `data/generated/*.json` (~45 MB total)
- **Docker compose mounts `ml/` at `/ml` and `data/` at `/data`** inside the API container for forecasting engine access.
- `asyncpg` requires native Python date objects, not ISO strings — parse before insert.

---

## Session log

Append one block per session. Newest at the top. Keep each to five lines.

### 2026-08-27 — session-2026-08-27-a
- **Did:** Implemented the Phase 8 War Room backend simulation engine (`ml/twin/simulator.py`). Merged the War Room into the main Dashboard (`Dashboard.tsx` & `ScenarioRunner.tsx`) using a Macro/Micro toggle. Deleted the standalone `WarRoom.tsx` tab for a unified experience. 
- **Decided:** Merged Macro (War Room) and Micro (Dashboard) simulation modes (ADR-025) into a single Command Center.
- **Left broken:** None. The repository is ready to ship.
- **Next session should:** Submit the project or deploy to GCP/Firebase if credentials are provided.

### 2026-08-26 — session-2026-08-26-h
- **Did:** Implemented Phase 7 Trust features. Added `ml/anomaly/detector.py` to detect anomalies via Benford's law, impossible rates, and backdated edits, and to compute ledger hashes. Added Trust endpoints to `apps/api/routes.py` and built the `DataTrust.tsx` dashboard.
- **Decided:** Computed hashes and ran detection dynamically on the demo trigger rather than at insert time to ensure batch demo compatibility (ADR-022).
- **Left broken:** None. The Data Trust dashboard successfully highlights the seeded flaws.
- **Next session should:** Begin Phase 8 (War room) or jump to Phase 9 (Ship).

### 2026-08-26 — session-2026-08-26-g
- **Did:** Implemented Phase 6 Federation features. Built `ml/federated/simulation.py` to mock 10 rounds of training across 5 states. Added API endpoints to retrieve training data. Created `FederationDashboard` with state cards, Recharts accuracy comparison, and a live transfer log.
- **Decided:** Use FedProx over FedAvg for simulated state clients because of non-IID data distributions (ADR-021).
- **Left broken:** None. The Federation dashboard successfully visualizes the FedProx simulation metrics and proves privacy constraints.
- **Next session should:** Begin Phase 7 (Trust).

### 2026-08-26 — session-2026-08-26-f
- **Did:** Implemented Phase 5 Capacity features. Added endpoints for CBI computation (`/api/capacity`), bed events, and staff check-ins. Updated `GET /api/risk` to include staff/bed bottlenecks alongside medicines. Built `CapacityPanel` UI with CBI rings and constraint bars. Fixed Vite proxy configuration for docker.
- **Decided:** Compute capacity scores dynamically on read in SQL rather than via cron job (ADR-019). If pharmacist is missing, explicitly force bottleneck to "staff".
- **Left broken:** None. Phase 5 exit test passes (no-pharmacist facility shows staff bottleneck).
- **Next session should:** Begin Phase 6 (Federation).

### 2026-08-26 — session-2026-08-26-e
- **Did:** Removed `batch_no` OCR parsing completely. Redesigned Scan UI to use a modal popup for drug mapping instead of inline inputs. Added explicit `UNRECOGNIZED DRUG` badges. Fixed Days of Cover rounding logic (`> 90 days`). Ensured Vite dev server listens on 0.0.0.0 for LAN access.
- **Decided:** Completely abandon the batch number feature per user preference (ADR-017). Use a mobile-first Modal for drug mapping (ADR-018).
- **Left broken:** None.
- **Next session should:** Begin Phase 5 (Capacity & Referrals).

### 2026-08-26 — session-2026-08-26-d
- **Did:** Fixed 500 error in `/api/scan/confirm` by handling empty expiry dates correctly. Added editable rows and drug mapping dropdown to the Phase 4 `ScanTab` UI. Fixed missing PWA types in frontend `tsconfig.json`.
- **Decided:** Mapped unrecognized drugs to `db.stock` master list in Dexie to allow users to associate fuzzy string matches.
- **Left broken:** None.
- **Next session should:** Begin Phase 5 (Capacity & Referrals).

### 2026-08-26 — session-2026-08-26-c
- **Did:** Fixed Gemini API scan endpoint 404 error by migrating to `gemini-3.1-flash-lite`. Fixed UI bug where CBI score circle showed 100% full instead of 60% by switching from solid border to conic-gradient. Stopped all backend and frontend dev servers.
- **Decided:** Migrated to Gemini 3.1 Flash Lite for API compatibility (ADR-014). Used conic-gradient for circular progress bars instead of SVGs (ADR-015).
- **Left broken:** None.
- **Next session should:** Begin Phase 5 (Capacity & Referrals).

### 2026-08-26 — session-2026-08-26-b
- **Did:** Fixed 500 error in outbreak scenario (added missing UNIQUE constraint to `forecasts` table). Built Phase 4 PHC app using Vite, React, Tailwind, and Dexie for offline sync. Integrated Gemini API for parsing register scans. Added `/api/scan` and `/api/sync` endpoints.
- **Decided:** Used TailwindCSS for mobile styling (ADR-012) and Vite PWA plugin with `generateSW` strategy (ADR-013).
- **Left broken:** None. Phase 4 is complete.
- **Next session should:** Begin Phase 5 (Capacity & Referrals).

### 2026-08-26 — session-2026-08-26-a
- **Did:** Fixed Phase 3 backend import and SQL casting bugs. Verified `test_phase3.py` passes. Built Phase 3 frontend components: `TransferPlanner`, `TransferMap`, `ImpactPanel`, and `TransferTable`. Integrated frontend with the `generatePlan` and `approveTransfers` API endpoints.
- **Decided:** Used maplibre-gl GeoJSON line strings to draw transfer lines on the map.
- **Left broken:** None. Phase 3 is complete.
- **Next session should:** Begin Phase 4 (Mobile/Field app) or add polish.

### 2026-08-25 — session-2026-08-25-d
- **Did:** Built Phase 2 forecasting: `ml/forecasting/engine.py` (SES + Croston SBA), 3 new API endpoints (`/forecast`, `/demo/scenario`, `/demo/reset`), frontend ForecastPanel + ScenarioRunner + RiskQueue upgrades. Upgraded `/api/risk` and `/api/facilities` to read from the `forecasts` table, allowing map pins and risk queue to instantly update when a scenario fires. All 7 API tests pass.
- **Decided:** 7-day lead time for reorder point (ADR-010). Pure NumPy per ADR-009 — no statsforecast. Capped outbreak factor at 5× to prevent absurd predictions.
- **Left broken:** None.
- **Next session should:** Run full Phase 2 acceptance test (fire outbreak → queue reorders), then start Phase 3.

### 2026-08-25 — session-2026-08-25-c
- **Did:** Ran start-of-session ritual, mapped Phase 2 scope, started frontend dev server. No code changes.
- **Decided:** Nothing.
- **Left broken:** None.
- **Next session should:** Begin Phase 2 implementation.

### 2026-08-25 — session-2026-08-25-b
- **Did:** Built Phase 1 backend API routes (SQL burn rates) and frontend React dashboard (MapLibre, risk queue).
- **Decided:** Used CartoDB dark_all tiles for free map (ADR-008) and custom CSS for glassmorphism styling instead of Tailwind utilities for speed/control.
- **Left broken:** Integration tests blocked — Docker/Postgres environment unavailable in this session.
- **Next session should:** Fix database environment, run e2e test, and verify Phase 1 acceptance criteria.

### 2026-08-25 — session-2026-08-25-a
- **Did:** Started Docker compose, solved port 5433 conflict, seeded database with synthetic data, verified Phase 0 SQL output manually. Marked Phase 0 complete.
- **Decided:** Mapped Docker Postgres to 5433 externally to avoid conflicts with local Postgres.
- **Left broken:** None.
- **Next session should:** Start building backend endpoints for Phase 1.

### 2026-08-24 — session-2026-08-24-a
- **Did:** Full Phase 0 scaffold. Moved docs to docs/. Created docker-compose.yml, FastAPI backend with all 15 SQLAlchemy models, data/generator.py (26 facs, 40 drugs, 180 days, flaws), data/seed.py with --reset. Verified generator output quality.
- **Decided:** JSON files as intermediate format between generator and seeder (ADR-007). Dhar district, MP as the pilot district.
- **Left broken:** No Docker available — integration test (compose up + seed + SQL verify) not run.
- **Next session should:** Install Docker, run integration test, pass Phase 0 exit test, then start Phase 1.
