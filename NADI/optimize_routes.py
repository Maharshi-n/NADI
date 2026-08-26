import re

with open("apps/api/routes.py", "r", encoding="utf-8") as f:
    content = f.read()

# We want to replace everything from `# Get all affected facility-drug pairs`
# to the end of the `for pair in pairs:` loop, right before `return ScenarioResponse(...)`

pattern = r"(# Get all affected facility-drug pairs\s+pairs_query = text.*?)(?=\s+return ScenarioResponse\()"

optimized_code = """# Get all stock values upfront
        stock_query = text(f\"\"\"
            SELECT s.facility_id, s.drug_id, SUM(s.quantity) AS current_stock,
                   d.category, f.district AS fac_district
            FROM stock s
            JOIN drugs d ON d.id = s.drug_id
            JOIN facilities f ON f.id = s.facility_id
            WHERE f.district = CAST(:district AS text)
              AND d.category IN ({placeholders})
              AND s.quantity > 0
            GROUP BY s.facility_id, s.drug_id, d.category, f.district
        \"\"\")
        stock_result = await db.execute(stock_query, {"district": district})
        pairs = stock_result.mappings().all()
        
        # Fetch shared data once
        sf_query = text("SELECT drug_category, month, factor FROM season_factor")
        sf_result = await db.execute(sf_query)
        season_factors = [dict(r) for r in sf_result.mappings().all()]
        
        ds_query = text(\"\"\"
            SELECT condition, week_start, case_count
            FROM disease_signal WHERE district = CAST(:district AS text)
            ORDER BY week_start DESC LIMIT 40
        \"\"\")
        ds_result = await db.execute(ds_query, {"district": district})
        disease_signals = [dict(r) for r in ds_result.mappings().all()]
        
        current_month = dt_module.date.today().month
        
        # Get all dispense history in one query
        hist_q = text(f\"\"\"
            SELECT t.facility_id, t.drug_id, DATE(t.occurred_at) AS date, SUM(t.quantity) AS quantity
            FROM transactions t
            JOIN facilities f ON f.id = t.facility_id
            JOIN drugs d ON d.id = t.drug_id
            WHERE f.district = CAST(:district AS text)
              AND d.category IN ({placeholders})
              AND t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '180 days'
              )
            GROUP BY t.facility_id, t.drug_id, DATE(t.occurred_at)
            ORDER BY DATE(t.occurred_at) ASC
        \"\"\")
        hist_result = await db.execute(hist_q, {"district": district})
        
        from collections import defaultdict
        history_map = defaultdict(list)
        for row in hist_result.mappings().all():
            history_map[(row["facility_id"], row["drug_id"])].append(row)
            
        upsert_params = []
        
        for pair in pairs:
            fid = pair["facility_id"]
            did = pair["drug_id"]
            cat = pair["category"]
            stock_val = pair["current_stock"]
            
            hist_rows = history_map.get((fid, did), [])
            if not hist_rows:
                continue
            
            all_dates = [row["date"] for row in hist_rows]
            min_date = min(all_dates)
            max_date = max(all_dates)
            date_qty_map = {row["date"]: int(row["quantity"]) for row in hist_rows}
            
            daily_series = []
            current = min_date
            while current <= max_date:
                daily_series.append({"date": current.isoformat(), "quantity": date_qty_map.get(current, 0)})
                current += timedelta(days=1)
            
            fc_result = forecast_facility_drug(
                daily_dispensing=daily_series,
                current_stock=int(stock_val),
                drug_category=cat,
                current_month=current_month,
                season_factors=season_factors,
                disease_signals=disease_signals,
                horizon=30,
                lead_time_days=7,
            )
            
            upsert_params.append({
                "fid": fid, "did": did,
                "rate": fc_result["predicted_daily_rate"],
                "dts": fc_result["days_to_stockout"],
                "conf": fc_result["confidence"],
                "driver": fc_result["driver"],
                "method": fc_result["method_used"],
            })
            
        if upsert_params:
            upsert_q = text(\"\"\"
                INSERT INTO forecasts (facility_id, drug_id, predicted_daily_rate,
                    days_to_stockout, confidence, driver_label, method_used)
                VALUES (CAST(:fid AS integer), CAST(:did AS integer), CAST(:rate AS numeric), CAST(:dts AS integer), CAST(:conf AS numeric), CAST(:driver AS text), CAST(:method AS text))
                ON CONFLICT (facility_id, drug_id) DO UPDATE SET
                    predicted_daily_rate = EXCLUDED.predicted_daily_rate,
                    days_to_stockout = EXCLUDED.days_to_stockout,
                    confidence = EXCLUDED.confidence,
                    driver_label = EXCLUDED.driver_label,
                    method_used = EXCLUDED.method_used
            \"\"\")
            try:
                await db.execute(upsert_q, upsert_params)
            except Exception as e:
                print(f"UPSERT ERROR: {e}")"""

new_content = re.sub(pattern, optimized_code, content, flags=re.DOTALL)

with open("apps/api/routes.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print("Optimized routes.py successfully.")
