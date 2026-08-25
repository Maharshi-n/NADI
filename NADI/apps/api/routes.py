"""
Phase 2 API routes — Forecast.

Adds:
- GET /api/forecast — history + forecast band + driver + confidence
- POST /api/demo/scenario — inject outbreak via inflated disease signals
- POST /api/demo/reset — restore seed state

Updates:
- GET /api/risk — now uses forecasts table for driver/confidence
- GET /api/kpis — projected days now forecast-aware

All burn-rate and days-of-cover computations in SQL (Phase 1).
Forecast computations call ml/forecasting/engine.py.
"""

import os
import sys
import math
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, func, select, case, literal_column, and_
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, os.path.dirname(__file__))
from db import get_db
from schemas import (
    FacilityItem,
    FacilityListResponse,
    FacilityDetailResponse,
    StockSummaryItem,
    StockItem,
    StockListResponse,
    RiskItem,
    RiskListResponse,
    KpiResponse,
    ForecastResponse,
    ForecastHistoryItem,
    ForecastBandItem,
    ScenarioRequest,
    ScenarioResponse,
)

# Add ml directory to path for forecasting imports
ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
sys.path.insert(0, ML_DIR)
from forecasting.engine import forecast_facility_drug
from forecasting.classify import classify_demand

router = APIRouter(prefix="/api")

# Status thresholds (shared with frontend via /api/kpis context)
CRITICAL_DAYS = 15
WARNING_DAYS = 30


def days_of_cover_status(days: Optional[float]) -> str:
    """Map days-of-cover to status string."""
    if days is None or days < CRITICAL_DAYS:
        return "critical"
    elif days < WARNING_DAYS:
        return "warning"
    return "healthy"


# ---------------------------------------------------------------------------
# GET /api/facilities
# ---------------------------------------------------------------------------

