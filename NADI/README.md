# NADI

**India's PHC network, predicted before it breaks.**

Public health facilities run out of medicine and nobody at district
level knows until a patient is turned away. NADI digitises the paper
stock register with a phone camera, scores every facility on whichever
of medicines, beds, or staff runs short first, forecasts shortages weeks
ahead, and proposes transfers from nearby facilities that already have
surplus. A district officer approves in one click.

*(30-second demo GIF goes here — it is the first thing a reviewer sees)*

**Live demo:** (url) · **Video:** (url) · **Deck:** (url)

No login required. Synthetic data. No real patient records.

---

## Architecture

*(architecture.png goes here)*

```
PHC app (offline PWA) ──► FastAPI ──► Postgres
                              ├─ forecasting  → days to stockout
                              ├─ optimiser    → transfer proposals
                              ├─ anomaly      → data trust scores
                              └─ twin         → outbreak scenarios
                          ──► Command web (district + national)

Federated layer: each state trains locally, only weights aggregate.
```

## Run it

```bash
git clone <repo> && cd nadi
cp .env.example .env          # add GEMINI_API_KEY
docker compose up             # api :8000, web :5173, db :5432
python data/seed.py --reset   # loads the synthetic district
```

Open http://localhost:5173

## Walk the demo

1. Landing page → **District officer**
2. Note the risk queue — 14 facilities amber or red
3. Click the top row → forecast chart with its driver
4. Header → **Run outbreak scenario** → map reddens
5. **Generate transfer plan** → arrows, table, 14 → 2 → **Approve all**
6. Landing → **PHC pharmacist** → Scan tab → upload
   `data/fixtures/register_1.jpg`
7. Landing → **National command** → Federation → note the zero counters

## Stack

Gemini (register extraction) · Cloud Run · Firebase Hosting ·
FastAPI · Postgres · React + Vite · MapLibre · OR-Tools ·
statsforecast · Flower

## Problem statement coverage

| Requirement | Where it lives |
|---|---|
| Real-time medicine stock visibility | Camera ingestion + offline sync |
| Bed availability | Derived from admit/discharge events |
| Personnel attendance | Role-level counts, inferred from activity |
| Demand forecasting | SKU-classified models with disease and season signals |
| Early warning in emergencies | Days-to-stockout + outbreak scenarios |
| Cross-district redistribution | Min-cost flow optimiser, human-approved |
| Shared modelling across states | Federated training, weights only |

## What is real vs simulated

**Real:** forecasting models, optimiser, anomaly detection, Gemini
extraction, offline sync, federated training loop.
**Simulated:** the district's stock history, disease counts, bed and
staff numbers, and the five state clients. The generator that produces
them is in `data/generator.py` with its seasonality assumptions
documented.

## Docs

`AGENTS.md` (session protocol) · `docs/PROJECT.md` · `docs/CONTEXT.md` ·
`docs/HANDOFF.md` · `docs/PHASES.md` · `docs/DATA_MODEL.md` ·
`docs/API.md` · `docs/DECISIONS.md` · `docs/GLOSSARY.md` · `docs/DEMO.md`
