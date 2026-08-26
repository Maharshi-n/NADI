"""
Pydantic response schemas — camelCase API responses.

Conventions (from CONTEXT.md):
- API responses are camelCase — convert at the serialisation boundary
- Errors: {"error": {"code": "...", "message": "..."}}
- No nulls where zero or empty array is meaningful
- List endpoints: {"items": [...], "total": n}
"""

from typing import List, Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    """snake_case → camelCase."""
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class CamelModel(BaseModel):
    """Base model with camelCase alias generation."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------------------------------------------------------------------------
# Facilities
# ---------------------------------------------------------------------------

class FacilityItem(CamelModel):
    id: int
    name: str
    type: str
    district: str
    block: str
    state: str
    lat: float
    lng: float
    status: str  # "critical" | "warning" | "healthy"
    worst_days_of_cover: Optional[float] = None
    beds_total: int = 0
    cold_chain_capable: bool = False
    population_served: int = 0
    cbi: Optional[float] = None
    bottleneck: Optional[str] = None


class FacilityListResponse(CamelModel):
    items: List[FacilityItem]
    total: int


class StockSummaryItem(CamelModel):
    drug_id: int
    name: str
    salt: str
    unit: str
    category: str
    is_essential: bool
    quantity: int
    burn_rate: Optional[float] = None
    days_of_cover: Optional[float] = None
    expiry_date: Optional[date] = None
    status: str  # "critical" | "warning" | "healthy"


class FacilityDetailResponse(CamelModel):
    id: int
    name: str
    type: str
    district: str
    block: str
    state: str
    lat: float
    lng: float
    hfr_code: Optional[str] = None
    beds_total: int = 0
    cold_chain_capable: bool = False
    population_served: int = 0
    status: str
    worst_days_of_cover: Optional[float] = None
    stock: List[StockSummaryItem] = []


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

class StockItem(CamelModel):
    drug_id: int
    name: str
    salt: str
    strength: str
    form: str
    unit: str
    category: str
    is_essential: bool
    quantity: int
    burn_rate: Optional[float] = None
    days_of_cover: Optional[float] = None
    expiry_date: Optional[date] = None
    status: str


class StockListResponse(CamelModel):
    items: List[StockItem]
    total: int


# ---------------------------------------------------------------------------
# Risk queue
# ---------------------------------------------------------------------------

class RiskItem(CamelModel):
    facility_id: int
    facility_name: str
    drug_id: Optional[int] = None
    drug_name: Optional[str] = None
    days_to_stockout: Optional[float] = None
    confidence: Optional[float] = None
    driver: Optional[str] = None
    bottleneck: str = "medicine"
    status: str


class RiskListResponse(CamelModel):
    items: List[RiskItem]
    total: int


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------

class KpiResponse(CamelModel):
    facilities_at_risk: int
    projected_stockout_days: int
    expiry_at_risk_paise: int
    fill_rate: float


# ---------------------------------------------------------------------------
# Forecast (Phase 2)
# ---------------------------------------------------------------------------

class ForecastHistoryPoint(CamelModel):
    date: str
    quantity: int


class ForecastPoint(CamelModel):
    date: str
    predicted: float
    lower: float
    upper: float


class ForecastResponse(CamelModel):
    history: List[ForecastHistoryPoint]
    forecast: List[ForecastPoint]
    reorder_point: int
    stockout_date: Optional[str] = None
    days_to_stockout: Optional[float] = None
    confidence: float
    driver: str
    method_used: str


class ScenarioRequest(CamelModel):
    condition: str
    multiplier: float = 3.0
    district: str = "Dhar"
    start_week: Optional[int] = None


class ScenarioResponse(CamelModel):
    affected: int
    condition: str
    multiplier: float


# ---------------------------------------------------------------------------
# Phase 3 — Optimiser & Transfers
# ---------------------------------------------------------------------------

class PlanRequest(CamelModel):
    district: str = "Dhar"
    max_radius_km: Optional[float] = 65.0


class TransferProposalItem(CamelModel):
    from_facility_id: int
    from_name: str
    to_facility_id: int
    to_name: str
    drug_id: int
    drug_name: str
    unit: str = "units"
    is_cold_chain: bool = False
    quantity: int
    distance_km: float
    cost_paise: int
    cover_restored_days: float
    expiry_saved_paise: int


class PlanImpact(CamelModel):
    breaches_before: int
    breaches_after: int
    total_cost_paise: int
    expiry_avoided_paise: int


class PlanResponse(CamelModel):
    plan_id: str
    transfers: List[TransferProposalItem]
    impact: PlanImpact


class ApproveTransfersRequest(CamelModel):
    plan_id: str
    transfer_ids: Optional[List[int]] = None
    transfers: Optional[List[TransferProposalItem]] = None


class ApproveTransfersResponse(CamelModel):
    status: str
    plan_id: str
    approved_count: int


class TransferItem(CamelModel):
    id: int
    plan_id: Optional[str] = None
    from_facility_id: int
    from_name: str
    to_facility_id: int
    to_name: str
    drug_id: int
    drug_name: str
    quantity: int
    status: str
    proposed_at: datetime
    approved_at: Optional[datetime] = None
    approved_by_role: Optional[str] = None
    distance_km: Optional[float] = None
    cost_paise: Optional[int] = None


class TransferListResponse(CamelModel):
    items: List[TransferItem]
    total: int


# ---------------------------------------------------------------------------
# Phase 4 — Scan & Sync
# ---------------------------------------------------------------------------

class ScannedRow(CamelModel):
    drug_id: Optional[int] = None
    matched_name: Optional[str] = None
    raw_text: str
    batch_no: str
    quantity: int
    expiry_date: str
    confidence: float
    uncertain_fields: List[str] = []


class ScanResponse(CamelModel):
    rows: List[ScannedRow]


class ScanConfirmRequest(CamelModel):
    rows: List[ScannedRow]


class MutationItem(CamelModel):
    client_id: str
    type: str
    facility_id: int
    drug_id: int
    quantity: int
    occurred_at: datetime
    batch_no: Optional[str] = None


class SyncRequest(CamelModel):
    mutations: List[MutationItem]


class SyncResponse(CamelModel):
    applied: int
    conflicts: int


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Phase 5 — Capacity
# ---------------------------------------------------------------------------

class SpilloverTarget(CamelModel):
    facility_id: int
    name: str


class CapacityResponse(CamelModel):
    facility_id: int
    facility_name: str
    medicine_score: float
    bed_score: float
    staff_score: float
    cbi: float
    bottleneck: str  # "medicine" | "beds" | "staff"
    beds_total: int
    beds_occupied: int
    days_to_saturation: Optional[float] = None
    spillover_to: Optional[SpilloverTarget] = None
    staff_present: dict  # {"doctor": 1, "pharmacist": 0, ...}
    staff_required: dict


class BedEventRequest(CamelModel):
    facility_id: int
    type: str  # "admit" | "discharge"


class BedEventResponse(CamelModel):
    id: int
    facility_id: int
    type: str
    occurred_at: str


class StaffCheckinRequest(CamelModel):
    facility_id: int
    role: str
    present: int
    required: int = 1


class StaffCheckinResponse(CamelModel):
    id: int
    facility_id: int
    role: str
    present: int
    required: int

