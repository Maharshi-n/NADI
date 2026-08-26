"""
NADI Transfer Optimizer Engine — OR-Tools Min-Cost Flow Solver.

ADR-006: Named as an optimization solver, not "AI".
ADR-003: Proposes transfers for human CMHO approval; never executes autonomously.

Core Rules & Constraints (per PHASES.md and CONTEXT.md):
- Surplus: days of cover > 60
- Deficit: days of cover < 15
- Source retention: NEVER strip a source facility below 30 days cover
- Cold-chain constraint: cold-chain drugs only move between cold-chain-capable facilities
- Max transfer radius: intra-district max 65 km
- Cost function: transport distance cost + expiry risk avoidance bonus + consolidation
- Impact: honest before/after breach count calculated by re-evaluating stock levels
"""

import math
import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from ortools.linear_solver import pywraplp


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance in kilometers between two GPS coordinates."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(r * c, 1)


def classify_cover(
    current_stock: int,
    daily_rate: float,
) -> Tuple[str, float]:
    """
    Classify stock cover into status and days of cover.
    - Deficit: < 15 days
    - Warning: 15 - 30 days
    - Adequate: 30 - 60 days
    - Surplus: > 60 days
    """
    if daily_rate <= 0:
        if current_stock > 0:
            return "surplus", 999.0
        return "adequate", 999.0

    days = current_stock / daily_rate
    if days < 15.0:
        return "deficit", round(days, 1)
    elif days < 30.0:
        return "warning", round(days, 1)
    elif days > 60.0:
        return "surplus", round(days, 1)
    else:
        return "adequate", round(days, 1)


