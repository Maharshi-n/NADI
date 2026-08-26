# HANDOFF.md — living state

**The most important file in the repo.** Overwrite "Current state" every
session. Append to the log. Never let this drift from reality.

---

## Current state

**Phase:** 3 — Optimiser
**Status:** Phase 3 complete. Backend min-cost flow engine, plan API, transfer approval workflow, and frontend Transfer Planner route with interactive map and impact panel are fully functional.
**Last updated:** 2026-08-26 by session-2026-08-26-a

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
- TypeScript compiles with zero errors.

**Broken / needs fixing first:**
- None.

**Next task, precisely:**
1. Start Phase 4 (Mobile/Field Interface) or finalize remaining polish on Phase 3 (animations, transitions).

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
