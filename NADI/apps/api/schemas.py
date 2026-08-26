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
    drug_id: int
    drug_name: str
    days_to_stockout: Optional[float] = None
    confidence: Optional[float] = None
    driver: Optional[str] = None
    bottleneck: str = "medicine"  # Phase 1: always medicine
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
# Errors
# ---------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