def optimize_transfers(
    facilities: List[Dict[str, Any]],
    drugs: List[Dict[str, Any]],
    stock_records: List[Dict[str, Any]],
    burn_rates: Dict[Tuple[int, int], float],
    max_radius_km: float = 65.0,
    cost_per_km_paise: int = 1500,  # ₹15/km
    base_unit_value_paise: int = 400,  # ₹4/unit average baseline
) -> Dict[str, Any]:
    """
    Solve intra-district stock redistribution using OR-Tools Linear Programming / Min-Cost Flow.

    facilities: list of dicts {id, name, type, lat, lng, cold_chain_capable, district}
    drugs: list of dicts {id, name, unit, category, is_essential, is_cold_chain, shelf_life_months}
    stock_records: list of dicts {facility_id, drug_id, quantity, expiry_date}
    burn_rates: dict mapping (facility_id, drug_id) -> daily_rate (predicted or 30-day burn)

    Returns dict matching API.md /plan contract.
    """
    fac_map = {f["id"]: f for f in facilities}
    drug_map = {d["id"]: d for d in drugs}

    # Aggregate current stock & nearest expiry per (facility_id, drug_id)
    current_stock: Dict[Tuple[int, int], int] = {}
    nearest_expiry: Dict[Tuple[int, int], Optional[date]] = {}

    for s in stock_records:
        key = (s["facility_id"], s["drug_id"])
        qty = int(s.get("quantity", 0))
        current_stock[key] = current_stock.get(key, 0) + qty

        exp = s.get("expiry_date")
        if isinstance(exp, str):
            exp = date.fromisoformat(exp)
        if exp:
            prev_exp = nearest_expiry.get(key)
            if prev_exp is None or exp < prev_exp:
                nearest_expiry[key] = exp

    # 1. Calculate Breaches Before Optimization
    breaches_before = 0
    facility_drug_status: Dict[Tuple[int, int], Dict[str, Any]] = {}

    for fid, f in fac_map.items():
        for did, d in drug_map.items():
            key = (fid, did)
            stock_qty = current_stock.get(key, 0)
            rate = burn_rates.get(key, 0.0)

            status, days_cover = classify_cover(stock_qty, rate)
            facility_drug_status[key] = {
                "stock": stock_qty,
                "rate": rate,
                "status": status,
                "days_cover": days_cover,
            }

            # Count deficit breaches (critical < 15 days with active burn)
            if status == "deficit" and rate > 0:
                breaches_before += 1

    # 2. Identify Sources and Destinations per Drug
    proposed_transfers: List[Dict[str, Any]] = []
    virtual_stock = dict(current_stock)
    total_cost_paise = 0
    total_expiry_avoided_paise = 0

    today = date.today()

    for did, drug in drug_map.items():
        is_cold_chain = bool(drug.get("is_cold_chain", False))

        sources: List[Dict[str, Any]] = []
        destinations: List[Dict[str, Any]] = []

        for fid, fac in fac_map.items():
            key = (fid, did)
            state = facility_drug_status[key]
            stock_qty = state["stock"]
            rate = state["rate"]

            # Cold chain check for facility
            fac_cold_capable = bool(fac.get("cold_chain_capable", False))
            if is_cold_chain and not fac_cold_capable:
                continue

            if state["status"] == "surplus" and stock_qty > 0:
                # Source retention rule: leave at least 30 days cover at source!
                min_retained = math.ceil(rate * 30.0) if rate > 0 else 0
                max_surplus = max(0, stock_qty - min_retained)

                if max_surplus > 10:  # meaningful surplus threshold
                    exp_date = nearest_expiry.get(key)
                    months_to_expiry = 24
                    if exp_date:
                        days_diff = (exp_date - today).days
                        months_to_expiry = max(1, days_diff // 30)

                    sources.append({
                        "facility_id": fid,
                        "facility": fac,
                        "available_qty": max_surplus,
                        "rate": rate,
                        "months_to_expiry": months_to_expiry,
                    })

            elif state["status"] == "deficit" and rate > 0:
                # Target: restore to 45 days cover
                target_stock = math.ceil(rate * 45.0)
                needed_qty = max(0, target_stock - stock_qty)

                if needed_qty > 0:
                    destinations.append({
                        "facility_id": fid,
                        "facility": fac,
                        "needed_qty": needed_qty,
                        "rate": rate,
                    })

        if not sources or not destinations:
            continue

        # 3. Solve OR-Tools Min-Cost Flow for this Drug
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            # Fallback to CBC or GLOP if SCIP is not available
            solver = pywraplp.Solver.CreateSolver("CBC") or pywraplp.Solver.CreateSolver("GLOP")

        if not solver:
            continue

        # Decision variables: flow[i, j] = units transferred from source i to destination j
        flow_vars: Dict[Tuple[int, int], Any] = {}

        for s_idx, src in enumerate(sources):
            src_fac = src["facility"]
            for d_idx, dst in enumerate(destinations):
                dst_fac = dst["facility"]

                dist = haversine_distance(
                    src_fac["lat"], src_fac["lng"],
                    dst_fac["lat"], dst_fac["lng"]
                )

                # Distance constraint
                if dist > max_radius_km:
                    continue

                var_name = f"flow_{src['facility_id']}_{dst['facility_id']}"
                max_flow = min(src["available_qty"], dst["needed_qty"])
                flow_vars[(s_idx, d_idx)] = solver.IntVar(0, max_flow, var_name)

        if not flow_vars:
            continue

        # Constraint: Do not exceed available surplus at each source
        for s_idx, src in enumerate(sources):
            src_flows = [flow_vars[(s_idx, d_idx)] for d_idx in range(len(destinations)) if (s_idx, d_idx) in flow_vars]
            if src_flows:
                solver.Add(solver.Sum(src_flows) <= src["available_qty"])

        # Constraint: Do not exceed needed deficit at each destination
        for d_idx, dst in enumerate(destinations):
            dst_flows = [flow_vars[(s_idx, d_idx)] for s_idx in range(len(sources)) if (s_idx, d_idx) in flow_vars]
            if dst_flows:
                solver.Add(solver.Sum(dst_flows) <= dst["needed_qty"])

        # Objective: Maximize deficit coverage while minimizing distance and avoiding expiry
        objective = solver.Objective()

        for (s_idx, d_idx), var in flow_vars.items():
            src = sources[s_idx]
            dst = destinations[d_idx]
            dist = haversine_distance(
                src["facility"]["lat"], src["facility"]["lng"],
                dst["facility"]["lat"], dst["facility"]["lng"]
            )

            # Expiry risk bonus: if source stock expires in < 12 months, moving it is advantageous
            expiry_bonus = max(0, (12 - src["months_to_expiry"]) * 5)

            # Per-unit weight: high benefit for filling deficit - distance penalty + expiry bonus
            unit_weight = 1000 - (dist * 5) + expiry_bonus
            objective.SetCoefficient(var, float(unit_weight))

        objective.SetMaximization()
        status = solver.Solve()

        if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            for (s_idx, d_idx), var in flow_vars.items():
                qty = int(round(var.solution_value()))
                if qty <= 0:
                    continue

                src = sources[s_idx]
                dst = destinations[d_idx]
                dist = haversine_distance(
                    src["facility"]["lat"], src["facility"]["lng"],
                    dst["facility"]["lat"], dst["facility"]["lng"]
                )

                # Cost in paise: base ₹15/km + batch handling
                transfer_cost_paise = int(round(dist * cost_per_km_paise + 5000))

                # Cover restored at destination
                dst_rate = dst["rate"]
                cover_restored = round(qty / dst_rate, 1) if dst_rate > 0 else 30.0

                # Expiry saved calculation:
                # If near expiry (< 12 months) and destination has high burn rate
                expiry_saved_paise = 0
                if src["months_to_expiry"] <= 12:
                    unit_price = base_unit_value_paise * (2 if drug.get("is_essential") else 1)
                    expiry_saved_paise = int(qty * unit_price)

                # Update virtual stock
                virtual_stock[(src["facility_id"], did)] -= qty
                virtual_stock[(dst["facility_id"], did)] = virtual_stock.get((dst["facility_id"], did), 0) + qty

                total_cost_paise += transfer_cost_paise
                total_expiry_avoided_paise += expiry_saved_paise

                proposed_transfers.append({
                    "fromFacilityId": src["facility_id"],
                    "fromName": src["facility"]["name"],
                    "toFacilityId": dst["facility_id"],
                    "toName": dst["facility"]["name"],
                    "drugId": did,
                    "drugName": drug["name"],
                    "unit": drug.get("unit", "units"),
                    "isColdChain": is_cold_chain,
                    "quantity": qty,
                    "distanceKm": dist,
                    "costPaise": transfer_cost_paise,
                    "coverRestoredDays": cover_restored,
                    "expirySavedPaise": expiry_saved_paise,
                })

    # 4. Calculate Breaches After Optimization (Honest Re-evaluation)
    breaches_after = 0
    for fid, f in fac_map.items():
        for did, d in drug_map.items():
            key = (fid, did)
            post_stock = virtual_stock.get(key, 0)
            rate = burn_rates.get(key, 0.0)

            post_status, _ = classify_cover(post_stock, rate)
            if post_status == "deficit" and rate > 0:
                breaches_after += 1

    plan_id = f"pl_{uuid.uuid4().hex[:8]}"

    return {
        "planId": plan_id,
        "transfers": proposed_transfers,
        "impact": {
            "breachesBefore": breaches_before,
            "breachesAfter": breaches_after,
            "totalCostPaise": total_cost_paise,
            "expiryAvoidedPaise": total_expiry_avoided_paise,
        },
    }