@router.get("/facilities", response_model=FacilityListResponse)
async def list_facilities(
    district: Optional[str] = None,
    type: Optional[str] = Query(None, alias="type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List facilities with their worst days-of-cover.
    
    Worst days-of-cover = MIN across all drugs of:
        current_stock / (dispensed_last_30_days / 30)
    
    Computed entirely in SQL.
    """
    # SQL: compute burn rate and days of cover per facility-drug,
    # then take the worst (minimum) per facility
    query = text("""
        WITH burn AS (
            SELECT
                t.facility_id,
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
              )
            GROUP BY t.facility_id, t.drug_id
        ),
        current_stock AS (
            SELECT
                s.facility_id,
                s.drug_id,
                SUM(s.quantity) AS total_qty
            FROM stock s
            GROUP BY s.facility_id, s.drug_id
        ),
        cover AS (
            SELECT
                cs.facility_id,
                cs.drug_id,
                cs.total_qty,
                b.burn_rate,
                CASE
                    WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                    ELSE NULL
                END AS days_of_cover
            FROM current_stock cs
            LEFT JOIN burn b ON cs.facility_id = b.facility_id
                            AND cs.drug_id = b.drug_id
        ),
        worst AS (
            SELECT
                facility_id,
                MIN(days_of_cover) AS worst_days
            FROM cover
            WHERE days_of_cover IS NOT NULL
            GROUP BY facility_id
        )
        SELECT
            f.id, f.name, f.type, f.district, f.block, f.state,
            f.lat, f.lng, f.beds_total, f.cold_chain_capable,
            f.population_served,
            w.worst_days
        FROM facilities f
        LEFT JOIN worst w ON f.id = w.facility_id
        WHERE 1=1
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
          AND (CAST(:ftype AS text) IS NULL OR CAST(f.type AS text) = CAST(:ftype AS text))
        ORDER BY COALESCE(w.worst_days, 999999) ASC
        LIMIT :lim OFFSET :off
    """)

    count_query = text("""
        SELECT COUNT(*)
        FROM facilities f
        WHERE 1=1
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
          AND (CAST(:ftype AS text) IS NULL OR CAST(f.type AS text) = CAST(:ftype AS text))
    """)

    params = {"district": district, "ftype": type, "lim": limit, "off": offset}

    result = await db.execute(query, params)
    rows = result.mappings().all()

    count_result = await db.execute(count_query, params)
    total = count_result.scalar()

    items = []
    for r in rows:
        worst = r["worst_days"]
        items.append(FacilityItem(
            id=r["id"],
            name=r["name"],
            type=r["type"],
            district=r["district"],
            block=r["block"],
            state=r["state"],
            lat=r["lat"],
            lng=r["lng"],
            beds_total=r["beds_total"],
            cold_chain_capable=r["cold_chain_capable"],
            population_served=r["population_served"],
            status=days_of_cover_status(worst),
            worst_days_of_cover=round(worst, 1) if worst is not None else None,
        ))

    return FacilityListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/facilities/{id}
# ---------------------------------------------------------------------------

@router.get("/facilities/{facility_id}", response_model=FacilityDetailResponse)
async def get_facility(
    facility_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Facility detail with current stock and burn rates."""
    # Facility info
    fac_result = await db.execute(
        text("SELECT * FROM facilities WHERE id = :fid"),
        {"fid": facility_id},
    )
    fac = fac_result.mappings().first()
    if not fac:
        raise HTTPException(status_code=404, detail="Facility not found")

    # Stock with burn rate computed in SQL
    stock_query = text("""
        WITH burn AS (
            SELECT
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.facility_id = :fid
              AND t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
              )
            GROUP BY t.drug_id
        ),
        current_stock AS (
            SELECT
                s.drug_id,
                SUM(s.quantity) AS total_qty,
                MIN(s.expiry_date) AS earliest_expiry
            FROM stock s
            WHERE s.facility_id = :fid
            GROUP BY s.drug_id
        )
        SELECT
            d.id AS drug_id,
            d.name,
            d.salt,
            d.unit,
            d.category,
            d.is_essential,
            COALESCE(cs.total_qty, 0) AS quantity,
            b.burn_rate,
            CASE
                WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                ELSE NULL
            END AS days_of_cover,
            cs.earliest_expiry AS expiry_date
        FROM current_stock cs
        JOIN drugs d ON d.id = cs.drug_id
        LEFT JOIN burn b ON b.drug_id = cs.drug_id
        ORDER BY COALESCE(
            CASE WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate ELSE NULL END,
            999999
        ) ASC
    """)

    stock_result = await db.execute(stock_query, {"fid": facility_id})
    stock_rows = stock_result.mappings().all()

    stock_items = []
    worst_days = None
    for r in stock_rows:
        doc = r["days_of_cover"]
        if doc is not None:
            doc_rounded = round(doc, 1)
            if worst_days is None or doc_rounded < worst_days:
                worst_days = doc_rounded
        else:
            doc_rounded = None

        stock_items.append(StockSummaryItem(
            drug_id=r["drug_id"],
            name=r["name"],
            salt=r["salt"],
            unit=r["unit"],
            category=r["category"],
            is_essential=r["is_essential"],
            quantity=r["quantity"],
            burn_rate=round(r["burn_rate"], 2) if r["burn_rate"] else None,
            days_of_cover=doc_rounded,
            expiry_date=r["expiry_date"],
            status=days_of_cover_status(doc),
        ))

    return FacilityDetailResponse(
        id=fac["id"],
        name=fac["name"],
        type=fac["type"],
        district=fac["district"],
        block=fac["block"],
        state=fac["state"],
        lat=fac["lat"],
        lng=fac["lng"],
        hfr_code=fac["hfr_code"],
        beds_total=fac["beds_total"],
        cold_chain_capable=fac["cold_chain_capable"],
        population_served=fac["population_served"],
        status=days_of_cover_status(worst_days),
        worst_days_of_cover=worst_days,
        stock=stock_items,
    )


# ---------------------------------------------------------------------------
# GET /api/stock
# ---------------------------------------------------------------------------

@router.get("/stock", response_model=StockListResponse)
async def list_stock(
    facility_id: Optional[int] = Query(None, alias="facilityId"),
    essential_only: Optional[bool] = Query(None, alias="essentialOnly"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Stock rows with burn rate and days of cover.
    Burn rate = dispensed_qty_last_30_days / 30, computed in SQL.
    """
    query = text("""
        WITH burn AS (
            SELECT
                t.facility_id,
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
              )
              AND (CAST(:fid AS int) IS NULL OR t.facility_id = :fid)
            GROUP BY t.facility_id, t.drug_id
        ),
        current_stock AS (
            SELECT
                s.facility_id,
                s.drug_id,
                SUM(s.quantity) AS total_qty,
                MIN(s.expiry_date) AS earliest_expiry
            FROM stock s
            WHERE (CAST(:fid AS int) IS NULL OR s.facility_id = :fid)
            GROUP BY s.facility_id, s.drug_id
        )
        SELECT
            d.id AS drug_id,
            d.name, d.salt, d.strength, d.form, d.unit,
            d.category, d.is_essential,
            COALESCE(cs.total_qty, 0) AS quantity,
            b.burn_rate,
            CASE
                WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                ELSE NULL
            END AS days_of_cover,
            cs.earliest_expiry AS expiry_date
        FROM current_stock cs
        JOIN drugs d ON d.id = cs.drug_id
        LEFT JOIN burn b ON b.facility_id = cs.facility_id
                        AND b.drug_id = cs.drug_id
        WHERE 1=1
          AND (CAST(:essential AS boolean) IS NULL OR d.is_essential = :essential)
        ORDER BY COALESCE(
            CASE WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate ELSE NULL END,
            999999
        ) ASC
        LIMIT :lim OFFSET :off
    """)

    count_query = text("""
        WITH current_stock AS (
            SELECT s.drug_id
            FROM stock s
            WHERE (CAST(:fid AS int) IS NULL OR s.facility_id = :fid)
            GROUP BY s.facility_id, s.drug_id
        )
        SELECT COUNT(*)
        FROM current_stock cs
        JOIN drugs d ON d.id = cs.drug_id
        WHERE (CAST(:essential AS boolean) IS NULL OR d.is_essential = :essential)
    """)

    params = {
        "fid": facility_id,
        "essential": essential_only,
        "lim": limit,
        "off": offset,
    }

    result = await db.execute(query, params)
    rows = result.mappings().all()

    count_result = await db.execute(count_query, params)
    total = count_result.scalar()

    items = []
    for r in rows:
        doc = r["days_of_cover"]
        items.append(StockItem(
            drug_id=r["drug_id"],
            name=r["name"],
            salt=r["salt"],
            strength=r["strength"],
            form=r["form"],
            unit=r["unit"],
            category=r["category"],
            is_essential=r["is_essential"],
            quantity=r["quantity"],
            burn_rate=round(r["burn_rate"], 2) if r["burn_rate"] else None,
            days_of_cover=round(doc, 1) if doc is not None else None,
            expiry_date=r["expiry_date"],
            status=days_of_cover_status(doc),
        ))

    return StockListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/risk — Phase 2: forecast-aware with driver + confidence
# ---------------------------------------------------------------------------

@router.get("/risk", response_model=RiskListResponse)
async def list_risk(
    district: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Risk queue — ranked ascending by days to stockout.
    Phase 2: uses forecasts table for driver/confidence when available,
    falls back to burn-rate days-of-cover when forecasts are absent.
    """
    # Try forecast-aware query first
    query = text("""
        WITH burn AS (
            SELECT
                t.facility_id,
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
              )
            GROUP BY t.facility_id, t.drug_id
        ),
        current_stock AS (
            SELECT
                s.facility_id,
                s.drug_id,
                SUM(s.quantity) AS total_qty
            FROM stock s
            GROUP BY s.facility_id, s.drug_id
        ),
        cover AS (
            SELECT
                cs.facility_id,
                cs.drug_id,
                CASE
                    WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                    ELSE NULL
                END AS days_of_cover
            FROM current_stock cs
            LEFT JOIN burn b ON cs.facility_id = b.facility_id
                            AND cs.drug_id = b.drug_id
        ),
        ranked_forecasts AS (
            SELECT
                fc.facility_id,
                fc.drug_id,
                fc.days_to_stockout,
                fc.confidence,
                fc.driver_label,
                ROW_NUMBER() OVER (
                    PARTITION BY fc.facility_id, fc.drug_id
                    ORDER BY fc.computed_at DESC
                ) AS rn
            FROM forecasts fc
        ),
        latest_forecasts AS (
            SELECT * FROM ranked_forecasts WHERE rn = 1
        )
        SELECT
            f.id AS facility_id,
            f.name AS facility_name,
            d.id AS drug_id,
            d.name AS drug_name,
            COALESCE(lf.days_to_stockout, c.days_of_cover) AS days_to_stockout,
            lf.confidence,
            lf.driver_label AS driver,
            'medicine' AS bottleneck
        FROM cover c
        JOIN facilities f ON f.id = c.facility_id
        JOIN drugs d ON d.id = c.drug_id
        LEFT JOIN latest_forecasts lf ON lf.facility_id = c.facility_id
                                      AND lf.drug_id = c.drug_id
        WHERE COALESCE(lf.days_to_stockout, c.days_of_cover) IS NOT NULL
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
        ORDER BY COALESCE(lf.days_to_stockout, c.days_of_cover) ASC
        LIMIT :lim OFFSET :off
    """)

    count_query = text("""
        WITH burn AS (
            SELECT
                t.facility_id,
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
              )
            GROUP BY t.facility_id, t.drug_id
        ),
        current_stock AS (
            SELECT
                s.facility_id,
                s.drug_id,
                SUM(s.quantity) AS total_qty
            FROM stock s
            GROUP BY s.facility_id, s.drug_id
        ),
        cover AS (
            SELECT
                cs.facility_id,
                cs.drug_id,
                CASE
                    WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                    ELSE NULL
                END AS days_of_cover
            FROM current_stock cs
            LEFT JOIN burn b ON cs.facility_id = b.facility_id
                            AND cs.drug_id = b.drug_id
        )
        SELECT COUNT(*)
        FROM cover c
        JOIN facilities f ON f.id = c.facility_id
        WHERE c.days_of_cover IS NOT NULL
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
    """)

    params = {"district": district, "lim": limit, "off": offset}

    result = await db.execute(query, params)
    rows = result.mappings().all()

    count_result = await db.execute(count_query, params)
    total = count_result.scalar()

    items = []
    for r in rows:
        dts = r["days_to_stockout"]
        items.append(RiskItem(
            facility_id=r["facility_id"],
            facility_name=r["facility_name"],
            drug_id=r["drug_id"],
            drug_name=r["drug_name"],
            days_to_stockout=round(dts, 1) if dts is not None else None,
            confidence=round(r["confidence"], 2) if r["confidence"] is not None else None,
            driver=r["driver"],
            bottleneck=r["bottleneck"],
            status=days_of_cover_status(dts),
        ))

    return RiskListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /api/kpis
# ---------------------------------------------------------------------------

@router.get("/kpis", response_model=KpiResponse)
async def get_kpis(
    district: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Four KPI tiles, computed server-side.
    - facilitiesAtRisk: count of facilities with any drug below 15 days cover
    - projectedStockoutDays: sum of (15 - daysOfCover) for critical pairs
    - expiryAtRiskPaise: 0 (no cost data in Phase 1)
    - fillRate: fraction of essential drugs with stock > 0 across all facilities
    """
    kpi_query = text("""
        WITH burn AS (
            SELECT
                t.facility_id,
                t.drug_id,
                COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
            FROM transactions t
            WHERE t.type = 'dispense'
              AND t.occurred_at >= (
                  (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
              )
            GROUP BY t.facility_id, t.drug_id
        ),
        current_stock AS (
            SELECT
                s.facility_id,
                s.drug_id,
                SUM(s.quantity) AS total_qty
            FROM stock s
            GROUP BY s.facility_id, s.drug_id
        ),
        cover AS (
            SELECT
                cs.facility_id,
                cs.drug_id,
                CASE
                    WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                    ELSE NULL
                END AS days_of_cover
            FROM current_stock cs
            JOIN facilities f ON f.id = cs.facility_id
            LEFT JOIN burn b ON cs.facility_id = b.facility_id
                            AND cs.drug_id = b.drug_id
            WHERE (CAST(:district AS text) IS NULL OR f.district = :district)
        ),
        -- Facilities at risk: any drug below 15 days
        at_risk AS (
            SELECT DISTINCT facility_id
            FROM cover
            WHERE days_of_cover IS NOT NULL AND days_of_cover < 15
        ),
        -- Projected stockout-days: sum of deficit
        deficit AS (
            SELECT
                COALESCE(SUM(15.0 - days_of_cover), 0)::int AS total_deficit
            FROM cover
            WHERE days_of_cover IS NOT NULL AND days_of_cover < 15
        ),
        -- Fill rate: fraction of essential drug slots with stock > 0
        essential_fill AS (
            SELECT
                COUNT(*) FILTER (WHERE cs.total_qty > 0) AS filled,
                COUNT(*) AS total_slots
            FROM facilities f
            CROSS JOIN drugs d
            LEFT JOIN current_stock cs ON cs.facility_id = f.id AND cs.drug_id = d.id
            WHERE d.is_essential = true
              AND (CAST(:district AS text) IS NULL OR f.district = :district)
        )
        SELECT
            (SELECT COUNT(*) FROM at_risk) AS facilities_at_risk,
            (SELECT total_deficit FROM deficit) AS projected_stockout_days,
            0 AS expiry_at_risk_paise,
            CASE
                WHEN (SELECT total_slots FROM essential_fill) > 0
                THEN (SELECT filled FROM essential_fill)::float / (SELECT total_slots FROM essential_fill)
                ELSE 0
            END AS fill_rate
    """)

    result = await db.execute(kpi_query, {"district": district})
    row = result.mappings().first()

    return KpiResponse(
        facilities_at_risk=row["facilities_at_risk"] or 0,
        projected_stockout_days=row["projected_stockout_days"] or 0,
        expiry_at_risk_paise=row["expiry_at_risk_paise"] or 0,
        fill_rate=round(row["fill_rate"] or 0, 4),
    )


# ---------------------------------------------------------------------------
# GET /api/forecast — Phase 2
# ---------------------------------------------------------------------------

@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    facility_id: int = Query(..., alias="facilityId"),
    drug_id: int = Query(..., alias="drugId"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast for a single facility-drug pair.
    Returns history, forecast band, reorder point, stockout date,
    confidence, driver, and method used.
    """
    # 1. Get daily dispensing history (up to 180 days)
    history_query = text("""
        SELECT
            DATE(t.occurred_at) AS day,
            COALESCE(SUM(t.quantity), 0) AS qty
        FROM transactions t
        WHERE t.facility_id = :fid
          AND t.drug_id = :did
          AND t.type = 'dispense'
        GROUP BY DATE(t.occurred_at)
        ORDER BY day ASC
    """)
    result = await db.execute(history_query, {"fid": facility_id, "did": drug_id})
    history_rows = result.mappings().all()

    if not history_rows:
        return ForecastResponse(
            history=[], forecast=[], reorder_point=0,
            stockout_date=None, days_to_stockout=None,
            confidence=0.0, driver="No history", method_used="none",
        )

    # Fill gaps with zeros for a continuous daily series
    daily_data = {}
    for r in history_rows:
        daily_data[r["day"]] = float(r["qty"])

    min_date = min(daily_data.keys())
    max_date = max(daily_data.keys())
    all_days = []
    current = min_date
    while current <= max_date:
        all_days.append((current.isoformat(), daily_data.get(current, 0.0)))
        current += timedelta(days=1)

    # 2. Get current stock
    stock_query = text("""
        SELECT COALESCE(SUM(s.quantity), 0) AS total_qty
        FROM stock s
        WHERE s.facility_id = :fid AND s.drug_id = :did
    """)
    stock_result = await db.execute(stock_query, {"fid": facility_id, "did": drug_id})
    current_stock = float(stock_result.scalar() or 0)

    # 3. Get drug category for season factor lookup
    drug_query = text("SELECT category FROM drugs WHERE id = :did")
    drug_result = await db.execute(drug_query, {"did": drug_id})
    drug_row = drug_result.mappings().first()
    drug_category = drug_row["category"] if drug_row else "unknown"

    # 4. Get facility district for outbreak factor
    fac_query = text("SELECT district FROM facilities WHERE id = :fid")
    fac_result = await db.execute(fac_query, {"fid": facility_id})
    fac_row = fac_result.mappings().first()
    district = fac_row["district"] if fac_row else "Dhar"

    # 5. Get season factor for current month
    current_month = date.today().month
    sf_query = text("""
        SELECT factor FROM season_factor
        WHERE drug_category = :cat AND month = :m
    """)
    sf_result = await db.execute(sf_query, {"cat": drug_category, "m": current_month})
    sf_row = sf_result.scalar()
    season_factor = float(sf_row) if sf_row else 1.0

    # 6. Compute outbreak factor from recent disease signals
    outbreak_factor, outbreak_condition, outbreak_pct = await _compute_outbreak_factor(
        db, district, drug_category
    )

    # 7. Classify demand
    quantities = [q for _, q in all_days]
    demand_class = classify_demand(quantities)

    # 8. Run the forecasting engine
    forecast_result = forecast_facility_drug(
        daily_dispensing=all_days,
        current_stock=current_stock,
        season_factor=season_factor,
        outbreak_factor=outbreak_factor,
        outbreak_condition=outbreak_condition,
        outbreak_pct_change=outbreak_pct,
        demand_class=demand_class,
    )

    return ForecastResponse(
        history=[ForecastHistoryItem(date=h["date"], quantity=h["quantity"])
                 for h in forecast_result["history"]],
        forecast=[ForecastBandItem(**b) for b in forecast_result["forecast_band"]],
        reorder_point=forecast_result["reorder_point"],
        stockout_date=forecast_result["stockout_date"],
        days_to_stockout=forecast_result["days_to_stockout"],
        confidence=forecast_result["confidence"],
        driver=forecast_result["driver_label"],
        method_used=forecast_result["method_used"],
    )


# ---------------------------------------------------------------------------
# Outbreak factor helper
# ---------------------------------------------------------------------------

# Map from disease condition to drug categories that are affected
CONDITION_DRUG_MAP = {
    "dengue": ["antimalarial", "analgesic", "antibiotic"],
    "malaria": ["antimalarial", "analgesic"],
    "diarrhoeal": ["ors_zinc", "antibiotic", "gastrointestinal"],
    "respiratory_infection": ["respiratory", "antibiotic", "antihistamine"],
    "tuberculosis": ["antibiotic"],
}


async def _compute_outbreak_factor(
    db: AsyncSession,
    district: str,
    drug_category: str,
) -> tuple:
    """
    Compare the latest 2 weeks of disease signals vs the prior 4-week
    baseline. If there's a spike in a condition that affects this drug
    category, return (factor, condition_name, pct_change).
    """
    signal_query = text("""
        WITH recent AS (
            SELECT condition, SUM(case_count) AS cases
            FROM disease_signal
            WHERE district = :dist
              AND week_start >= CURRENT_DATE - INTERVAL '14 days'
            GROUP BY condition
        ),
        baseline AS (
            SELECT condition, SUM(case_count) / 4.0 AS avg_cases
            FROM disease_signal
            WHERE district = :dist
              AND week_start >= CURRENT_DATE - INTERVAL '42 days'
              AND week_start < CURRENT_DATE - INTERVAL '14 days'
            GROUP BY condition
        )
        SELECT
            r.condition,
            r.cases AS recent_cases,
            COALESCE(b.avg_cases, 1) AS baseline_cases
        FROM recent r
        LEFT JOIN baseline b ON r.condition = b.condition
        ORDER BY (r.cases / GREATEST(b.avg_cases, 1)) DESC
    """)

    result = await db.execute(signal_query, {"dist": district})
    rows = result.mappings().all()

    max_factor = 1.0
    max_condition = None
    max_pct = 0.0

    for r in rows:
        condition = r["condition"]
        affected_cats = CONDITION_DRUG_MAP.get(condition, [])
        if drug_category not in affected_cats:
            continue

        recent = float(r["recent_cases"])
        baseline = float(r["baseline_cases"])
        if baseline > 0:
            ratio = recent / baseline
            pct_change = (recent - baseline) / baseline
        else:
            ratio = 1.0
            pct_change = 0.0

        # Only count as outbreak if > 50% increase
        if ratio > 1.5 and ratio > max_factor:
            max_factor = min(ratio, 5.0)  # Cap at 5x to avoid absurd forecasts
            max_condition = condition
            max_pct = pct_change

    return max_factor, max_condition, max_pct


# ---------------------------------------------------------------------------
# Forecast computation — batch (for startup and post-scenario)
# ---------------------------------------------------------------------------

async def compute_all_forecasts(db: AsyncSession):
    """
    Compute forecasts for all facility-drug pairs and write to the
    forecasts table. Called on startup and after scenario changes.
    """
    # Get all facility-drug pairs with stock
    pairs_query = text("""
        SELECT DISTINCT s.facility_id, s.drug_id
        FROM stock s
        JOIN facilities f ON f.id = s.facility_id
        WHERE f.type != 'warehouse'
    """)
    result = await db.execute(pairs_query)
    pairs = result.mappings().all()

    # Clear existing forecasts
    await db.execute(text("DELETE FROM forecasts"))

    computed = 0
    for pair in pairs:
        fid = pair["facility_id"]
        did = pair["drug_id"]

        # History
        hist_result = await db.execute(text("""
            SELECT DATE(t.occurred_at) AS day, COALESCE(SUM(t.quantity), 0) AS qty
            FROM transactions t
            WHERE t.facility_id = :fid AND t.drug_id = :did AND t.type = 'dispense'
            GROUP BY DATE(t.occurred_at) ORDER BY day ASC
        """), {"fid": fid, "did": did})
        hist_rows = hist_result.mappings().all()

        if not hist_rows:
            continue

        # Fill gaps
        daily_data = {r["day"]: float(r["qty"]) for r in hist_rows}
        min_d = min(daily_data.keys())
        max_d = max(daily_data.keys())
        all_days = []
        cur = min_d
        while cur <= max_d:
            all_days.append((cur.isoformat(), daily_data.get(cur, 0.0)))
            cur += timedelta(days=1)

        # Stock
        stock_res = await db.execute(text(
            "SELECT COALESCE(SUM(quantity), 0) FROM stock WHERE facility_id = :fid AND drug_id = :did"
        ), {"fid": fid, "did": did})
        current_stock = float(stock_res.scalar() or 0)

        # Drug category
        drug_res = await db.execute(text("SELECT category FROM drugs WHERE id = :did"), {"did": did})
        drug_row = drug_res.mappings().first()
        drug_category = drug_row["category"] if drug_row else "unknown"

        # District
        fac_res = await db.execute(text("SELECT district FROM facilities WHERE id = :fid"), {"fid": fid})
        fac_row = fac_res.mappings().first()
        district = fac_row["district"] if fac_row else "Dhar"

        # Season factor
        current_month = date.today().month
        sf_res = await db.execute(text(
            "SELECT factor FROM season_factor WHERE drug_category = :cat AND month = :m"
        ), {"cat": drug_category, "m": current_month})
        sf_val = sf_res.scalar()
        season_factor = float(sf_val) if sf_val else 1.0

        # Outbreak factor
        outbreak_factor, outbreak_condition, outbreak_pct = await _compute_outbreak_factor(
            db, district, drug_category
        )

        # Classify and forecast
        quantities = [q for _, q in all_days]
        demand_class = classify_demand(quantities)

        fc = forecast_facility_drug(
            daily_dispensing=all_days,
            current_stock=current_stock,
            season_factor=season_factor,
            outbreak_factor=outbreak_factor,
            outbreak_condition=outbreak_condition,
            outbreak_pct_change=outbreak_pct,
            demand_class=demand_class,
        )

        # Write to forecasts table
        await db.execute(text("""
            INSERT INTO forecasts (facility_id, drug_id, computed_at,
                predicted_daily_rate, days_to_stockout, confidence,
                driver_label, method_used)
            VALUES (:fid, :did, NOW(), :rate, :dts, :conf, :driver, :method)
        """), {
            "fid": fid, "did": did,
            "rate": fc["predicted_daily_rate"],
            "dts": fc["days_to_stockout"],
            "conf": fc["confidence"],
            "driver": fc["driver_label"],
            "method": fc["method_used"],
        })
        computed += 1

    await db.commit()
    return computed


# ---------------------------------------------------------------------------
# POST /api/demo/scenario — Phase 2
# ---------------------------------------------------------------------------

@router.post("/demo/scenario", response_model=ScenarioResponse)
async def fire_scenario(
    body: ScenarioRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Inject an outbreak: write inflated disease_signal case counts,
    then recompute forecasts. Returns affected facility count.
    """
    condition = body.condition
    multiplier = body.multiplier
    district = body.district

    # Inflate recent disease signals for this condition
    await db.execute(text("""
        UPDATE disease_signal
        SET case_count = CAST(case_count * :mult AS int)
        WHERE condition = :cond
          AND district = :dist
          AND week_start >= CURRENT_DATE - INTERVAL '14 days'
    """), {"mult": multiplier, "cond": condition, "dist": district})

    await db.commit()

    # Recompute all forecasts
    computed = await compute_all_forecasts(db)

    # Count affected facilities (those whose forecast worsened)
    affected_cats = CONDITION_DRUG_MAP.get(condition, [])
    if affected_cats:
        cat_list = ",".join(f"'{c}'" for c in affected_cats)
        count_result = await db.execute(text(f"""
            SELECT COUNT(DISTINCT s.facility_id)
            FROM stock s
            JOIN drugs d ON d.id = s.drug_id
            JOIN facilities f ON f.id = s.facility_id
            WHERE d.category IN ({cat_list})
              AND f.district = :dist
              AND f.type != 'warehouse'
        """), {"dist": district})
        affected = count_result.scalar() or 0
    else:
        affected = 0

    return ScenarioResponse(
        affected_facilities=affected,
        message=f"{condition.replace('_', ' ').title()} outbreak ({multiplier}×) applied to {district}. {computed} forecasts recomputed.",
    )


# ---------------------------------------------------------------------------
# POST /api/demo/reset — Phase 2
# ---------------------------------------------------------------------------

@router.post("/demo/reset", response_model=ScenarioResponse)
async def reset_demo(
    db: AsyncSession = Depends(get_db),
):
    """
    Restore seed state: regenerate disease_signal data from the
    generator and recompute all forecasts.
    """
    # Re-seed disease signals from generated data
    import json
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "generated"))
    ds_path = os.path.join(data_dir, "disease_signal.json")

    if os.path.exists(ds_path):
        with open(ds_path) as f:
            signals = json.load(f)

        # Clear and re-insert
        await db.execute(text("DELETE FROM disease_signal"))
        for s in signals:
            await db.execute(text("""
                INSERT INTO disease_signal (district, condition, week_start, case_count, source)
                VALUES (:district, :condition, :week_start, :case_count, :source)
            """), {
                "district": s["district"],
                "condition": s["condition"],
                "week_start": datetime.strptime(s["week_start"], "%Y-%m-%d").date(),
                "case_count": s["case_count"],
                "source": s.get("source", "IDSP"),
            })
        await db.commit()

    # Recompute forecasts
    computed = await compute_all_forecasts(db)

    return ScenarioResponse(
        affected_facilities=0,
        message=f"Demo reset complete. Disease signals restored, {computed} forecasts recomputed.",
    )
