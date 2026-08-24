# HANDOFF.md — living state

**The most important file in the repo.** Overwrite "Current state" every
session. Append to the log. Never let this drift from reality.

---

## Current state

**Phase:** 1 — The Spine
**Status:** ready to start
**Last updated:** 2026-08-25 by session-2026-08-25-a

**Works right now:**
- Repo scaffold matches CONTEXT.md layout — all directories created
- docker-compose.yml brings up Postgres + FastAPI successfully (port 5433 mapped to avoid local conflict)
- All 15 SQLAlchemy models match DATA_MODEL.md exactly
- `data/generator.py --seed 42` produces deterministic synthetic data:
  26 facilities (22 PHC + 3 CHC + 1 warehouse), 40 drugs (25 essential,
  4 cold-chain), 141,608 transactions over 180 days, 1,040 stock rows
- Generator includes: weekend dips, seasonality, ~40% intermittent demand,
  3 under-reporters, 2 backdaters, 1 impossible spike, 1 no-pharmacist facility
- `data/seed.py --reset` loads generated JSON into Postgres successfully (seeded 145916 rows)
- `.env` configured for Docker DB connection

**Broken / needs fixing first:**
- (none)

**Next task, precisely:**
1. Begin Phase 1 (The Spine) by building the backend endpoints (`GET /api/facilities`, `GET /api/stock`, `GET /api/risk`).
2. Implement SQL queries for computing burn rate and days-of-cover.
3. Build the frontend dashboard (`command-web`) with MapLibre, risk queue, and KPI tiles.

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
