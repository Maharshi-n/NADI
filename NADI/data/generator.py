"""
NADI synthetic district generator.
Produces JSON files in data/generated/ for seed.py to load.

Usage: python data/generator.py [--seed 42] [--output data/generated]
"""

import argparse, json, math, os, random
from datetime import date, timedelta, datetime

# ── District: Dhar, Madhya Pradesh ──────────────────────────────────────────

DISTRICT = "Dhar"
STATE = "Madhya Pradesh"
BLOCKS = ["Dhar", "Badnawar", "Dharampuri", "Manawar", "Sardarpur", "Kukshi", "Gandhwani"]

# Real lat/lng bounding box for Dhar district
LAT_MIN, LAT_MAX = 22.0, 22.8
LNG_MIN, LNG_MAX = 74.8, 75.8

# ── Facility templates ──────────────────────────────────────────────────────

FACILITY_NAMES_PHC = [
    "PHC Dhamnod", "PHC Badnawar", "PHC Manawar", "PHC Sardarpur",
    "PHC Kukshi", "PHC Gandhwani", "PHC Tirla", "PHC Nalchha",
    "PHC Bakaner", "PHC Dharampuri", "PHC Umarban", "PHC Singhana",
    "PHC Rajgarh", "PHC Amjhera", "PHC Pithampur", "PHC Nisarpur",
    "PHC Bagdi", "PHC Dahi", "PHC Bagh", "PHC Tanda", "PHC Khalghat", "PHC Raoti",
]
FACILITY_NAMES_CHC = ["CHC Dhar", "CHC Badnawar", "CHC Manawar"]
FACILITY_NAMES_WH = ["District Drug Warehouse Dhar"]

# ── Drug master ─────────────────────────────────────────────────────────────

DRUGS = [
    # (name, salt, strength, form, unit, category, essential, cold_chain, shelf_life)
    ("Paracetamol 500mg", "Paracetamol", "500mg", "tablet", "tab", "analgesic", True, False, 36),
    ("Amoxicillin 250mg", "Amoxicillin", "250mg", "capsule", "cap", "antibiotic", True, False, 24),
    ("Amoxicillin 500mg", "Amoxicillin", "500mg", "capsule", "cap", "antibiotic", True, False, 24),
    ("Metronidazole 400mg", "Metronidazole", "400mg", "tablet", "tab", "antibiotic", True, False, 36),
    ("Ciprofloxacin 500mg", "Ciprofloxacin", "500mg", "tablet", "tab", "antibiotic", True, False, 24),
    ("Doxycycline 100mg", "Doxycycline", "100mg", "capsule", "cap", "antibiotic", True, False, 24),
    ("Azithromycin 500mg", "Azithromycin", "500mg", "tablet", "tab", "antibiotic", True, False, 24),
    ("Cotrimoxazole 480mg", "Sulfamethoxazole+Trimethoprim", "480mg", "tablet", "tab", "antibiotic", True, False, 36),
    ("ORS Sachets", "ORS", "21g", "sachet", "sachet", "ors_zinc", True, False, 36),
    ("Zinc Dispersible 20mg", "Zinc Sulphate", "20mg", "tablet", "tab", "ors_zinc", True, False, 36),
    ("Iron Folic Acid", "Ferrous Sulphate+Folic Acid", "100mg+0.5mg", "tablet", "tab", "nutritional", True, False, 24),
    ("Albendazole 400mg", "Albendazole", "400mg", "tablet", "tab", "anthelmintic", True, False, 36),
    ("Chloroquine 250mg", "Chloroquine", "250mg", "tablet", "tab", "antimalarial", True, False, 36),
    ("Artesunate+Sulfadoxine", "Artesunate+SP", "50mg+500mg", "tablet", "tab", "antimalarial", True, False, 24),
    ("Diclofenac 50mg", "Diclofenac Sodium", "50mg", "tablet", "tab", "analgesic", True, False, 36),
    ("Omeprazole 20mg", "Omeprazole", "20mg", "capsule", "cap", "gastrointestinal", True, False, 24),
    ("Ranitidine 150mg", "Ranitidine", "150mg", "tablet", "tab", "gastrointestinal", True, False, 36),
    ("Metformin 500mg", "Metformin", "500mg", "tablet", "tab", "antidiabetic", True, False, 36),
    ("Amlodipine 5mg", "Amlodipine", "5mg", "tablet", "tab", "cardiovascular", True, False, 36),
    ("Atenolol 50mg", "Atenolol", "50mg", "tablet", "tab", "cardiovascular", True, False, 36),
    ("Enalapril 5mg", "Enalapril", "5mg", "tablet", "tab", "cardiovascular", True, False, 36),
    ("Salbutamol 4mg", "Salbutamol", "4mg", "tablet", "tab", "respiratory", True, False, 24),
    ("Cetirizine 10mg", "Cetirizine", "10mg", "tablet", "tab", "antihistamine", True, False, 36),
    ("Ibuprofen 400mg", "Ibuprofen", "400mg", "tablet", "tab", "analgesic", True, False, 36),
    ("Povidone Iodine 5%", "Povidone Iodine", "5%", "solution", "ml", "antiseptic", True, False, 24),
    # Non-essential drugs
    ("Pantoprazole 40mg", "Pantoprazole", "40mg", "tablet", "tab", "gastrointestinal", False, False, 24),
    ("Loperamide 2mg", "Loperamide", "2mg", "capsule", "cap", "gastrointestinal", False, False, 36),
    ("Domperidone 10mg", "Domperidone", "10mg", "tablet", "tab", "gastrointestinal", False, False, 24),
    ("Tramadol 50mg", "Tramadol", "50mg", "capsule", "cap", "analgesic", False, False, 24),
    ("Montelukast 10mg", "Montelukast", "10mg", "tablet", "tab", "respiratory", False, False, 24),
    ("Cough Syrup", "Dextromethorphan", "15mg/5ml", "syrup", "ml", "respiratory", False, False, 18),
    ("Vitamin B Complex", "B-Complex", "mixed", "tablet", "tab", "nutritional", False, False, 36),
    ("Calcium+D3", "Calcium Carbonate+Cholecalciferol", "500mg+250IU", "tablet", "tab", "nutritional", False, False, 36),
    ("Mupirocin Ointment", "Mupirocin", "2%", "ointment", "ml", "antiseptic", False, False, 24),
    ("Clotrimazole Cream", "Clotrimazole", "1%", "cream", "ml", "antifungal", False, False, 24),
    ("Betamethasone Cream", "Betamethasone", "0.1%", "cream", "ml", "dermatological", False, False, 24),
    # Cold-chain drugs
    ("Oxytocin Injection", "Oxytocin", "5IU/ml", "injection", "vial", "obstetric", False, True, 18),
    ("Insulin Regular", "Insulin", "40IU/ml", "injection", "vial", "antidiabetic", False, True, 12),
    ("TT Vaccine", "Tetanus Toxoid", "0.5ml", "injection", "vial", "vaccine", False, True, 24),
    ("Measles Vaccine", "Measles", "0.5ml", "injection", "vial", "vaccine", False, True, 12),
]

