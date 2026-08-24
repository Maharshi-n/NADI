# PROJECT.md — the north star

Stable document. Changes here require a DECISIONS.md entry explaining why.

---

## One line

NADI predicts which Primary Health Centres will run out of capacity —
medicines, beds, or staff — and proposes transfers from nearby facilities
that already have surplus.

## The problem we are solving

Public health facilities in India run out of medicine and nobody at
district level knows until a patient is turned away. The existing state
supply-chain systems record what was procured and issued, but the demand
forecasting layer was never delivered in practice. Stock data is entered
late, entered wrong, or not entered at all, because entry is a manual
burden on staff who are already stretched.

The result: shortages are discovered after they happen, and the response
is a fresh procurement cycle measured in weeks — when the medicine
needed often already exists twenty kilometres away at a facility with
surplus.

## The insight the whole product rests on

A facility's real ability to treat patients is not its stock level. It is
the **minimum** of three things:

- Does it have the medicine?
- Does it have a bed?
- Does it have the staff member who can dispense or treat?

A PHC with full shelves and no pharmacist is functionally out of
medicine. A PHC whose beds are full sends patients to the next PHC —
which means that facility's medicine demand is about to rise.

So beds and staff are not three separate dashboards bolted together.
They are the reason the medicine forecast is right or wrong. We collapse
them into one number per facility and name the binding constraint.

## Who this is for

**Buyer:** a State Health Department — the State Health Society under
NHM, or the state medical services corporation that handles drug
procurement.

**Pilot customer:** one district's CMHO office, roughly 20 PHCs.

**Daily users:**

| Role | Device | Does what |
|---|---|---|
| PHC pharmacist / storekeeper | Mobile | Records stock, beds, staff; accepts transfers |
| Medical Officer (PHC in-charge) | Mobile | Approves outgoing transfers, sees own facility |
| Block Medical Officer | Web | Watches 15–20 PHCs |
| CMHO / District Officer | Web | **Primary dashboard user.** Approves transfer plans |
| State officer | Web | Cross-district movement, outbreak scenarios |

**Beneficiary, not user:** the patient. They never see this product.

## Non-goals — do not build these

- Any citizen or patient-facing app
- Private pharmacy inventory, e-pharmacy, or medicine ordering by consumers
- Automated purchasing from suppliers without human approval
- Autonomous shipping — the system recommends, a human always approves
- Prescription-to-patient matching or any clinical decision support
- Substitution recommendations beyond identical salt, strength and form
- Real-time vehicle or courier tracking
- Replacing the state's existing supply chain system — we integrate above it

Each of these has been considered and rejected. If a session proposes
one, the answer is no unless PROJECT.md changes first.

## Positioning against what exists

State drug supply-chain systems already handle procurement, warehousing
and issue records. They are systems of record. NADI is the intelligence
layer that sits above one: it consumes stock movements and adds
forecasting, capacity scoring, and redistribution.

The go-to-market story is "a module on top of what is already deployed,"
not "replace your system."

## What success looks like in a pilot

Measured over three months in one district, against the district's own
prior records:

- Stockout-days reduced
- Fill rate improved
- Expiry write-off value reduced
- Time from shortage detection to resolution reduced

Not measured: model accuracy percentages. Nobody buys a MAPE.

## Constraints that shape every design decision

- **Connectivity is unreliable.** The PHC app must work fully offline.
- **Staff time is the scarcest resource.** Data entry must not add work.
  Prefer deriving data over asking for it.
- **States will not share raw data.** Cross-state learning must be
  federated — model weights move, records do not.
- **Health data is regulated.** No patient-level data in the system at
  all. We store facility-level aggregates only.
- **A human approves every consequential action.** Non-negotiable, and
  it is a feature, not a limitation.
