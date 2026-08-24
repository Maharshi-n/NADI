# DATA_MODEL.md — schema

Create every table in Phase 0, including ones not used until Phase 6.
Schema churn mid-build breaks parallel sessions.

Additive columns are fine anytime. Renames and drops need a loud
HANDOFF.md warning.

---

## Core

**facilities** — PHCs, CHCs, warehouses
```
id, name, type(phc|chc|dh|warehouse), district, block, state,
lat, lng, hfr_code(nullable), beds_total, cold_chain_capable(bool),
population_served, created_at
```

**drugs** — the master. Nothing outside this table can enter stock.
```
id, name, salt, strength, form, unit(tab|cap|sachet|vial|ml),
category, is_essential(bool), is_cold_chain(bool),
shelf_life_months, atc_class(nullable)
```

**stock** — current holdings, one row per facility/drug/batch
```
id, facility_id, drug_id, batch_no, quantity, expiry_date,
last_updated, trust_score(default 1.0)
```

**transactions** — the event log everything is derived from
```
id, facility_id, drug_id, batch_no, quantity,
type(receive|dispense|transfer_in|transfer_out|adjust|expire),
occurred_at, recorded_at, recorded_by_role, source(app|scan|sync|seed),
prev_hash, hash
```
`occurred_at` vs `recorded_at` is how backdated-edit detection works in
Phase 7. `prev_hash`/`hash` form the append-only chain.

**transfers**
```
id, from_facility_id, to_facility_id, drug_id, quantity,
status(proposed|approved|dispatched|received|rejected),
proposed_at, approved_at, approved_by_role,
distance_km, cost_paise, plan_id
```

## Capacity (Phase 5)

**bed_events** — occupancy is derived, never typed
```
id, facility_id, type(admit|discharge), occurred_at, recorded_at
```

**staff_daily** — role counts only. Never individual identities.
```
id, facility_id, date, role(doctor|pharmacist|nurse|anm|lab),
required, present, source(system|checkin|inferred)
```

**footfall**
```
id, facility_id, date, patients, referrals_out, referrals_in
```

## Signals

**disease_signal**
```
id, district, condition, week_start, case_count, source
```

**season_factor** — lookup, not learned
```
id, drug_category, month, factor
```

## Derived / cache

**forecasts**
```
id, facility_id, drug_id, computed_at, predicted_daily_rate,
days_to_stockout, confidence, driver_label, method_used
```
`method_used` records which model class was chosen — needed to justify
the SKU-classification design.

**capacity_scores**
```
id, facility_id, computed_at, medicine_score, bed_score, staff_score,
cbi, bottleneck(medicine|beds|staff)
```

## Federation (Phase 6)

**fl_rounds**
```
id, round_no, started_at, completed_at, aggregation_method,
clients_participating, bytes_transferred, tensor_count,
global_accuracy, baseline_accuracy,
patient_records_transferred(always 0),
stock_rows_transferred(always 0)
```
The zero columns exist so the UI reads them from the database rather
than printing a hardcoded string. That distinction matters if a judge
asks.

**fl_clients**
```
id, state_name, sample_count, last_round, model_version, status
```

## Trust (Phase 7)

**anomalies**
```
id, facility_id, drug_id(nullable), detected_at,
rule(benford|impossible_rate|backdated|expiry_cluster),
confidence, resolved(bool), note
```

---

## Indexes worth creating in Phase 0

```sql
CREATE INDEX ON transactions (facility_id, drug_id, occurred_at DESC);
CREATE INDEX ON stock (facility_id, drug_id);
CREATE INDEX ON forecasts (facility_id, days_to_stockout);
CREATE INDEX ON disease_signal (district, week_start DESC);
```
The first one is load-bearing — burn rate queries hit it constantly.

---

## Generator requirements

`data/generator.py` must produce, at minimum:

- 22 PHCs, 3 CHCs, 1 warehouse, coordinates inside one real district
- 40 drugs, 25 essential, mixed units, 4 cold-chain
- 180 days of dispensing per facility/drug pair
- Weekly dips at weekends
- Seasonality: vector-borne Jun–Sep, respiratory Nov–Jan, ORS with heat
- ~40% of pairs intermittent or lumpy with many zero days
- Current stock reverse-engineered so ~6 facilities are amber and ~3 red
  at seed time
- Three deliberate data flaws for Phase 7: under-reporting facilities,
  backdated edits, an impossible consumption spike
- One facility with no pharmacist, for the Phase 5 exit test

Determinism: seed the RNG and expose `--seed`. Two people running the
generator must get identical data or bug reports become meaningless.
