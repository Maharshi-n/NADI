# PHASES.md — implementation plan

Ten phases. Each ends with something a human can click. Never start a
phase before the previous one's exit test passes.

**Two tracks.** Compressed = 48-hour hackathon. Standard = three-week
build. Pick one and stay on it.

| Phase | Standard | Compressed | Can drop? |
|---|---|---|---|
| 0 Foundation | 1 day | 3 h | No |
| 1 Spine | 2 days | 6 h | No |
| 2 Forecast | 2 days | 5 h | No |
| 3 Optimiser | 2 days | 5 h | No |
| 4 PHC app | 3 days | 8 h | No |
| 5 Capacity | 2 days | 4 h | No |
| 6 Federation | 2 days | 4 h | No |
| 7 Trust | 1 day | 2 h | Yes |
| 8 War room | 2 days | 3 h | Yes |
| 9 Ship | 2 days | 6 h | No |

If time runs out, you ship after Phase 6 with a coherent product. Phases
7 and 8 are upside.

---

## Phase 0 — Foundation

**Product outcome:** nothing visible yet, but every later phase becomes
straightforward instead of blocked.

Data comes first. Every screen in this product renders rows. Without
believable rows, every subsequent phase stalls on "what do I display?"

### Build

1. Repo scaffold matching `CONTEXT.md`, `docker-compose.yml` bringing up
   Postgres + API + web with one command.
2. Schema migration creating every table in `DATA_MODEL.md`. Create all
   of them now, even ones used in Phase 6 — schema churn mid-build is
   what breaks parallel sessions.
3. `data/generator.py` — the important artefact. It must produce:
   - 22 PHCs, 3 CHCs, 1 district warehouse, real lat/lng inside one
     district boundary
   - 40 drugs, of which 25 flagged essential, with realistic units
   - 180 days of daily dispensing per facility per drug
   - Seasonality baked in: vector-borne rise Jun–Sep, respiratory rise
     Nov–Jan, ORS spike with summer and with any diarrhoeal signal
   - Intermittency: roughly 40% of drug/facility pairs should have
     sparse, lumpy demand with many zero days. Smooth demand everywhere
     is the tell of fake data and makes Phase 2 trivially easy in a way
     that will not generalise
   - Deliberate flaws: 3 facilities that under-report, 2 with backdated
     edits, 1 with a physically impossible consumption spike. Phase 7
     needs these to exist
   - Current stock levels reverse-engineered so that ~6 facilities are
     already amber and ~3 red on day zero
4. `data/seed.py` loading generated output, idempotent, with `--reset`.
5. `docs/` files filled in, `.env.example` complete.

### Acceptance

- [x] `docker compose up` from a clean clone produces a running API
- [x] `python data/seed.py --reset` completes and reports row counts
- [x] `SELECT` on any table returns believable data
- [x] Re-running seed twice does not duplicate rows

### Exit test

Open a SQL client, pick a random facility and drug, and eyeball 180 days
of dispensing. Does it look like a real health facility's record — with
weekends dipping, seasons moving, and gaps? If it looks like noise
around a constant, fix the generator before moving on.

### Do not

Do not build any UI. Do not write forecasting code. Do not skip the
deliberate-flaws requirement because it feels like extra work — Phase 7
is impossible without it.

---

## Phase 1 — The spine

**Product outcome:** a district officer opens a URL and sees every PHC
in their district, colour-coded by how close each is to running out.
This is the smallest thing that is genuinely useful.

### Build

Backend:
- `GET /api/facilities` — list with lat/lng, type, current status
- `GET /api/facilities/{id}` — detail with current stock
- `GET /api/stock?facility_id=` — stock rows with days of cover
- `GET /api/risk?district=` — the ranked list. Days of cover only at
  this stage, no forecasting yet
- Burn rate and days-of-cover computed in SQL, not Python — this stays
  fast at scale and the query is worth getting right once

Frontend (`command-web`):
- App shell, header, role switcher stub
- District dashboard route
- MapLibre map with facility pins coloured by worst days-of-cover
- Risk queue panel, ranked, clickable
- Four KPI tiles, computed server-side in one endpoint
- Skeleton loaders

### Acceptance

- [ ] Map shows 26 facilities in correct geographic positions
- [ ] Pin colour matches the facility's worst days-of-cover
- [ ] Risk queue is sorted ascending by days remaining
- [ ] Clicking a queue row highlights its pin
- [ ] KPI tiles show non-zero, plausible numbers
- [ ] Page loads in under 2 seconds on seed data

### Exit test

Show it to someone who has not seen the project. Ask: "which facility is
in the most trouble?" If they can answer in under five seconds, the
phase is done.

