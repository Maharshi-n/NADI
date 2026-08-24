# API.md — endpoint contracts

Update whenever an endpoint is added or changed. Frontend sessions read
this instead of the backend source.

Base: `/api`. All responses camelCase. Errors:
`{"error":{"code":"...","message":"..."}}` with a real HTTP status.
List endpoints take `limit`/`offset`, return `{"items":[],"total":n}`.

---

## Phase 1

**GET /facilities** — `?district=&type=`
```json
{"items":[{"id":1,"name":"PHC Dhamnod","type":"phc","lat":22.2,"lng":75.4,
"status":"critical","worstDaysOfCover":9,"bedsTotal":6}],"total":26}
```

**GET /facilities/{id}** — detail plus current stock summary

**GET /stock** — `?facilityId=&essentialOnly=`
```json
{"items":[{"drugId":12,"name":"ORS sachets","quantity":240,"unit":"sachet",
"burnRate":21.8,"daysOfCover":11,"expiryDate":"2027-03-01","status":"critical"}]}
```

**GET /risk** — `?district=&limit=`  The ranked queue.
```json
{"items":[{"facilityId":1,"facilityName":"PHC Dhamnod","drugId":12,
"drugName":"ORS sachets","daysToStockout":9,"confidence":0.82,
"driver":"Dengue cases +180% in this block","bottleneck":"medicine"}]}
```

**GET /kpis** — `?district=`
```json
{"facilitiesAtRisk":14,"projectedStockoutDays":312,
"expiryAtRiskPaise":420000,"fillRate":0.87}
```

## Phase 2

**GET /forecast** — `?facilityId=&drugId=`
```json
{"history":[{"date":"2026-06-01","quantity":18}],
"forecast":[{"date":"2026-08-25","predicted":24,"lower":18,"upper":31}],
"reorderPoint":120,"stockoutDate":"2026-09-02","daysToStockout":9,
"confidence":0.82,"driver":"Dengue cases +180% in this block",
"methodUsed":"croston_sba"}
```

**POST /demo/scenario**
```json
{"condition":"dengue","multiplier":3,"district":"Dhar","startWeek":34}
```
Writes inflated case counts, invalidates forecast cache. Returns
affected facility count.

**POST /demo/reset** — restores seed state exactly.

## Phase 3

**POST /plan** — `{"district":"Dhar"}`
```json
{"planId":"pl_88","transfers":[{"fromFacilityId":4,"fromName":"PHC Bagdi",
"toFacilityId":1,"toName":"PHC Dhamnod","drugId":12,"drugName":"ORS sachets",
"quantity":400,"distanceKm":22,"costPaise":34000,"coverRestoredDays":18,
"expirySavedPaise":210000}],
"impact":{"breachesBefore":14,"breachesAfter":2,
"totalCostPaise":184000,"expiryAvoidedPaise":630000}}
```

**POST /transfers/approve** — `{"planId":"pl_88","transferIds":[1,2]}`
Writes rows, notifies both facilities.

**GET /transfers** — `?facilityId=&status=`

## Phase 4

**POST /scan** — multipart image
```json
{"rows":[{"drugId":12,"matchedName":"ORS sachets","rawText":"O.R.S sachet",
"batchNo":"B-4417","quantity":240,"expiryDate":"2027-03-01",
"confidence":0.97,"uncertainFields":[]},
{"drugId":null,"matchedName":null,"rawText":"Doxycyclin 100",
"confidence":0.61,"uncertainFields":["batchNo"]}]}
```
`drugId: null` means unmatched — the client must never write it.
Nothing persists until `/scan/confirm`.

**POST /scan/confirm** — confirmed rows only, writes stock + transactions.

**POST /sync** — offline queue replay
```json
{"mutations":[{"clientId":"m_1","type":"dispense","facilityId":1,
"drugId":12,"quantity":8,"occurredAt":"2026-08-24T09:12:00Z"}]}
```
Returns per-mutation `applied` / `conflict` with server state.

## Phase 5

**POST /bed-events** — `{"facilityId":1,"type":"admit"}`
**GET /capacity** — `?facilityId=`
```json
{"medicineScore":0.82,"bedScore":0.60,"staffScore":0.90,"cbi":0.60,
"bottleneck":"beds","daysToSaturation":6,
"spilloverTo":{"facilityId":7,"name":"PHC Bagdi"}}
```
**POST /staff-checkin** — role counts only, never identities.

## Phase 6

**GET /fl/rounds**
```json
{"items":[{"roundNo":7,"aggregationMethod":"fedprox","clients":5,
"bytesTransferred":2201600,"tensorCount":4,"globalAccuracy":0.86,
"baselineAccuracy":0.71,"patientRecordsTransferred":0,
"stockRowsTransferred":0}]}
```
**GET /fl/clients** — the five state cards.

## Phase 7

**GET /anomalies** — `?facilityId=&resolved=`

## Phase 8

**POST /simulate**
```json
{"condition":"dengue","multiplier":3,"region":"MP","weeks":8,"runs":1000}
```
Returns fragility ranking and first-to-break list with dates.
