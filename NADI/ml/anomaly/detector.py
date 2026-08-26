import hashlib
import math
from collections import defaultdict
from typing import List, Dict, Any
from datetime import timedelta, datetime

def compute_transaction_hashes(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Computes an append-only hash chain for a list of transactions ordered by occurred_at ASC.
    Updates the transactions in place with `hash` and `prev_hash` fields.
    """
    # Sort transactions by occurred_at, then id to ensure deterministic order
    sorted_txs = sorted(transactions, key=lambda x: (x["occurred_at"], x["id"]))
    
    prev_hash = None
    for tx in sorted_txs:
        # Create a string representation of the core data
        # For a real system we'd serialize deterministically.
        data_str = f"{tx['facility_id']}_{tx['drug_id']}_{tx['batch_no']}_{tx['quantity']}_{tx['type']}_{tx['occurred_at'].isoformat()}_{prev_hash or ''}"
        
        current_hash = hashlib.sha256(data_str.encode('utf-8')).hexdigest()
        
        tx["prev_hash"] = prev_hash
        tx["hash"] = current_hash
        
        prev_hash = current_hash
        
    return sorted_txs

def analyze_benford(transactions: List[Dict[str, Any]]) -> Dict[int, float]:
    """
    Applies Benford's Law to transaction quantities and returns anomaly confidence scores per facility.
    """
    facility_counts = defaultdict(lambda: defaultdict(int))
    facility_totals = defaultdict(int)
    
    for tx in transactions:
        qty = tx.get("quantity", 0)
        if qty > 0:
            first_digit = int(str(qty)[0])
            facility_counts[tx["facility_id"]][first_digit] += 1
            facility_totals[tx["facility_id"]] += 1
            
    # Benford's law expected percentages
    expected = {d: math.log10(1 + 1/d) for d in range(1, 10)}
    
    anomaly_scores = {}
    for fid, counts in facility_counts.items():
        total = facility_totals[fid]
        if total < 50:
            continue  # Not enough data for statistical significance
            
        # Calculate divergence
        divergence = 0
        for d in range(1, 10):
            actual_pct = counts[d] / total
            expected_pct = expected[d]
            divergence += (actual_pct - expected_pct) ** 2
            
        # Empirical threshold: divergence > 0.05 is highly suspicious
        if divergence > 0.05:
            # Scale divergence to a 0-1 confidence
            confidence = min(1.0, divergence * 10)
            if confidence > 0.6:
                anomaly_scores[fid] = confidence
                
    return anomaly_scores

def detect_anomalies(transactions: List[Dict[str, Any]], footfall: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Runs all anomaly rules and returns a list of Anomaly objects.
    """
    anomalies = []
    
    # 1. Backdated edits
    # Rule: recorded_at is > 2 days after occurred_at
    for tx in transactions:
        occurred = tx["occurred_at"]
        recorded = tx["recorded_at"]
        if recorded and occurred:
            diff = recorded - occurred
            if diff > timedelta(days=2):
                confidence = min(1.0, diff.days / 10.0) # More days = higher confidence
                anomalies.append({
                    "facility_id": tx["facility_id"],
                    "drug_id": tx["drug_id"],
                    "rule": "backdated",
                    "confidence": round(confidence, 2),
                    "note": f"Transaction recorded {diff.days} days after it occurred"
                })
                
    # 2. Impossible consumption (rate)
    # Rule: Sum of dispensed qty on a given day > 5 * footfall
    daily_footfall = defaultdict(int)
    for f in footfall:
        key = (f["facility_id"], f["date"])
        daily_footfall[key] += f["patients"]
        
    daily_dispensed = defaultdict(lambda: defaultdict(int))
    for tx in transactions:
        if tx["type"] == "dispense":
            day = tx["occurred_at"].date()
            key = (tx["facility_id"], day)
            daily_dispensed[key][tx["drug_id"]] += tx["quantity"]
            
    for (fid, day), drugs in daily_dispensed.items():
        patients = daily_footfall.get((fid, day), 0)
        # Even if patients is 0, dispensing something might be okay (data delay),
        # but a massive spike is an anomaly.
        for drug_id, qty in drugs.items():
            if patients == 0 and qty > 100:
                 anomalies.append({
                    "facility_id": fid,
                    "drug_id": drug_id,
                    "rule": "impossible_rate",
                    "confidence": 0.95,
                    "note": f"Dispensed {qty} units with 0 recorded patients on {day}"
                })
            elif patients > 0 and qty > patients * 10:
                confidence = min(1.0, (qty / (patients * 10)) / 10)
                if confidence > 0.5:
                    anomalies.append({
                        "facility_id": fid,
                        "drug_id": drug_id,
                        "rule": "impossible_rate",
                        "confidence": round(confidence, 2),
                        "note": f"Dispensed {qty} units to {patients} patients on {day} (impossible ratio)"
                    })
                    
    # 3. Benford's Law
    benford_scores = analyze_benford(transactions)
    for fid, score in benford_scores.items():
        anomalies.append({
            "facility_id": fid,
            "drug_id": None,
            "rule": "benford",
            "confidence": round(score, 2),
            "note": "Quantity distribution violates Benford's law, indicating possible artificial data entry"
        })
        
    return anomalies