### Do not

Do not add forecasting. Do not add tabs for beds and staff yet. Resist
building the transfer feature — it depends on Phase 2 output.

---

## Phase 2 — Forecast

**Product outcome:** the dashboard stops reporting the present and
starts reporting the future, with a reason attached.

This is where the product earns the word "predict." The critical design
choice: the forecast must always come with a driver. "Runs out in 9
days" is useful. "Runs out in 9 days because dengue cases rose 180% in
this block" is what makes an officer act.

### Build

- `disease_signal` ingestion — seeded weekly case counts per district
  per condition
- Season factors — a lookup by drug category and month, derived from the
  generator's own seasonality so the model can actually recover it
- SKU classification: for each facility-drug pair, classify demand as
  smooth, erratic, intermittent, or lumpy using the coefficient of
  variation and the average inter-demand interval. Route each class to
  a method: exponential smoothing or LightGBM for smooth and erratic,
  Croston / SBA / TSB for intermittent and lumpy
- `predicted_rate = burn_rate * season_factor * outbreak_factor`, with
  the model producing burn_rate and the factors applied on top
- Confidence: derived from history length, demand variance, and the
  trust score placeholder. Surface it — a forecast that admits doubt is
  more credible than one that does not
- Driver attribution: record which factor moved the forecast most and
  return it as a human string
- `GET /api/forecast?facility_id=&drug_id=` returning history, forecast
  band, reorder point, projected stockout date, confidence, driver
- `POST /api/demo/scenario` — inject an outbreak by writing inflated
  case counts, then invalidate cached forecasts

Frontend:
- Forecast panel below the risk queue: history line, forecast band,
  reorder line, stockout marker
- Driver chip beside the title
- Confidence shown on each risk queue row
- "Run outbreak scenario" wired to the demo endpoint

### Acceptance

- [ ] Forecast for a smooth SKU visually tracks its history
- [ ] Forecast for a lumpy SKU does not produce absurd values
- [ ] Firing the outbreak scenario visibly reddens the map within one refresh
- [ ] Every risk row shows a driver string
- [ ] Reset restores the pre-scenario state exactly

### Exit test

Fire the outbreak. Does the risk queue reorder sensibly — do diarrhoeal
and antibiotic lines rise while unrelated drugs stay put? If everything
rises uniformly, the outbreak factor is not drug-specific and needs
fixing.

### Do not

Do not reach for LSTMs or transformers. Sparse per-facility demand is
exactly where they lose to Croston-family methods, and a judge who knows
forecasting will ask. Do not report accuracy metrics anywhere in the UI.

---

## Phase 3 — Optimiser

**Product outcome:** the product stops describing problems and starts
proposing solutions. This is the moment in the demo where people lean in.

### Build

- Surplus/deficit classification per facility-drug: surplus above 60
  days cover, deficit below 15
- Min-cost flow with OR-Tools. Cost function combines transport cost by
  road distance, expiry risk (moving stock that expires soon is worth
  more), and a small penalty per distinct shipment to encourage
  consolidation
- Constraints: cold-chain items only move between cold-chain-capable
  facilities; never strip a source below 30 days cover; respect a max
  transfer radius
- Impact calculation — the before/after breach count. This number is
  the product's headline; compute it honestly by re-running the
  forecast with proposed transfers applied
- `POST /api/plan` returns proposed transfers plus impact
- `POST /api/transfers/approve` writes rows with status, and generates
  notifications for both facilities

Frontend:
- Transfer planner route
- Map with arrows from source to destination
- Table: from, to, item, qty, distance, cost, cover restored
- Impact panel with breach count before and after, cost, expiry avoided
- Approve all / approve selected
- "Requires CMHO sign-off — nothing ships automatically" footer

### Acceptance

- [ ] Plan generates in under 3 seconds
- [ ] No proposed transfer leaves a source facility in deficit
- [ ] Cold-chain constraint holds — verify with a cold-chain drug
- [ ] Before/after numbers are computed, not hardcoded
- [ ] Approving writes transfer rows and they appear in the facility view

### Exit test

Fire the outbreak, generate a plan, and read the transfers aloud. Would
a district officer find each one obviously sensible? If any transfer
looks arbitrary — a long haul when a near facility had stock — the cost
function needs work.

### Do not

Do not call this AI in any UI copy or slide. It is optimisation, and
naming it correctly makes the whole project more credible. Do not
implement auto-approval, even behind a flag.

---

## Phase 4 — PHC app

**Product outcome:** the data stops being magic. A pharmacist
photographs a paper register and it becomes structured stock — offline,
on a cheap phone.

