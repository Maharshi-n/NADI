import json

with open("/data/generated/facilities.json") as f:
    facs = json.load(f)
for fc in facs:
    if fc["id"] in [11, 16]:
        print("id:", fc["id"], "name:", fc["name"], "beds:", fc.get("beds_total"), "type:", fc.get("type"))

with open("/data/generated/staff_daily.json") as f:
    staff = json.load(f)
for s in staff:
    if s["facility_id"] in [11, 16]:
        print("staff:", s)
