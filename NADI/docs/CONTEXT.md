# CONTEXT.md — architecture and conventions

Update this only when architecture, stack, or conventions actually change.

---

## Repository layout

```
nadi/
├── AGENTS.md                 session protocol, read first
├── README.md                 public-facing, judged
├── docker-compose.yml        one command to run everything
├── .env.example              every env var, no real values
├── docs/
│   ├── PROJECT.md            what and for whom
│   ├── CONTEXT.md            this file
│   ├── HANDOFF.md            living state, updated every session
│   ├── PHASES.md             the build plan
│   ├── DATA_MODEL.md         schema and seed logic
│   ├── API.md                endpoint contracts
│   ├── DECISIONS.md          append-only ADR log
│   ├── GLOSSARY.md           domain vocabulary
│   └── DEMO.md               the demo script and what must work
├── apps/
│   ├── api/                  FastAPI backend
│   ├── command-web/          React dashboard (district + national)
│   └── phc-app/              React PWA (mobile, offline)
├── ml/
│   ├── forecasting/          demand models
│   ├── optimizer/            transfer planning
│   ├── federated/            Flower server and clients
│   ├── twin/                 outbreak simulation
│   └── anomaly/              data trust scoring
├── data/
│   ├── generator.py          synthetic district generator
│   ├── seed.py               loads generated data into the DB
│   └── fixtures/             register photos for the scan demo
└── infra/                    deploy configs
```

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | FastAPI, Python 3.11 | Async endpoints, Pydantic models |
| DB | Postgres 15 | Neon in production, Docker locally |
| ORM | SQLAlchemy 2.x | Or raw SQL where clearer |
| Frontend | React 18 + Vite + TypeScript | Two apps, shared component lib |
| Styling | Tailwind | No component framework |
| Maps | MapLibre GL | Free tiles, no Mapbox token |
| Charts | Recharts | |
| Offline | IndexedDB via Dexie + service worker | PHC app only |
| Forecasting | statsforecast, LightGBM | Croston/SBA/TSB for sparse SKUs |
| Optimisation | Google OR-Tools | Min-cost flow |
| Federated | Flower | Simulated clients, run offline |
| Vision | Gemini API | Register photo to structured rows |
| Hosting | Firebase Hosting + Cloud Run + Neon | See infra/ |

## System shape

```
PHC app (offline PWA)
    │ writes stock, beds, staff, dispensing
    ▼
FastAPI  ──►  Postgres
    │              │
    │              ├─► forecasting  ──► days-to-stockout, CBI
    │              ├─► optimizer    ──► transfer proposals
    │              ├─► anomaly      ──► trust score per record
    │              └─► twin         ──► outbreak scenarios
    ▼
Command web (district + national dashboards)

Federated layer runs out-of-band: each simulated state trains locally,
weights aggregate, results written to fl_rounds table for the UI to read.
```

## The four calculations everything depends on

```python
burn_rate      = dispensed_qty_last_30_days / 30
days_of_cover  = current_stock / burn_rate
predicted_rate = burn_rate * season_factor * outbreak_factor
days_to_stockout = current_stock / predicted_rate

medicine_score = pct of essential drugs with days_of_cover > 15
bed_score      = free_beds / expected_demand
staff_score    = critical_roles_present / critical_roles_required
CBI            = min(medicine_score, bed_score, staff_score)
```

`CBI` also records **which** of the three was the minimum. That label is
what the UI shows — "bottleneck: no pharmacist" is the product, not the
number 78.

## Conventions

**Naming.** Backend snake_case, frontend camelCase, DB snake_case. API
responses are camelCase — convert at the serialisation boundary, not
scattered through components.

**IDs.** Integer primary keys for internal entities. Facilities also
carry a `hfr_code` text field for future registry alignment; nullable
for now.

**Dates.** All timestamps UTC in the DB, `timestamptz`. Convert to IST
for display only. Dates without times use `date`.

**Money.** Store paise as integers, never floats. Display as `₹1,840`.

**Quantities.** Always integers with an explicit `unit` on the drug
record (tabs, caps, sachets, vials, ml).

**Errors.** API returns `{"error": {"code": "...", "message": "..."}}`
with a real HTTP status. Never a 200 with an error body.

**No nulls in API responses** where a zero or empty array is meaningful.
An empty risk queue is `[]`, not `null`.

**Every list endpoint** takes `limit` and `offset` and returns
`{"items": [...], "total": n}`.

## Frontend conventions

- One accent colour plus red / amber / green for status only
- Status thresholds are shared constants, never repeated per component:
  `CRITICAL < 15 days`, `WARNING < 30 days`, else healthy
- Skeleton loaders, never blank screens
- Every timestamp displayed as relative time ("6 min ago")
- No control rendered for an unbuilt feature
- Both apps share `packages/ui` for status pills, cards, and the colour
  constants

## Demo mode

The deployed app runs in demo mode permanently:

- No authentication; a role switcher in the header
- `POST /api/demo/scenario` injects an outbreak
- `POST /api/demo/reset` restores the seed state
- API auto-seeds on startup if the DB is empty

Demo mode is a first-class feature, not a hack. It is how judges
experience the product.

## What is real vs simulated

State this honestly everywhere — README, deck, and video.

| Real | Simulated |
|---|---|
| Forecasting models | The district's stock and dispensing history |
| Optimiser and its constraints | Disease case counts |
| Anomaly detection | Bed and staff numbers |
| Gemini register extraction | The five federated state clients |
| Offline sync | |

The generator that produces simulated data is itself a deliverable — it
encodes seasonality assumptions and is worth showing.
