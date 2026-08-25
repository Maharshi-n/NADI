import urllib.request
import json

base_url = "http://localhost:8000/api"

print("--- Test 1: Fetching forecast for a facility-drug pair ---")
req = urllib.request.Request(f"{base_url}/forecast?facilityId=1&drugId=1")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"Method used: {data.get('methodUsed')}")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Driver: {data.get('driver')}")
    print(f"Days to stockout: {data.get('daysToStockout')}")
    print(f"Reorder point: {data.get('reorderPoint')}")
    print(f"Forecast length: {len(data.get('forecast', []))} days")
    print()

print("--- Test 2: Firing an outbreak scenario (Dengue, 4x) ---")
req = urllib.request.Request(
    f"{base_url}/demo/scenario",
    data=json.dumps({"condition": "dengue", "multiplier": 4.0, "district": "Dhar"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"Scenario Response: {data.get('message')}")
    print(f"Affected Facilities: {data.get('affectedFacilities')}")
    print()

print("--- Test 3: Fetching forecast again to check driver change ---")
# Finding a dengue drug, let's say drugId=1 (antimalarial might be affected? Dengue mapping: antimalarial, analgesic, antibiotic)
# Let's check drugId 12 (ORS) or something, but we just check /risk endpoint to see top risks
req = urllib.request.Request(f"{base_url}/risk?limit=5")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    for item in data.get('items', []):
        print(f"Facility {item['facilityId']}, Drug {item['drugName']} -> Driver: {item['driver']}, Confidence: {item['confidence']}, Days to stockout: {item['daysToStockout']}")
    print()

print("--- Test 4: Resetting the scenario ---")
req = urllib.request.Request(f"{base_url}/demo/reset", method="POST")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"Reset Response: {data.get('message')}")
