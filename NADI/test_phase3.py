#!/usr/bin/env python3
"""Phase 3 API Acceptance Test — Transfer Optimiser."""
import urllib.request
import json
import time

base = "http://localhost:8000/api"

print("=== Test 1: POST /api/plan (Generate Redistribution Plan) ===")
start_time = time.time()
body = json.dumps({"district": "Dhar", "maxRadiusKm": 65.0}).encode()
req = urllib.request.Request(f"{base}/plan", data=body, headers={"Content-Type": "application/json"})

with urllib.request.urlopen(req) as res:
    plan_data = json.loads(res.read())
    elapsed = time.time() - start_time
    
    print(f"  Plan ID: {plan_data['planId']}")
    print(f"  Generation Time: {elapsed:.2f}s (Acceptance bar: < 3.0s)")
    assert elapsed < 3.0, "Plan generation took too long!"
    
    impact = plan_data["impact"]
    print(f"  Breaches Before: {impact['breachesBefore']}")
    print(f"  Breaches After:  {impact['breachesAfter']}")
    print(f"  Total Cost:      Rs. {impact['totalCostPaise'] / 100:.2f}")
    print(f"  Expiry Avoided:  Rs. {impact['expiryAvoidedPaise'] / 100:.2f}")
    
    assert impact["breachesBefore"] >= impact["breachesAfter"], "Optimizer did not reduce or maintain breaches!"
    
    transfers = plan_data["transfers"]
    print(f"  Proposed Transfers: {len(transfers)}")
    assert len(transfers) > 0, "Expected at least 1 proposed transfer from seed data shortages!"
    
    # Inspect first few transfers
    for t in transfers[:3]:
        print(f"    * {t['fromName']} --({t['quantity']} {t['unit']} {t['drugName']})--> {t['toName']} ({t['distanceKm']} km, +{t['coverRestoredDays']}d cover)")
    print()

print("=== Test 2: Constraint Verifications ===")
# Fetch facilities to verify cold chain
fac_req = urllib.request.Request(f"{base}/facilities?district=Dhar&limit=100")
with urllib.request.urlopen(fac_req) as res:
    facs = {f["id"]: f for f in json.loads(res.read())["items"]}

for t in transfers:
    assert t["fromFacilityId"] != t["toFacilityId"], "Source and destination must be distinct!"
    assert t["distanceKm"] <= 65.0, f"Distance {t['distanceKm']} exceeds 65km max radius!"
    if t.get("isColdChain"):
        src_cold = facs[t["fromFacilityId"]]["coldChainCapable"]
        dst_cold = facs[t["toFacilityId"]]["coldChainCapable"]
        assert src_cold and dst_cold, f"Cold chain violation: src={src_cold}, dst={dst_cold}"

print("  [OK] All source != destination constraints hold")
print("  [OK] All distance <= 65km constraints hold")
print("  [OK] Cold-chain capability strictly verified for all cold chain items")
print()

print("=== Test 3: POST /api/transfers/approve ===")
approve_body = json.dumps({
    "planId": plan_data["planId"],
    "transfers": transfers[:5]  # approve first 5
}).encode()
approve_req = urllib.request.Request(f"{base}/transfers/approve", data=approve_body, headers={"Content-Type": "application/json"})

with urllib.request.urlopen(approve_req) as res:
    approve_data = json.loads(res.read())
    print(f"  Status: {approve_data['status']}")
    print(f"  Approved Count: {approve_data['approvedCount']}")
    assert approve_data["approvedCount"] == min(5, len(transfers))
    print()

print("=== Test 4: GET /api/transfers ===")
list_req = urllib.request.Request(f"{base}/transfers?limit=10")
with urllib.request.urlopen(list_req) as res:
    trans_list = json.loads(res.read())
    print(f"  Total recorded transfers: {trans_list['total']}")
    assert trans_list["total"] >= approve_data["approvedCount"]
    for item in trans_list["items"][:3]:
        print(f"    * ID #{item['id']} [Plan {item['planId']}]: {item['fromName']} -> {item['toName']} ({item['quantity']} units of {item['drugName']}) [{item['status']}]")
    print()

print("All Phase 3 backend tests passed successfully!")
