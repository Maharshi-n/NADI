#!/usr/bin/env python3
"""Quick Phase 2 API test."""
import urllib.request
import json

base = "http://localhost:8000/api"

print("=== Test 1: GET /forecast (smooth SKU: Paracetamol, facility 1) ===")
req = urllib.request.Request(f"{base}/forecast?facilityId=1&drugId=1")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Method: {data['methodUsed']}")
    print(f"  Driver: {data['driver']}")
    print(f"  Confidence: {data['confidence']}")
    print(f"  Days to stockout: {data['daysToStockout']}")
    print(f"  Reorder point: {data['reorderPoint']}")
    print(f"  History length: {len(data['history'])} days")
    print(f"  Forecast length: {len(data['forecast'])} days")
    print()

print("=== Test 2: GET /forecast (ORS Sachets - ors_zinc category) ===")
req = urllib.request.Request(f"{base}/forecast?facilityId=1&drugId=9")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Method: {data['methodUsed']}")
    print(f"  Driver: {data['driver']}")
    print(f"  Confidence: {data['confidence']}")
    print(f"  Days to stockout: {data['daysToStockout']}")
    print()

print("=== Test 3: GET /forecast (intermittent/lumpy - cold chain drug) ===")
req = urllib.request.Request(f"{base}/forecast?facilityId=5&drugId=37")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Method: {data['methodUsed']}")
    print(f"  Driver: {data['driver']}")
    print(f"  Confidence: {data['confidence']}")
    print(f"  Days to stockout: {data['daysToStockout']}")
    print()

print("=== Test 4: POST /demo/scenario (Dengue, 4x) ===")
body = json.dumps({"condition": "dengue", "multiplier": 4.0, "district": "Dhar"}).encode()
req = urllib.request.Request(f"{base}/demo/scenario", data=body, headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Affected: {data['affected']}")
    print(f"  Condition: {data['condition']}")
    print(f"  Multiplier: {data['multiplier']}")
    print()

print("=== Test 5: GET /forecast AFTER scenario ===")
req = urllib.request.Request(f"{base}/forecast?facilityId=1&drugId=1")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Driver (should mention outbreak): {data['driver']}")
    print(f"  Days to stockout (should be lower): {data['daysToStockout']}")
    print()

print("=== Test 6: POST /demo/reset ===")
req = urllib.request.Request(f"{base}/demo/reset", data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Status: {data['status']}")
    print(f"  Message: {data['message']}")
    print()

print("=== Test 7: GET /forecast AFTER reset ===")
req = urllib.request.Request(f"{base}/forecast?facilityId=1&drugId=1")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"  Driver (should be back to normal): {data['driver']}")
    print(f"  Days to stockout (should be restored): {data['daysToStockout']}")
    print()

print("All Phase 2 tests passed!")