# ── Seasonality factors by category and month ───────────────────────────────
# month 1-12. Vector-borne rise Jun-Sep, respiratory Nov-Jan, ORS summer+diarrhoeal

def _season_factors():
    """Returns {category: {month: factor}}."""
    base = {cat: {m: 1.0 for m in range(1, 13)} for cat in set(d[5] for d in DRUGS)}
    # Vector-borne: antimalarial peaks Jun-Sep
    for cat in ["antimalarial"]:
        for m in [6, 7, 8, 9]:
            base[cat][m] = 2.0 + (0.5 if m in [7, 8] else 0.0)
    # Respiratory: Nov-Jan
    for cat in ["respiratory"]:
        for m in [11, 12, 1]:
            base[cat][m] = 1.8
    # ORS/zinc: summer Apr-Jun + diarrhoeal signal
    for cat in ["ors_zinc"]:
        for m in [4, 5, 6]:
            base[cat][m] = 2.0
        for m in [7, 8, 9]:
            base[cat][m] = 1.5
    # Antibiotic: mild monsoon rise
    for cat in ["antibiotic"]:
        for m in [7, 8, 9]:
            base[cat][m] = 1.3
    # Antihistamine: seasonal allergy Mar-May
    for cat in ["antihistamine"]:
        for m in [3, 4, 5]:
            base[cat][m] = 1.5
    return base

SEASON_FACTORS = _season_factors()

# ── Demand classification ───────────────────────────────────────────────────

def classify_demand(values):
    """Classify as smooth/erratic/intermittent/lumpy per CV and ADI."""
    non_zero = [v for v in values if v > 0]
    if len(non_zero) < 3:
        return "lumpy"
    cv = (sum((x - sum(non_zero)/len(non_zero))**2 for x in non_zero) / len(non_zero))**0.5 / (sum(non_zero)/len(non_zero)) if sum(non_zero) > 0 else 0
    zero_pct = 1 - len(non_zero) / max(len(values), 1)
    adi = len(values) / max(len(non_zero), 1)
    if cv < 0.49 and adi < 1.32:
        return "smooth"
    elif cv >= 0.49 and adi < 1.32:
        return "erratic"
    elif cv < 0.49 and adi >= 1.32:
        return "intermittent"
    else:
        return "lumpy"

