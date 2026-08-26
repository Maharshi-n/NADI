import re

with open("apps/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

pattern = r"(# Phase 5: inject capacity bottleneck items \(staff/bed\).*?)(?=\s+# ---------------------------------------------------------------------------)"

optimized_code = """# Phase 5: inject capacity bottleneck items (staff/bed)
    capacity_q = text(\"\"\"
        SELECT cs.facility_id, f.name AS facility_name,
               cs.staff_score, cs.bed_score, cs.medicine_score, cs.cbi, cs.bottleneck
        FROM capacity_scores cs
        JOIN facilities f ON f.id = cs.facility_id
        WHERE cs.cbi <= 0.5
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
        ORDER BY cs.cbi ASC
    \"\"\")
    try:
        cap_res = await db.execute(capacity_q, {"district": district})
        cap_rows = cap_res.mappings().all()

        if cap_rows:
            fids = tuple(set(cr["facility_id"] for cr in cap_rows))

            # Batch fetch staff
            staff_q = text(\"\"\"
                SELECT facility_id, role, present, required, date
                FROM staff_daily
                WHERE facility_id = ANY(:fids)
                ORDER BY facility_id, date DESC
            \"\"\")
            staff_res = await db.execute(staff_q, {"fids": list(fids)})
            staff_map = {}
            for r in staff_res.mappings().all():
                fid = r["facility_id"]
                if fid not in staff_map:
                    staff_map[fid] = []
                staff_map[fid].append(r)

            # Batch fetch dispenses
            dispense_q = text(\"\"\"
                SELECT facility_id, COUNT(*) as cnt
                FROM transactions
                WHERE type = 'dispense'
                  AND occurred_at >= ((SELECT MAX(occurred_at) FROM transactions) - INTERVAL '1 day')
                  AND facility_id = ANY(:fids)
                GROUP BY facility_id
            \"\"\")
            dispense_res = await db.execute(dispense_q, {"fids": list(fids)})
            dispense_map = {r["facility_id"]: r["cnt"] for r in dispense_res.mappings().all()}

            # Batch fetch stock
            stock_q = text(\"\"\"
                SELECT facility_id, COALESCE(SUM(quantity), 0) AS total_stock
                FROM stock 
                WHERE facility_id = ANY(:fids)
                GROUP BY facility_id
            \"\"\")
            stock_res = await db.execute(stock_q, {"fids": list(fids)})
            stock_map = {r["facility_id"]: r["total_stock"] for r in stock_res.mappings().all()}

            for cr in cap_rows:
                fid = cr["facility_id"]
                
                # Check staff bottleneck
                if cr["staff_score"] <= 0.5 or cr["bottleneck"] == "staff":
                    staff_rows = staff_map.get(fid, [])
                    missing_roles = []
                    seen = set()
                    for sr in staff_rows:
                        if sr["role"] not in seen:
                            seen.add(sr["role"])
                            if sr["present"] == 0:
                                missing_roles.append(sr["role"])
                    
                    disp_count = dispense_map.get(fid, 0)
                    if disp_count == 0 and "pharmacist" not in missing_roles:
                        missing_roles.append("pharmacist")

                    total_stock = stock_map.get(fid, 0)

                    if "pharmacist" in missing_roles:
                        driver = f"no pharmacist — {total_stock:,} units stock undispensable"
                    else:
                        driver = f"missing: {', '.join(missing_roles)}" if missing_roles else "staffing critical"

                    items.insert(0, RiskItem(
                        facility_id=fid,
                        facility_name=cr["facility_name"],
                        drug_id=None,
                        drug_name=None,
                        days_to_stockout=0,
                        confidence=1.0,
                        driver=driver,
                        bottleneck="staff",
                        status="critical",
                    ))
                    
                # Check beds bottleneck
                if cr["bed_score"] <= 0.5 or cr["bottleneck"] == "beds":
                    driver = f"bed occupancy critical — score {round(cr['bed_score'] * 100)}%"
                    items.insert(0, RiskItem(
                        facility_id=fid,
                        facility_name=cr["facility_name"],
                        drug_id=None,
                        drug_name=None,
                        days_to_stockout=0,
                        confidence=1.0,
                        driver=driver,
                        bottleneck="beds",
                        status="critical",
                    ))
                    
    except Exception as e:
        print(f"Capacity risk queue error: {e}")
        
    return RiskListResponse(
        items=items,
        total=total + len(items)
    )
"""

new_content = re.sub(pattern, optimized_code, content, flags=re.DOTALL)

with open("apps/api/routes.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Optimized get_risk_queue successfully.")