This is the phase that answers the hardest question anyone will ask:
"where does the data come from?"

### Build

- React PWA, separate entry, mobile-first, installable
- Service worker, app shell cached, works with no network
- IndexedDB via Dexie holding local stock, pending mutations, sync queue
- Sync engine: queue mutations offline, replay on reconnect,
  last-write-wins per row with a conflict log. Show pending count in the
  header
- Home: capacity ring, three constraint bars, lowest-cover callout
- Stock tab: list with days of cover and expiry chips, search
- Scan tab — the centrepiece:
  - Camera capture or file picker
  - `POST /api/scan` sends the image to Gemini with a strict prompt
    requesting JSON only
  - **Constrain the output.** Fuzzy-match every extracted drug name
    against the drug master. Never accept a free-text drug name. An
    unmatched name is surfaced as "not recognised", never guessed
  - Per-row confidence; rows below threshold rendered amber with the
    specific uncertain field flagged
  - Nothing writes to stock until the user taps confirm
- Transfers tab: incoming and outgoing, accept/reject

### Acceptance

- [ ] App installs to home screen and launches offline
- [ ] With network disabled: record a dispense, close app, reopen, entry persists
- [ ] On reconnect the queue drains and the server reflects the change
- [ ] Scanning a fixture register photo returns correctly matched drugs
- [ ] A deliberately blurry fixture produces low confidence, not a wrong guess
- [ ] No drug name outside the master can ever be written to stock

### Exit test

Turn on airplane mode. Use the app for two minutes — record dispensing,
browse stock, accept a transfer. Turn networking back on. Everything
should reconcile with no user action and no error toast.

### Do not

Do not let Gemini output reach the database without human confirmation.
Do not build an APK — the PWA is the deliverable, because judges will
not sideload. Do not skip the low-confidence path; it is the most
persuasive part of the scan demo.

---

## Phase 5 — Capacity

**Product outcome:** the product stops being a stock tracker. Beds and
staff enter the model, and the dashboard starts naming the real
bottleneck — which is often not medicine.

### Build

Bed capture, derived rather than typed:
- Admission and discharge events recorded in the PHC app, two taps
- Occupancy computed from events; nobody types an occupancy number
- Saturation forecast — days until full at the current admission rate
- Spillover: when a facility saturates, identify the nearest facility
  with free beds **and raise that facility's forecast demand
  accordingly**. This is the mechanism that ties beds back to medicine

Staff capture, three sources in priority order:
- Read from an existing state attendance system where available
  (stubbed for the demo with a documented adapter interface)
- Shift check-in in the app, four taps
- **Inferred from activity silence** — zero dispensing events from the
  pharmacy counter all day implies no pharmacist. Tamper-resistant,
  because presence can be faked but a day of records cannot
- Critical role logic: map each role to the services it gates. No
  pharmacist means stock cannot be dispensed at all, so
  `medicine_score` for that facility drops to zero regardless of shelf
  contents

CBI unification:
- Compute all three sub-scores, take the minimum, record the label
- Every surface shows the bottleneck label, not just the number

Frontend:
- Beds and Staff tabs on the district dashboard
- Capacity ring and three bars on PHC home
- Risk queue entries can now read "no pharmacist — ₹1.8L stock
  undispensable" alongside stockout rows

### Acceptance

- [ ] Occupancy is never directly editable, only derived from events
- [ ] A facility with full beds raises its neighbour's forecast demand
- [ ] Removing the pharmacist zeroes that facility's medicine score
- [ ] Bottleneck label is correct across a spread of facilities
- [ ] Staff inference correctly flags a facility with no dispensing activity

### Exit test

Find a facility with healthy stock and remove its pharmacist in the
seed. It should immediately appear in the risk queue with a staff
bottleneck, not a stock one. That single behaviour is the phase.

### Do not

Do not build a rostering or HR module. Do not store any individual staff
member's name, ID, or attendance record — role-level counts only. This
is both a privacy requirement and a scope guard.

---

## Phase 6 — Federation

**Product outcome:** the problem statement's "shared predictive
modelling across states" requirement is satisfied, visibly and
provably.

### Build

- Partition the generated data into five simulated state clients with
  deliberately different disease mixes and volumes — non-IID on purpose
- Flower server plus five clients. Model kept small: a shared encoder
  over seasonal and disease features with a per-state head
- **Use FedProx or an equivalent personalisation split, not plain
  FedAvg,** and record why in DECISIONS.md. With genuinely non-IID
  clients, plain averaging degrades. Being able to explain this in one
  sentence separates you from teams who wrote "we used federated
  learning"
- Cold-start transfer: a new district with under 90 days of history
  borrows the seasonal response curve from similar districts, matched on
  climate zone and disease profile, without receiving their data
