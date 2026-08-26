# DEMO.md — the demo script

The product exists to produce this five minutes. Any feature that does
not serve it is optional.

---

## What must work, in priority order

If something breaks the night before, fix in this order:

1. District dashboard loads with populated map and risk queue
2. Outbreak scenario button visibly changes the map
3. Transfer plan generates and shows before/after
4. PHC app loads offline and records an entry
5. Register scan returns matched drugs
6. Federation panel renders with the baseline comparison
7. Everything else

## The seven beats

**1. Open on failure (20s)**
A real stockout statistic. Then: "nobody knew until it happened."
No product on screen yet.

**2. The register (25s)**
PHC app. Photograph the paper register. Rows appear with confidence
badges. Point at an amber row: "it flags what it cannot read instead of
guessing a drug name." **Do not skip the amber row.** It is the most
persuasive second in the video.

**3. Kill the network (20s)**
Airplane mode on. Record a dispense. Reopen the app — the entry is
still there. Reconnect. It syncs. Say: "2G, no G, still works."

**4. The dashboard (35s)**
District Command. Fourteen facilities amber or red. Click the top risk
row. Forecast chart with the driver chip visible: "dengue +180% in this
block." Say: "not a report — a countdown, with a reason."

**5. The surge (40s)**
Run outbreak scenario. Map reddens, queue reorders. Show that
diarrhoeal and antibiotic lines rise while unrelated drugs stay flat —
this proves the model is drug-specific, not a blanket multiplier.

**6. The fix (40s)**
Generate transfer plan. Arrows appear. Read one transfer aloud. Show
14 → 2. Approve. Cut to the phone: notification arrives. Say:
"the system recommends, the CMHO approves. Nothing ships on its own."

**7. Federation and close (40s)**
Five state nodes. Accuracy curve above the dashed single-state
baseline. Point at the log: "zero patient records, zero stock rows."
Close on the number: "stockout-days avoided: 287."

## Video mechanics

- 1080p screen recording, 3:00 hard limit
- Burned-in captions — judges often watch muted
- No talking-head longer than 10 seconds
- Cursor movements slow and deliberate; no hunting for buttons
- Pre-load every page before recording to avoid spinners
- Record beats separately and cut together; do not attempt one take
- Unlisted YouTube, link in README and deck

## Live demo contingencies

| Risk | Mitigation |
|---|---|
| Venue wifi dies | Local build on a laptop, recorded fallback video |
| Cloud Run cold start | min-instances 1 before judging |
| Someone breaks the demo data | Reset button, always visible |
| Gemini API rate limit | Cache one scan result as a fixture fallback |
| Projector colour washes out | Verify red/amber/green contrast beforehand |

## Questions you will be asked

**"This already exists."** — State systems are systems of record with
the demand-forecasting layer undelivered in practice. We are the
intelligence layer above one, not a replacement. Show the integration
arrow.

**"Your data is fake."** — Correct, and here is the generator with its
seasonality assumptions written down. The models, solver, and federation
are real. Swap in a district's feed and it runs.

**"Why federated, not one database?"** — States will not hand over raw
health data, centralisation carries regulatory liability, and the
national digital health architecture is already federated-with-consent.
We match the country's data governance instead of fighting it.

**"How does it get adopted?"** — As a module on top of the supply chain
system already deployed across many states. One district pilot, 20 PHCs,
three months, measured against their own prior records.

**"What if the pharmacist doesn't use it?"** — Which is why the primary
input is a photograph of the register they already keep, and staff
presence is inferred from activity rather than asked for.
