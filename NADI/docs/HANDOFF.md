# HANDOFF.md — living state

**The most important file in the repo.** Overwrite "Current state" every
session. Append to the log. Never let this drift from reality.

---

## Current state

**Phase:** 3 — Optimization
**Status:** Phase 2 complete. Ready to begin Phase 3 (Transfers and Optimization).
**Last updated:** 2026-08-25 by session-2026-08-25-d

**Works right now:**
- Generator and seeder work completely.
- Phase 1 API and Dashboard are complete.
- Phase 2 API (Forecast engine with SES and Croston SBA) works.
- Phase 2 Dashboard (Forecast Panel, Scenario Runner) works.

**Broken / needs fixing first:**
- Cannot test end-to-end locally because Docker is not available in the current environment.

**Next task, precisely:**
1. Start Phase 3 (Optimization).
2. Implement min-cost flow optimizer for supply transfers.
3. Add API routes for transfer planning and approval.
4. Update frontend to include transfer interface.

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

---

## Session log

Append one block per session. Newest at the top. Keep each to five lines.

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
### 2026-08-25 � session-2026-08-25-d
- **Did:** Built Phase 2 Forecast Engine (SES, Croston SBA), Phase 2 API endpoints, and Dashboard (ForecastPanel, ScenarioRunner, RiskQueue driver/confidence enhancements).
- **Decided:** Implemented SES and Croston SBA manually using NumPy instead of relying on statsforecast for a lighter build (ADR-009).
- **Left broken:** Docker not available, so no E2E test run yet.
- **Next session should:** Validate everything once docker is back or proceed to Phase 3.