- Instrumentation: log bytes transferred per round, tensor count, and
  explicit zero counters for patient records, stock rows, and facility
  names
- Write every round to `fl_rounds`; run training offline and let the API
  read results
- Baseline comparison: also train a single-state model so the UI can
  show federated beating it

Frontend:
- Federation panel: five state cards with sample counts and status
- Accuracy-per-round chart with the single-state baseline as a dashed line
- Mono-font transfer log showing the zero counters
- Cold-start callout naming the newest state

### Acceptance

- [ ] Five clients train and aggregate across at least seven rounds
- [ ] Federated curve beats the single-state baseline
- [ ] Transfer log shows real byte counts, not placeholders
- [ ] Cold-start state's forecast is materially better than a
      history-less baseline
- [ ] No raw record crosses a client boundary — verifiable in the code path

### Exit test

Have someone read the transfer log and ask: "could a state's stock data
leak through this?" You should be able to point at the code path and say
no, in one sentence.

### Do not

Do not claim differential privacy unless you have set an epsilon and can
show the utility cost. An unsupported privacy claim is worse than no
claim. Do not run live federated training in the deployed app.

---

## Phase 7 — Trust *(droppable)*

**Product outcome:** the system stops trusting its own inputs blindly —
directly answering the documented weakness of existing systems, which
is data quality rather than software.

### Build

- Benford's law check on quantity distributions per facility
- Physically impossible consumption detection against facility footfall
- Backdated edit detection and suspicious expiry clustering
- Trust score per facility, propagating into forecast confidence
- Append-only hash-chained ledger for stock events — tamper-evident, and
  deliberately not a blockchain
- Data Trust tab: flagged entries with reason, confidence, and action

### Acceptance

- [ ] All three seeded flaw types are detected
- [ ] No more than one false positive across clean facilities
- [ ] Low trust visibly lowers forecast confidence
- [ ] Ledger detects a manually tampered row

### Do not

Do not use the word blockchain anywhere. A hash chain is the honest
description and sounds more competent.

---

## Phase 8 — War room *(droppable)*

**Product outcome:** the system becomes a preparedness tool rather than
a reporting tool — answering "capacity to respond when it matters most."

### Build

- Vectorised simulation over the facility network: injects a surge,
  propagates demand, applies lead times, runs Monte Carlo rollouts
- Scenario builder: condition, surge multiplier, region, start week
- Outputs: fragility ranking, first-to-break list with dates,
  confidence bands
- Counterfactual replay: run a historical outbreak, show what the system
  would have warned and how many stockout-days it would have prevented
- National choropleth by risk

### Acceptance

- [ ] Simulation over 30k synthetic nodes completes in under 10 seconds
- [ ] Higher multipliers produce monotonically worse outcomes
- [ ] Fragility ranking is stable across runs

---

## Phase 9 — Ship

**Product outcome:** the four graded deliverables exist and work.

### Build

**Deploy**
- Cloud Run `asia-south1`, Firebase Hosting, Neon Postgres
- Firebase rewrite proxying `/api/**` to Cloud Run — single origin, no CORS
- Auto-seed on empty DB
- `--min-instances 1` for the judging window only, reverted after
- GCP budget alert set

**README** — judged more than the code. In this order: one-line pitch,
30-second GIF, architecture image, `docker compose up`, demo walkthrough
with exact clicks, tech stack naming Google services, and a table
mapping every problem-statement requirement to a feature.

**Video, 3 minutes**, per `DEMO.md`. Screen recording, burned-in
captions, unlisted.

**Deck, 12 slides.** Requirement-mapping table on slide 2.

### Acceptance

- [ ] Fresh incognito load works with no login in under 3 seconds
- [ ] Outbreak scenario and reset both work on the deployed URL
- [ ] PWA installs from the deployed URL on a real phone
- [ ] A stranger can reproduce the demo from the README alone
- [ ] Every link in the submission resolves

### Exit test

Hand the URL and README to someone outside the team with no
explanation. Can they reach the outbreak-to-transfer-plan moment on
their own? If not, the demo controls are not obvious enough.

---

## Cross-cutting rules

**Every phase ends demoable.** If you cannot show it, the phase is not
done.

**Data model is frozen after Phase 0.** Additive columns are fine;
renames and drops require a HANDOFF.md warning.

**Nothing autonomous ships.** Human approval on every consequential
action, in every phase.

**No patient-level data anywhere, ever.** Facility aggregates only. This
is a hard architectural boundary, not a preference.

**Honesty about simulated data** in the README, deck, and video. Teams
lose more credibility hiding it than admitting it.
