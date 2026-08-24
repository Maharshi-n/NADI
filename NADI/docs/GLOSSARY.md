# GLOSSARY.md — domain vocabulary

Use these exact terms. If something is missing, add it here rather than
inventing a synonym in code.

## Health system

| Term | Meaning |
|---|---|
| **PHC** | Primary Health Centre. Rural facility, ~30,000 population, small bed count |
| **CHC** | Community Health Centre. Block level, above PHCs, has specialists |
| **Sub-centre / HWC** | Smallest unit below a PHC, staffed by an ANM |
| **DH** | District Hospital |
| **MO** | Medical Officer — the doctor in charge of a PHC |
| **BMO** | Block Medical Officer — oversees PHCs in a block |
| **CMHO** | Chief Medical and Health Officer — district head. **Our primary dashboard user** |
| **ANM** | Auxiliary Nurse Midwife — sub-centre staff |
| **ASHA** | Community health worker, village level |
| **NHM** | National Health Mission — the programme funding this layer |
| **District Health Society** | District governance body; Collector presides, CMHO is secretary |
| **State medical services corporation** | State body that procures and warehouses drugs |
| **District Drug Warehouse** | Where district stock sits before going to facilities |
| **EDL** | Essential Drug List — the drugs a facility is required to stock |

## Product terms — use exactly

| Term | Meaning |
|---|---|
| **Burn rate** | Average daily dispensing over the last 30 days |
| **Days of cover** | Current stock ÷ burn rate. The core number |
| **Days to stockout** | Current stock ÷ *predicted* rate. Forward-looking |
| **CBI** | Capacity Bottleneck Index — min(medicine, beds, staff) |
| **Bottleneck** | Which of the three was the minimum. Always shown |
| **Driver** | The factor that moved a forecast most, as a human string |
| **Surplus / deficit** | Above 60 days cover / below 15 days cover |
| **Spillover** | Demand shifted to a neighbour when a facility saturates |
| **Trust score** | Confidence that a facility's reported numbers are real |
| **Transfer plan** | A set of proposed movements plus its before/after impact |
| **Fill rate** | Share of demand met from stock on hand |
| **Stockout-days** | Facility-days with an essential drug at zero. **Our headline metric** |

## Status thresholds — shared constants, never re-declared

```
CRITICAL  days_of_cover < 15
WARNING   15 <= days_of_cover < 30
HEALTHY   days_of_cover >= 30
SURPLUS   days_of_cover > 60
```

## Words we do not use

| Avoid | Use instead | Why |
|---|---|---|
| AI (for the optimiser) | optimiser, solver | It is min-cost flow |
| blockchain | hash-chained ledger | Accurate and less hype |
| patient | facility, footfall | We never store patients |
| accuracy | fill rate, stockout-days avoided | Officers buy outcomes |
| real-time | near-real-time | Honest about sync latency |
| replace | integrate above | Our go-to-market position |
