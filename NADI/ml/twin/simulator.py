"""
Phase 8 — War Room Twin Simulator
Vectorised simulation of demand propagation and stockout risks.
"""
import math
from typing import List, Dict, Any
from sqlalchemy import text

async def run_simulation(db, district: str, condition: str, multiplier: float) -> Dict[str, Any]:
    """
    Run a simplified vectorised rollout.
    - Fetches baseline burn_rate per facility-drug for essential drugs
    - Fetches current stock
    - Applies condition-specific multiplier to relevant drugs
    - Computes new days_to_stockout
    - Outputs fragility ranking, first-to-break list, and counterfactual stockout days prevented
    """
    
    condition = condition.lower()
    affected_categories = []
    if "dengue" in condition or "malaria" in condition:
        affected_categories = ["antipyretic", "iv_fluids", "antibiotic"]
    elif "diarrhoea" in condition or "cholera" in condition:
        affected_categories = ["ors", "zinc", "antibiotic"]
    else:
        affected_categories = ["antibiotic", "analgesic"] # Fallback

    # 1. Fetch facility-drug baseline
    query = text("""
        WITH burn AS (
            SELECT
                t.facility_id,
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.type = 'dispense'
              AND t.occurred_at >= ((SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days')
            GROUP BY t.facility_id, t.drug_id
        ),
        current_stock AS (
            SELECT
                s.facility_id,
                s.drug_id,
                SUM(s.quantity) AS total_qty
            FROM stock s
            GROUP BY s.facility_id, s.drug_id
        )
        SELECT
            f.id AS facility_id,
            f.name AS facility_name,
            d.id AS drug_id,
            d.category AS drug_category,
            COALESCE(b.burn_rate, 0) AS burn_rate,
            COALESCE(cs.total_qty, 0) AS current_stock
        FROM facilities f
        CROSS JOIN drugs d
        LEFT JOIN current_stock cs ON cs.facility_id = f.id AND cs.drug_id = d.id
        LEFT JOIN burn b ON b.facility_id = f.id AND b.drug_id = d.id
        WHERE d.is_essential = true
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
    """)
    
    result = await db.execute(query, {"district": district})
    rows = result.mappings().all()
    
    # Process results
    facility_risks = {}
    total_stockout_days_prevented = 0
    
    for row in rows:
        fid = row["facility_id"]
        fname = row["facility_name"]
        cat = row["drug_category"]
        burn_rate = row["burn_rate"]
        qty = row["current_stock"]
        
        if fid not in facility_risks:
            facility_risks[fid] = {
                "facility_name": fname,
                "worst_days": 9999,
                "risk_score": 0.0
            }
            
        # Baseline days of cover
        baseline_doc = 9999
        if burn_rate > 0:
            baseline_doc = qty / burn_rate
            
        # Simulated days of cover
        sim_burn_rate = burn_rate
        if cat and cat.lower() in affected_categories:
            sim_burn_rate = burn_rate * multiplier
            
        sim_doc = 9999
        if sim_burn_rate > 0:
            sim_doc = qty / sim_burn_rate
            
        if sim_doc < facility_risks[fid]["worst_days"]:
            facility_risks[fid]["worst_days"] = sim_doc
            
        # Compute fragility (risk score is inversely proportional to worst days)
        if sim_doc < 30:
            facility_risks[fid]["risk_score"] += (30 - sim_doc)
            
        # Counterfactual: if sim_doc < 15, we assume we prevented (15 - sim_doc) stockout days by simulating
        if sim_doc < 15:
            total_stockout_days_prevented += int(15 - sim_doc)
            
    # Compile outputs
    fragility_list = []
    first_to_break = []
    
    for fid, data in facility_risks.items():
        score = data["risk_score"]
        wd = int(data["worst_days"]) if data["worst_days"] < 9999 else None
        
        item = {
            "facility_id": fid,
            "facility_name": data["facility_name"],
            "risk_score": round(score, 1),
            "days_to_stockout": wd
        }
        fragility_list.append(item)
        
        if wd is not None and wd < 15:
            first_to_break.append(item)
            
    # Sort
    fragility_list.sort(key=lambda x: x["risk_score"], reverse=True)
    first_to_break.sort(key=lambda x: (x["days_to_stockout"] or 9999))
    
    return {
        "fragility_ranking": fragility_list,
        "first_to_break": first_to_break[:10], # top 10
        "counterfactual_impact": {
            "stockout_days_prevented": total_stockout_days_prevented
        }
    }