# ── Generator ───────────────────────────────────────────────────────────────

def generate(seed_val=42):
    rng = random.Random(seed_val)
    today = date(2026, 8, 24)
    start_date = today - timedelta(days=179)

    # 1. Facilities
    facilities = []
    fid = 0
    # Assign blocks round-robin
    for i, name in enumerate(FACILITY_NAMES_PHC):
        fid += 1
        block = BLOCKS[i % len(BLOCKS)]
        facilities.append({
            "id": fid, "name": name, "type": "phc",
            "district": DISTRICT, "block": block, "state": STATE,
            "lat": round(rng.uniform(LAT_MIN, LAT_MAX), 4),
            "lng": round(rng.uniform(LNG_MIN, LNG_MAX), 4),
            "hfr_code": None,
            "beds_total": rng.choice([4, 6, 6, 6, 8, 10]),
            "cold_chain_capable": rng.random() < 0.6,
            "population_served": rng.randint(20000, 40000),
        })
    for i, name in enumerate(FACILITY_NAMES_CHC):
        fid += 1
        facilities.append({
            "id": fid, "name": name, "type": "chc",
            "district": DISTRICT, "block": BLOCKS[i], "state": STATE,
            "lat": round(rng.uniform(LAT_MIN, LAT_MAX), 4),
            "lng": round(rng.uniform(LNG_MIN, LNG_MAX), 4),
            "hfr_code": None,
            "beds_total": rng.choice([20, 30, 30]),
            "cold_chain_capable": True,
            "population_served": rng.randint(80000, 120000),
        })
    for name in FACILITY_NAMES_WH:
        fid += 1
        facilities.append({
            "id": fid, "name": name, "type": "warehouse",
            "district": DISTRICT, "block": "Dhar", "state": STATE,
            "lat": 22.5977, "lng": 75.3025,
            "hfr_code": None,
            "beds_total": 0, "cold_chain_capable": True,
            "population_served": 0,
        })

    # 2. Drugs
    drugs = []
    for i, d in enumerate(DRUGS):
        drugs.append({
            "id": i + 1, "name": d[0], "salt": d[1], "strength": d[2],
            "form": d[3], "unit": d[4], "category": d[5],
            "is_essential": d[6], "is_cold_chain": d[7],
            "shelf_life_months": d[8], "atc_class": None,
        })

    # 3. Deliberate flaws: pick facility indices
    under_reporters = [f["id"] for f in facilities[:3]]  # first 3 PHCs under-report
    backdaters = [f["id"] for f in facilities[5:7]]       # 2 with backdated edits
    spike_facility = facilities[10]["id"]                  # 1 impossible spike
    no_pharmacist_facility = facilities[15]["id"]          # 1 with no pharmacist

    # 4. Determine which facility-drug pairs are intermittent (~40%)
    intermittent_pairs = set()
    for f in facilities:
        if f["type"] == "warehouse":
            continue
        for d in drugs:
            if rng.random() < 0.40:
                intermittent_pairs.add((f["id"], d["id"]))

    # 5. Generate 180 days of dispensing transactions
    transactions = []
    # Track cumulative dispensing for stock reverse-engineering
    total_dispensed = {}  # (fac_id, drug_id) -> total

    for f in facilities:
        if f["type"] == "warehouse":
            continue
        pop_scale = f["population_served"] / 30000.0
        for d in drugs:
            pair_key = (f["id"], d["id"])
            is_intermittent = pair_key in intermittent_pairs

            # Base daily demand
            if d["is_essential"]:
                base_demand = rng.uniform(3, 18) * pop_scale
            else:
                base_demand = rng.uniform(1, 8) * pop_scale

            # Cold chain drugs: lower volume
            if d["is_cold_chain"]:
                base_demand *= 0.3

            cumulative = 0
            for day_offset in range(180):
                current_date = start_date + timedelta(days=day_offset)
                m = current_date.month
                dow = current_date.weekday()  # 0=Mon, 6=Sun

                # Weekend dip
                if dow == 5:
                    dow_factor = 0.6
                elif dow == 6:
                    dow_factor = 0.3
                else:
                    dow_factor = 1.0

                # Seasonality
                cat = d["category"]
                season_f = SEASON_FACTORS.get(cat, {}).get(m, 1.0)

                # Intermittent: many zero days
                if is_intermittent:
                    if rng.random() < 0.55:  # 55% chance of zero
                        qty = 0
                    else:
                        raw = base_demand * dow_factor * season_f * rng.uniform(0.5, 2.5)
                        qty = max(0, round(raw))
                else:
                    raw = base_demand * dow_factor * season_f * rng.gauss(1.0, 0.15)
                    qty = max(0, round(raw))

                # Under-reporters: reduce by 40-60%
                if f["id"] in under_reporters and qty > 0:
                    qty = max(1, round(qty * rng.uniform(0.4, 0.6)))

                # Impossible spike: one day, one drug, 50x normal
                if f["id"] == spike_facility and d["id"] == 1 and day_offset == 90:
                    qty = round(base_demand * 50)

                if qty > 0:
                    tx_date = datetime(current_date.year, current_date.month, current_date.day, 10, 0)
                    rec_date = tx_date

                    # Backdated edits: some entries recorded 3-7 days later
                    if f["id"] in backdaters and rng.random() < 0.15:
                        rec_date = tx_date + timedelta(days=rng.randint(3, 7))

                    transactions.append({
                        "facility_id": f["id"], "drug_id": d["id"],
                        "batch_no": f"B-{f['id']:02d}-{d['id']:02d}",
                        "quantity": qty, "type": "dispense",
                        "occurred_at": tx_date.isoformat(),
                        "recorded_at": rec_date.isoformat(),
                        "recorded_by_role": "pharmacist",
                        "source": "seed", "prev_hash": None, "hash": None,
                    })
                    cumulative += qty

            total_dispensed[pair_key] = cumulative

    # 6. Reverse-engineer stock levels
    # Target: ~6 amber (15-30 days), ~3 red (<15 days), rest healthy
    stock = []
    # Sort facilities by id, assign status targets
    non_wh = [f for f in facilities if f["type"] != "warehouse"]
    red_ids = set(f["id"] for f in non_wh[:3])      # 3 red
    amber_ids = set(f["id"] for f in non_wh[3:9])   # 6 amber
    # rest are healthy

    for f in facilities:
        for d in drugs:
            pair_key = (f["id"], d["id"])
            total = total_dispensed.get(pair_key, 0)
            burn_rate = total / 180.0 if total > 0 else 0.5

            if f["type"] == "warehouse":
                days_cover = rng.uniform(90, 180)
            elif f["id"] in red_ids:
                days_cover = rng.uniform(5, 14)
            elif f["id"] in amber_ids:
                days_cover = rng.uniform(16, 29)
            else:
                days_cover = rng.uniform(35, 75)

            qty = max(0, round(burn_rate * days_cover))
            exp_months = rng.randint(3, d["shelf_life_months"])
            exp_date = today + timedelta(days=exp_months * 30)

            stock.append({
                "facility_id": f["id"], "drug_id": d["id"],
                "batch_no": f"B-{f['id']:02d}-{d['id']:02d}",
                "quantity": qty,
                "expiry_date": exp_date.isoformat(),
                "trust_score": 0.6 if f["id"] in under_reporters else 1.0,
            })

    # 7. Receive transactions (initial stock load at day 0)
    for s in stock:
        transactions.append({
            "facility_id": s["facility_id"], "drug_id": s["drug_id"],
            "batch_no": s["batch_no"], "quantity": s["quantity"] + total_dispensed.get((s["facility_id"], s["drug_id"]), 0),
            "type": "receive", "occurred_at": datetime(start_date.year, start_date.month, start_date.day).isoformat(),
            "recorded_at": datetime(start_date.year, start_date.month, start_date.day).isoformat(),
            "recorded_by_role": "system", "source": "seed",
            "prev_hash": None, "hash": None,
        })

    # 8. Staff daily (today snapshot)
    staff_daily = []
    roles = ["doctor", "pharmacist", "nurse", "anm", "lab"]
    for f in facilities:
        if f["type"] == "warehouse":
            continue
        for role in roles:
            required = 2 if f["type"] == "chc" else 1
            # No pharmacist for the designated facility
            if f["id"] == no_pharmacist_facility and role == "pharmacist":
                present = 0
            else:
                present = required if rng.random() > 0.1 else max(0, required - 1)
            staff_daily.append({
                "facility_id": f["id"], "date": today.isoformat(),
                "role": role, "required": required, "present": present,
                "source": "system",
            })

    # 9. Bed events (last 30 days of admits/discharges)
    bed_events = []
    for f in facilities:
        if f["type"] == "warehouse" or f["beds_total"] == 0:
            continue
        occupancy = 0
        for day_offset in range(30):
            d = today - timedelta(days=29 - day_offset)
            # Admissions
            n_admit = rng.randint(0, max(1, f["beds_total"] // 3))
            for _ in range(n_admit):
                if occupancy < f["beds_total"]:
                    bed_events.append({
                        "facility_id": f["id"], "type": "admit",
                        "occurred_at": datetime(d.year, d.month, d.day, rng.randint(8, 18), 0).isoformat(),
                    })
                    occupancy += 1
            # Discharges
            n_discharge = rng.randint(0, max(1, occupancy))
            for _ in range(n_discharge):
                if occupancy > 0:
                    bed_events.append({
                        "facility_id": f["id"], "type": "discharge",
                        "occurred_at": datetime(d.year, d.month, d.day, rng.randint(9, 17), 0).isoformat(),
                    })
                    occupancy -= 1

    # 10. Footfall (last 30 days)
    footfall = []
    for f in facilities:
        if f["type"] == "warehouse":
            continue
        base_patients = f["population_served"] / 500
        for day_offset in range(30):
            d = today - timedelta(days=29 - day_offset)
            dow = d.weekday()
            dow_f = 0.3 if dow == 6 else (0.6 if dow == 5 else 1.0)
            patients = max(0, round(base_patients * dow_f * rng.gauss(1.0, 0.2)))
            footfall.append({
                "facility_id": f["id"], "date": d.isoformat(),
                "patients": patients,
                "referrals_out": rng.randint(0, max(1, patients // 20)),
                "referrals_in": rng.randint(0, max(1, patients // 30)),
            })

    # 11. Disease signals (26 weeks)
    disease_signal = []
    conditions = ["dengue", "malaria", "diarrhoeal", "respiratory_infection", "tuberculosis"]
    for condition in conditions:
        for week in range(26):
            ws = today - timedelta(weeks=25 - week)
            ws = ws - timedelta(days=ws.weekday())  # Monday
            m = ws.month
            base_cases = 20
            if condition == "dengue" and m in [7, 8, 9]:
                base_cases = 80
            elif condition == "malaria" and m in [6, 7, 8, 9]:
                base_cases = 60
            elif condition == "diarrhoeal" and m in [4, 5, 6]:
                base_cases = 70
            elif condition == "respiratory_infection" and m in [11, 12, 1]:
                base_cases = 65
            cases = max(0, round(base_cases * rng.gauss(1.0, 0.25)))
            disease_signal.append({
                "district": DISTRICT, "condition": condition,
                "week_start": ws.isoformat(), "case_count": cases,
                "source": "IDSP",
            })

    # 12. Season factor lookup
    season_factor = []
    for cat, months in SEASON_FACTORS.items():
        for m, f in months.items():
            season_factor.append({"drug_category": cat, "month": m, "factor": f})

    # 13. Metadata
    metadata = {
        "seed": seed_val, "generated_at": datetime.now().isoformat(),
        "district": DISTRICT, "state": STATE,
        "facilities_count": len(facilities),
        "drugs_count": len(drugs),
        "transactions_count": len(transactions),
        "stock_count": len(stock),
        "deliberate_flaws": {
            "under_reporters": under_reporters,
            "backdaters": backdaters,
            "spike_facility": spike_facility,
            "no_pharmacist_facility": no_pharmacist_facility,
        },
    }

    return {
        "metadata": metadata,
        "facilities": facilities,
        "drugs": drugs,
        "stock": stock,
        "transactions": transactions,
        "staff_daily": staff_daily,
        "bed_events": bed_events,
        "footfall": footfall,
        "disease_signal": disease_signal,
        "season_factor": season_factor,
    }


def save(data, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for key, value in data.items():
        path = os.path.join(output_dir, f"{key}.json")
        with open(path, "w") as f:
            json.dump(value, f, indent=2, default=str)
        count = len(value) if isinstance(value, list) else 1
        print(f"  {key}: {count} {'rows' if isinstance(value, list) else 'object'} -> {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic NADI district data")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for determinism")
    parser.add_argument("--output", default=os.path.join(os.path.dirname(__file__), "generated"),
                        help="Output directory")
    args = parser.parse_args()

    print(f"Generating with seed={args.seed}...")
    data = generate(args.seed)
    save(data, args.output)
    meta = data["metadata"]
    print(f"\nDone. {meta['facilities_count']} facilities, {meta['drugs_count']} drugs, "
          f"{meta['transactions_count']} transactions, {meta['stock_count']} stock rows.")
    print(f"Flaws: under-reporters={meta['deliberate_flaws']['under_reporters']}, "
          f"backdaters={meta['deliberate_flaws']['backdaters']}, "
          f"spike={meta['deliberate_flaws']['spike_facility']}, "
          f"no pharmacist={meta['deliberate_flaws']['no_pharmacist_facility']}")
