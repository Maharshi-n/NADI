"""
Phase 1 API routes — The Spine.

All burn-rate and days-of-cover computations happen in SQL, not Python.
This is a PHASES.md requirement for scale correctness.

Conventions:
- camelCase responses via Pydantic alias
- List endpoints: limit/offset → {items, total}
- Status thresholds: CRITICAL < 15 days, WARNING < 30 days
"""

import os
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
import json
import difflib
import google.generativeai as genai
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
)

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
                c.facility_id,
                MIN(COALESCE(fc.days_to_stockout, c.days_of_cover)) AS worst_days
            FROM cover c
            LEFT JOIN forecasts fc ON fc.facility_id = c.facility_id
                                  AND fc.drug_id = c.drug_id
            WHERE COALESCE(fc.days_to_stockout, c.days_of_cover) IS NOT NULL
            GROUP BY c.facility_id
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
        text("SELECT * FROM facilities WHERE id = CAST(:fid AS integer)"),
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
            COALESCE(
                fc.days_to_stockout,
                CASE
                    WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                    ELSE NULL
                END
            ) AS days_of_cover,
            cs.earliest_expiry AS expiry_date
        FROM current_stock cs
        JOIN drugs d ON d.id = cs.drug_id
        LEFT JOIN burn b ON b.drug_id = cs.drug_id
        LEFT JOIN forecasts fc ON fc.drug_id = cs.drug_id AND fc.facility_id = :fid
        ORDER BY COALESCE(
            fc.days_to_stockout,
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
# GET /api/risk
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
    Phase 2: prefers forecast data when available, falls back to burn-rate.
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
        SELECT
            f.id AS facility_id,
            f.name AS facility_name,
            d.id AS drug_id,
            d.name AS drug_name,
            COALESCE(fc.days_to_stockout, c.days_of_cover) AS days_to_stockout,
            fc.confidence,
            fc.driver_label AS driver
        FROM cover c
        JOIN facilities f ON f.id = c.facility_id
        JOIN drugs d ON d.id = c.drug_id
        LEFT JOIN forecasts fc ON fc.facility_id = c.facility_id
                              AND fc.drug_id = c.drug_id
        WHERE COALESCE(fc.days_to_stockout, c.days_of_cover) IS NOT NULL
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
        ORDER BY COALESCE(fc.days_to_stockout, c.days_of_cover) ASC
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
        LEFT JOIN forecasts fc ON fc.facility_id = c.facility_id
                              AND fc.drug_id = c.drug_id
        WHERE COALESCE(fc.days_to_stockout, c.days_of_cover) IS NOT NULL
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
        dts_float = float(dts) if dts is not None else None
        conf = float(r["confidence"]) if r["confidence"] is not None else None
        items.append(RiskItem(
            facility_id=r["facility_id"],
            facility_name=r["facility_name"],
            drug_id=r["drug_id"],
            drug_name=r["drug_name"],
            days_to_stockout=round(dts_float, 1) if dts_float is not None else None,
            confidence=round(conf, 2) if conf is not None else None,
            driver=r["driver"],
            bottleneck="medicine",
            status=days_of_cover_status(dts_float),
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
                COALESCE(
                    fc.days_to_stockout,
                    CASE
                        WHEN b.burn_rate > 0 THEN cs.total_qty / b.burn_rate
                        ELSE NULL
                    END
                ) AS days_of_cover
            FROM current_stock cs
            JOIN facilities f ON f.id = cs.facility_id
            LEFT JOIN burn b ON cs.facility_id = b.facility_id
                            AND cs.drug_id = b.drug_id
            LEFT JOIN forecasts fc ON fc.facility_id = cs.facility_id
                                  AND fc.drug_id = cs.drug_id
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


# ===========================================================================
# PHASE 2 — Forecast endpoints
# ===========================================================================

from schemas import (
    ForecastHistoryPoint,
    ForecastPoint,
    ForecastResponse,
    ScenarioRequest,
    ScenarioResponse,
)

# Add ml/ to path for forecasting engine import
# Docker mounts ml/ at /ml; local dev has it relative to apps/api/
ML_DIR = "/ml" if os.path.isdir("/ml/forecasting") else os.path.join(os.path.dirname(__file__), "..", "..", "ml")
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from forecasting.engine import (
    forecast_facility_drug,
    CONDITION_DRUG_MAP,
)


# ---------------------------------------------------------------------------
# GET /api/forecast
# ---------------------------------------------------------------------------

@router.get("/forecast", response_model=ForecastResponse)
async def get_forecast(
    facility_id: int = Query(..., alias="facilityId"),
    drug_id: int = Query(..., alias="drugId"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast for a specific facility-drug pair.
    
    Returns 90 days of history + 30 days of forecast with
    confidence band, driver attribution, and method used.
    """
    # 1. Fetch dispensing history (last 180 days for classification, return last 90)
    history_query = text("""
        SELECT
            DATE(t.occurred_at) AS date,
            SUM(t.quantity) AS quantity
        FROM transactions t
        WHERE t.facility_id = :fid
          AND t.drug_id = :did
          AND t.type = 'dispense'
          AND t.occurred_at >= (
              (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '180 days'
          )
        GROUP BY DATE(t.occurred_at)
        ORDER BY DATE(t.occurred_at) ASC
    """)
    
    result = await db.execute(history_query, {"fid": facility_id, "did": drug_id})
    history_rows = result.mappings().all()
    
    if not history_rows:
        raise HTTPException(
            status_code=404,
            detail="No dispensing history found for this facility-drug pair"
        )
    
    # Build a complete daily series (fill zeros for missing days)
    from datetime import date as date_type, datetime as dt_type, timedelta
    
    # Find date range
    all_dates = [row["date"] for row in history_rows]
    min_date = min(all_dates)
    max_date = max(all_dates)
    
    date_qty_map = {}
    for row in history_rows:
        d = row["date"]
        date_qty_map[d] = int(row["quantity"])
    
    # Fill in complete daily series
    daily_series = []
    current = min_date
    while current <= max_date:
        qty = date_qty_map.get(current, 0)
        daily_series.append({"date": current.isoformat(), "quantity": qty})
        current += timedelta(days=1)
    
    # 2. Get current stock
    stock_query = text("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM stock
        WHERE facility_id = CAST(:fid AS integer) AND drug_id = CAST(:did AS integer)
    """)
    stock_result = await db.execute(stock_query, {"fid": facility_id, "did": drug_id})
    current_stock = stock_result.scalar() or 0
    
    # 3. Get drug category
    drug_query = text("SELECT category FROM drugs WHERE id = CAST(:did AS integer)")
    drug_result = await db.execute(drug_query, {"did": drug_id})
    drug_row = drug_result.mappings().first()
    if not drug_row:
        raise HTTPException(status_code=404, detail="Drug not found")
    drug_category = drug_row["category"]
    
    # 4. Get facility district for disease signals
    fac_query = text("SELECT district FROM facilities WHERE id = CAST(:fid AS integer)")
    fac_result = await db.execute(fac_query, {"fid": facility_id})
    fac_row = fac_result.mappings().first()
    if not fac_row:
        raise HTTPException(status_code=404, detail="Facility not found")
    district = fac_row["district"]
    
    # 5. Fetch season factors
    sf_query = text("SELECT drug_category, month, factor FROM season_factor")
    sf_result = await db.execute(sf_query)
    season_factors = [dict(r) for r in sf_result.mappings().all()]
    
    # 6. Fetch disease signals (last 8 weeks, sorted desc)
    ds_query = text("""
        SELECT condition, week_start, case_count
        FROM disease_signal
        WHERE district = CAST(:district AS text)
        ORDER BY week_start DESC
        LIMIT 40
    """)
    ds_result = await db.execute(ds_query, {"district": district})
    disease_signals = [dict(r) for r in ds_result.mappings().all()]
    
    # 7. Run forecast engine
    import datetime
    current_month = datetime.date.today().month
    
    forecast_result = forecast_facility_drug(
        daily_dispensing=daily_series,
        current_stock=current_stock,
        drug_category=drug_category,
        current_month=current_month,
        season_factors=season_factors,
        disease_signals=disease_signals,
        horizon=30,
        lead_time_days=7,
    )
    
    # 8. Build history response (last 90 days)
    history_for_response = daily_series[-90:] if len(daily_series) > 90 else daily_series
    history_points = [
        ForecastHistoryPoint(date=d["date"], quantity=d["quantity"])
        for d in history_for_response
    ]
    
    # 9. Build forecast response with dates
    forecast_start = max_date + timedelta(days=1)
    forecast_points = []
    for i, fp in enumerate(forecast_result["forecast"]):
        forecast_date = forecast_start + timedelta(days=i)
        forecast_points.append(ForecastPoint(
            date=forecast_date.isoformat(),
            predicted=fp["predicted"],
            lower=fp["lower"],
            upper=fp["upper"],
        ))
    
    # 10. Stockout date
    stockout_date = None
    dts = forecast_result["days_to_stockout"]
    if dts is not None and dts < 365:
        stockout_date = (max_date + timedelta(days=int(dts))).isoformat()
    
    # 11. Cache in forecasts table
    cache_query = text("""
        INSERT INTO forecasts (facility_id, drug_id, predicted_daily_rate,
            days_to_stockout, confidence, driver_label, method_used)
        VALUES (:fid, :did, :rate, :dts, :conf, :driver, :method)
        ON CONFLICT DO NOTHING
    """)
    try:
        await db.execute(cache_query, {
            "fid": facility_id, "did": drug_id,
            "rate": forecast_result["predicted_daily_rate"],
            "dts": forecast_result["days_to_stockout"],
            "conf": forecast_result["confidence"],
            "driver": forecast_result["driver"],
            "method": forecast_result["method_used"],
        })
    except Exception:
        pass  # Cache write failure is non-fatal
    
    return ForecastResponse(
        history=history_points,
        forecast=forecast_points,
        reorder_point=forecast_result["reorder_point"],
        stockout_date=stockout_date,
        days_to_stockout=forecast_result["days_to_stockout"],
        confidence=forecast_result["confidence"],
        driver=forecast_result["driver"],
        method_used=forecast_result["method_used"],
    )


# ---------------------------------------------------------------------------
# POST /api/demo/scenario
# ---------------------------------------------------------------------------

@router.post("/demo/scenario", response_model=ScenarioResponse)
async def fire_scenario(
    request: ScenarioRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Inject an outbreak scenario by writing inflated disease case counts.
    Then invalidate cached forecasts so the next fetch recomputes.
    """
    from datetime import date as date_type, timedelta
    
    condition = request.condition.lower() if request.condition else request.condition
    multiplier = request.multiplier
    district = request.district
    
    # Validate condition
    valid_conditions = ["dengue", "malaria", "diarrhoeal", "respiratory_infection", "tuberculosis"]
    if condition not in valid_conditions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition. Must be one of: {valid_conditions}"
        )
    
    # Get the most recent week_start
    latest_query = text("""
        SELECT MAX(week_start) AS latest FROM disease_signal
        WHERE district = CAST(:district AS text)
    """)
    latest_result = await db.execute(latest_query, {"district": district})
    latest_week = latest_result.scalar()
    
    if latest_week is None:
        raise HTTPException(status_code=404, detail="No disease signals found for district")
    
    # Insert inflated signals for the last 3 weeks
    affected_count = 0
    for week_offset in range(3):
        week_start = latest_week + timedelta(weeks=week_offset + 1)
        
        # Base case count for the condition (use existing recent average)
        avg_query = text("""
            SELECT COALESCE(AVG(sub.case_count), 20) AS avg_cases
            FROM (
                SELECT case_count
                FROM disease_signal
                WHERE district = CAST(:district AS text) AND condition = CAST(:condition AS text)
                ORDER BY week_start DESC
                LIMIT 4
            ) sub
        """)
        avg_result = await db.execute(avg_query, {"district": district, "condition": condition})
        avg_cases = float(avg_result.scalar() or 20)
        
        inflated_count = int(avg_cases * multiplier)
        
        insert_query = text("""
            INSERT INTO disease_signal (district, condition, week_start, case_count, source)
            VALUES (CAST(:district AS text), CAST(:condition AS text), CAST(:week_start AS date), CAST(:case_count AS integer), CAST(:source AS text))
        """)
        await db.execute(insert_query, {
            "district": district,
            "condition": condition,
            "week_start": week_start,
            "case_count": inflated_count,
            "source": "scenario",
        })
        affected_count += 1
    
    # Invalidate cached forecasts — delete all for this district's facilities
    invalidate_query = text("""
        DELETE FROM forecasts
        WHERE facility_id IN (
            SELECT id FROM facilities WHERE district = CAST(:district AS text)
        )
    """)
    await db.execute(invalidate_query, {"district": district})
    
    # Count affected facilities (those with drugs in affected categories)
    affected_cats = CONDITION_DRUG_MAP.get(condition, [])
    if affected_cats:
        placeholders = ", ".join(f"'{c}'" for c in affected_cats)
        count_query = text(f"""
            SELECT COUNT(DISTINCT s.facility_id) AS cnt
            FROM stock s
            JOIN drugs d ON d.id = s.drug_id
            JOIN facilities f ON f.id = s.facility_id
            WHERE f.district = CAST(:district AS text)
              AND d.category IN ({placeholders})
              AND s.quantity > 0
        """)
        count_result = await db.execute(count_query, {"district": district})
        affected_facilities = count_result.scalar() or 0
    else:
        affected_facilities = 0
    
    # Batch-compute forecasts for affected facility-drug pairs
    # so that /api/risk and /api/facilities pick up the outbreak immediately
    if affected_cats:
        from datetime import date as date_type, datetime as dt_type, timedelta
        import datetime as dt_module
        
        # Get all affected facility-drug pairs
        pairs_query = text(f"""
            SELECT DISTINCT s.facility_id, s.drug_id, d.category,
                   f.district AS fac_district
            FROM stock s
            JOIN drugs d ON d.id = s.drug_id
            JOIN facilities f ON f.id = s.facility_id
            WHERE f.district = CAST(:district AS text)
              AND d.category IN ({placeholders})
              AND s.quantity > 0
        """)
        pairs_result = await db.execute(pairs_query, {"district": district})
        pairs = pairs_result.mappings().all()
        
        # Fetch shared data once
        sf_query = text("SELECT drug_category, month, factor FROM season_factor")
        sf_result = await db.execute(sf_query)
        season_factors = [dict(r) for r in sf_result.mappings().all()]
        
        ds_query = text("""
            SELECT condition, week_start, case_count
            FROM disease_signal WHERE district = CAST(:district AS text)
            ORDER BY week_start DESC LIMIT 40
        """)
        ds_result = await db.execute(ds_query, {"district": district})
        disease_signals = [dict(r) for r in ds_result.mappings().all()]
        
        current_month = dt_module.date.today().month
        
        for pair in pairs:
            fid = pair["facility_id"]
            did = pair["drug_id"]
            cat = pair["category"]
            
            # Get dispensing history
            hist_q = text("""
                SELECT DATE(t.occurred_at) AS date, SUM(t.quantity) AS quantity
                FROM transactions t
                WHERE t.facility_id = CAST(:fid AS integer) AND t.drug_id = CAST(:did AS integer)
                  AND t.type = 'dispense'
                  AND t.occurred_at >= (
                      (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '180 days'
                  )
                GROUP BY DATE(t.occurred_at)
                ORDER BY DATE(t.occurred_at) ASC
            """)
            hist_result = await db.execute(hist_q, {"fid": fid, "did": did})
            hist_rows = hist_result.mappings().all()
            
            if not hist_rows:
                continue
            
            # Build daily series
            all_dates = [row["date"] for row in hist_rows]
            min_date = min(all_dates)
            max_date = max(all_dates)
            date_qty_map = {row["date"]: int(row["quantity"]) for row in hist_rows}
            
            daily_series = []
            current = min_date
            while current <= max_date:
                daily_series.append({"date": current.isoformat(), "quantity": date_qty_map.get(current, 0)})
                current += timedelta(days=1)
            
            # Get stock
            stock_q = text("SELECT COALESCE(SUM(quantity), 0) FROM stock WHERE facility_id = CAST(:fid AS integer) AND drug_id = CAST(:did AS integer)")
            stock_val = (await db.execute(stock_q, {"fid": fid, "did": did})).scalar() or 0
            
            # Compute forecast
            fc_result = forecast_facility_drug(
                daily_dispensing=daily_series,
                current_stock=int(stock_val),
                drug_category=cat,
                current_month=current_month,
                season_factors=season_factors,
                disease_signals=disease_signals,
                horizon=30,
                lead_time_days=7,
            )
            
            # Upsert into forecasts table
            upsert_q = text("""
                INSERT INTO forecasts (facility_id, drug_id, predicted_daily_rate,
                    days_to_stockout, confidence, driver_label, method_used)
                VALUES (CAST(:fid AS integer), CAST(:did AS integer), CAST(:rate AS numeric), CAST(:dts AS integer), CAST(:conf AS numeric), CAST(:driver AS text), CAST(:method AS text))
                ON CONFLICT (facility_id, drug_id) DO UPDATE SET
                    predicted_daily_rate = EXCLUDED.predicted_daily_rate,
                    days_to_stockout = EXCLUDED.days_to_stockout,
                    confidence = EXCLUDED.confidence,
                    driver_label = EXCLUDED.driver_label,
                    method_used = EXCLUDED.method_used
            """)
            try:
                await db.execute(upsert_q, {
                    "fid": fid, "did": did,
                    "rate": fc_result["predicted_daily_rate"],
                    "dts": fc_result["days_to_stockout"],
                    "conf": fc_result["confidence"],
                    "driver": fc_result["driver"],
                    "method": fc_result["method_used"],
                })
            except Exception as e:
                print(f"UPSERT ERROR: {e}")
    
    return ScenarioResponse(
        affected=affected_facilities,
        condition=condition,
        multiplier=multiplier,
    )


# ---------------------------------------------------------------------------
# POST /api/demo/reset
# ---------------------------------------------------------------------------

@router.post("/demo/reset")
async def reset_demo(
    db: AsyncSession = Depends(get_db),
):
    """
    Restore seed state exactly.
    Truncates scenario-injected signals and forecast cache,
    then re-inserts original seed data.
    """
    import json
    
    # Docker mounts data/ at /data; local dev has it relative
    DATA_DIR = "/data/generated" if os.path.isdir("/data/generated") else os.path.join(os.path.dirname(__file__), "..", "..", "data", "generated")
    
    # 1. Delete all disease signals and re-insert from seed
    await db.execute(text("DELETE FROM disease_signal"))
    await db.execute(text("DELETE FROM forecasts"))
    
    # 2. Reload disease_signal from generated JSON
    ds_path = os.path.join(DATA_DIR, "disease_signal.json")
    if os.path.exists(ds_path):
        from datetime import date as date_type
        with open(ds_path) as f:
            signals = json.load(f)
        for s in signals:
            # Parse week_start string to date object (asyncpg needs native types)
            ws = s["week_start"]
            if isinstance(ws, str):
                ws = date_type.fromisoformat(ws)
            insert_q = text("""
                INSERT INTO disease_signal (district, condition, week_start, case_count, source)
                VALUES (CAST(:district AS text), CAST(:condition AS text), CAST(:week_start AS date), CAST(:case_count AS integer), CAST(:source AS text))
            """)
            await db.execute(insert_q, {
                "district": s["district"],
                "condition": s["condition"],
                "week_start": ws,
                "case_count": s["case_count"],
                "source": s.get("source", "IDSP"),
            })
    
    # 3. Reload season_factor from generated JSON
    await db.execute(text("DELETE FROM season_factor"))
    sf_path = os.path.join(DATA_DIR, "season_factor.json")
    if os.path.exists(sf_path):
        with open(sf_path) as f:
            factors = json.load(f)
        for sf in factors:
            insert_q = text("""
                INSERT INTO season_factor (drug_category, month, factor)
                VALUES (:drug_category, :month, :factor)
            """)
            await db.execute(insert_q, {
                "drug_category": sf["drug_category"],
                "month": sf["month"],
                "factor": sf["factor"],
            })
    
    return {"status": "reset", "message": "Seed state restored"}


# ===========================================================================
# PHASE 3 — Transfer Optimizer Endpoints
# ===========================================================================

from schemas import (
    PlanRequest,
    PlanResponse,
    TransferProposalItem,
    PlanImpact,
    ApproveTransfersRequest,
    ApproveTransfersResponse,
    TransferItem,
    TransferListResponse,
)
from optimizer.engine import optimize_transfers


@router.post("/plan", response_model=PlanResponse)
async def generate_plan(
    request: PlanRequest = PlanRequest(),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an intra-district stock redistribution plan using OR-Tools min-cost flow.
    Surplus: >60 days cover (leaves >= 30 days cover at source).
    Deficit: <15 days cover (restores to 45 days cover).
    Cold-chain constraint strictly enforced.
    Honest before/after breach impact calculated.
    """
    district = request.district
    max_radius = request.max_radius_km or 65.0

    # 1. Fetch facilities in district
    fac_q = text("""
        SELECT id, name, type, lat, lng, cold_chain_capable, district
        FROM facilities
        WHERE district = :district
    """)
    fac_res = await db.execute(fac_q, {"district": district})
    facilities = [dict(r) for r in fac_res.mappings().all()]

    if not facilities:
        raise HTTPException(status_code=404, detail=f"No facilities found for district {district}")

    # 2. Fetch all drugs
    drug_q = text("""
        SELECT id, name, unit, category, is_essential, is_cold_chain, shelf_life_months
        FROM drugs
    """)
    drug_res = await db.execute(drug_q)
    drugs = [dict(r) for r in drug_res.mappings().all()]

    # 3. Fetch stock records
    stock_q = text("""
        SELECT s.facility_id, s.drug_id, s.quantity, s.expiry_date
        FROM stock s
        JOIN facilities f ON f.id = s.facility_id
        WHERE f.district = :district
    """)
    stock_res = await db.execute(stock_q, {"district": district})
    stock_records = [dict(r) for r in stock_res.mappings().all()]

    # 4. Fetch burn rates / predicted rates
    # First get predicted rates from forecasts table
    fc_q = text("""
        SELECT fc.facility_id, fc.drug_id, fc.predicted_daily_rate
        FROM forecasts fc
        JOIN facilities f ON f.id = fc.facility_id
        WHERE f.district = :district AND fc.predicted_daily_rate IS NOT NULL
    """)
    fc_res = await db.execute(fc_q, {"district": district})
    fc_map = {(r["facility_id"], r["drug_id"]): float(r["predicted_daily_rate"]) for r in fc_res.mappings().all()}

    # Then get 30-day dispensing burn rates as fallback/baseline
    burn_q = text("""
        SELECT t.facility_id, t.drug_id,
               COALESCE(SUM(t.quantity), 0)::float / 30.0 AS burn_rate
        FROM transactions t
        JOIN facilities f ON f.id = t.facility_id
        WHERE f.district = :district
          AND t.type = 'dispense'
          AND t.occurred_at >= (
              (SELECT MAX(occurred_at) FROM transactions) - INTERVAL '30 days'
          )
        GROUP BY t.facility_id, t.drug_id
    """)
    burn_res = await db.execute(burn_q, {"district": district})
    burn_rates = {}
    for r in burn_res.mappings().all():
        key = (r["facility_id"], r["drug_id"])
        rate = float(r["burn_rate"] or 0.0)
        # Use forecast predicted rate if available and > 0, else 30-day burn rate
        if key in fc_map and fc_map[key] > 0:
            burn_rates[key] = fc_map[key]
        else:
            burn_rates[key] = rate

    # Also include any forecast entries not in 30-day dispensing
    for key, rate in fc_map.items():
        if key not in burn_rates and rate > 0:
            burn_rates[key] = rate

    # 5. Run OR-Tools optimizer
    plan_result = optimize_transfers(
        facilities=facilities,
        drugs=drugs,
        stock_records=stock_records,
        burn_rates=burn_rates,
        max_radius_km=max_radius,
    )

    transfer_items = [
        TransferProposalItem(
            from_facility_id=t["fromFacilityId"],
            from_name=t["fromName"],
            to_facility_id=t["toFacilityId"],
            to_name=t["toName"],
            drug_id=t["drugId"],
            drug_name=t["drugName"],
            unit=t["unit"],
            is_cold_chain=t["isColdChain"],
            quantity=t["quantity"],
            distance_km=t["distanceKm"],
            cost_paise=t["costPaise"],
            cover_restored_days=t["coverRestoredDays"],
            expiry_saved_paise=t["expirySavedPaise"],
        )
        for t in plan_result["transfers"]
    ]

    impact_item = PlanImpact(
        breaches_before=plan_result["impact"]["breachesBefore"],
        breaches_after=plan_result["impact"]["breachesAfter"],
        total_cost_paise=plan_result["impact"]["totalCostPaise"],
        expiry_avoided_paise=plan_result["impact"]["expiryAvoidedPaise"],
    )

    return PlanResponse(
        plan_id=plan_result["planId"],
        transfers=transfer_items,
        impact=impact_item,
    )

# ---------------------------------------------------------------------------
# Phase 4 — Scan and Sync
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=dict)
async def scan_register(image: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    """
    Scan a paper register using Gemini API.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key in ["your-key-here", "your_api_key_here"]:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured in backend .env file")
        
    genai.configure(api_key=api_key)
    
    try:
        image_bytes = await image.read()
        model = genai.GenerativeModel('gemini-3.1-flash-lite', generation_config={"response_mime_type": "application/json"})
        
        prompt = '''
        You are a medical data extraction assistant. Extract rows of drug stock information from this register image.
        Return ONLY a JSON array of objects. Each object must have:
        - raw_text: The raw text of the drug name exactly as written
        - quantity: The quantity (integer)
        - expiry_date: The expiry date (YYYY-MM-DD format)
        - confidence: A confidence score between 0.0 and 1.0 representing how clearly you could read this row
        - uncertain_fields: An array of strings representing field names (like "quantity", "expiryDate") that were hard to read or blurry.
        If you are unsure of a field, make your best guess but include it in uncertain_fields.
        '''
        
        response = await model.generate_content_async([
            prompt,
            {"mime_type": image.content_type or "image/jpeg", "data": image_bytes}
        ])
        
        extracted_data = json.loads(response.text)
    except Exception as e:
        print(f"Gemini API Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image with Gemini")
        
    # Fetch all drugs to fuzzy match
    drugs_query = text("SELECT id, name FROM drugs")
    drugs_res = await db.execute(drugs_query)
    all_drugs = [{"id": row[0], "name": row[1]} for row in drugs_res.all()]
    drug_names = [d["name"].lower() for d in all_drugs]
    
    rows = []
    for item in extracted_data:
        raw_name = item.get("raw_text", "")
        matched_name = None
        drug_id = None
        
        # Fuzzy match
        matches = difflib.get_close_matches(raw_name.lower(), drug_names, n=1, cutoff=0.6)
        if matches:
            matched_drug = next((d for d in all_drugs if d["name"].lower() == matches[0]), None)
            if matched_drug:
                matched_name = matched_drug["name"]
                drug_id = matched_drug["id"]
                
        rows.append({
            "drugId": drug_id,
            "matchedName": matched_name,
            "rawText": raw_name,
            "batchNo": "",
            "quantity": int(item.get("quantity", 0)),
            "expiryDate": item.get("expiry_date", "2027-01-01"),
            "confidence": item.get("confidence", 0.9),
            "uncertainFields": item.get("uncertain_fields", [])
        })
        
    return {"rows": rows}


@router.post("/scan/confirm", response_model=dict)
async def confirm_scan(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Confirm scanned rows and update stock.
    """
    rows = payload.get("rows", [])
    if not rows:
        return {"status": "success", "updated": 0}
        
    try:
        # We'll just hardcode facility_id=1 (PHC Dhamnod) for the demo
        facility_id = 1
        
        for row in rows:
            drug_id = row.get("drugId")
            matched_name = row.get("matchedName")
            if not drug_id and not matched_name:
                continue
                
            if not drug_id and matched_name:
                # Create a new drug with defaults
                insert_drug_q = text("""
                    INSERT INTO drugs (name, salt, strength, form, unit, category, is_essential, is_cold_chain, shelf_life_months, atc_class)
                    VALUES (:name, 'Unknown', 'Unknown', 'Unknown', 'tab', 'Uncategorized', false, false, 24, 'Unknown')
                    RETURNING id
                """)
                res = await db.execute(insert_drug_q, {"name": matched_name})
                drug_id = res.scalar()
                
            qty = row.get("quantity", 0)
            batch = row.get("batchNo")
            if not batch:
                batch = "UNKNOWN"
            
            exp = row.get("expiryDate")
            if not exp:
                exp = "2027-01-01"
            
            # asyncpg requires actual datetime.date objects for date columns
            from datetime import datetime
            try:
                exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            except ValueError:
                exp_date = datetime.strptime("2027-01-01", "%Y-%m-%d").date()
            
            # Upsert into stock
            upsert_q = text("""
                INSERT INTO stock (facility_id, drug_id, batch_no, quantity, expiry_date, trust_score)
                VALUES (:fid, :did, :batch, :qty, :exp, :trust)
                ON CONFLICT (facility_id, drug_id) DO UPDATE SET
                    quantity = stock.quantity + EXCLUDED.quantity,
                    last_updated = now()
            """)
            # Note: the actual ON CONFLICT requires the index ix_stock_facility_drug
            # But ix_stock_facility_drug is just an index, not a unique constraint!
            # Let's do a simple update or insert.
            
            # Check if exists
            check_q = text("SELECT id, quantity FROM stock WHERE facility_id = :fid AND drug_id = :did LIMIT 1")
            existing = await db.execute(check_q, {"fid": facility_id, "did": drug_id})
            existing_row = existing.first()
            
            if existing_row:
                update_q = text("UPDATE stock SET quantity = quantity + :qty, last_updated = now() WHERE id = :id")
                await db.execute(update_q, {"qty": qty, "id": existing_row[0]})
            else:
                insert_q = text("""
                    INSERT INTO stock (facility_id, drug_id, batch_no, quantity, expiry_date, trust_score)
                    VALUES (:fid, :did, :batch, :qty, :exp, 1.0)
                """)
                await db.execute(insert_q, {"fid": facility_id, "did": drug_id, "batch": batch, "qty": qty, "exp": exp_date})
                
            # Add transaction
            tx_q = text("""
                INSERT INTO transactions (facility_id, drug_id, batch_no, quantity, type, occurred_at, source)
                VALUES (:fid, :did, :batch, :qty, 'receive', now(), 'scan')
            """)
            await db.execute(tx_q, {"fid": facility_id, "did": drug_id, "batch": batch, "qty": qty})
            
        await db.commit()
        return {"status": "success", "updated": len(rows)}
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync", response_model=dict)
async def sync_mutations(payload: dict, db: AsyncSession = Depends(get_db)):
    """
    Sync offline mutations from the PHC app.
    """
    mutations = payload.get("mutations", [])
    if not mutations:
        return {"applied": 0, "conflicts": 0}
        
    applied = 0
    conflicts = 0
    
    try:
        for m in mutations:
            fid = m.get("facilityId")
            did = m.get("drugId")
            qty = m.get("quantity")
            mtype = m.get("type", "dispense")
            batch = m.get("batchNo", "UNKNOWN")
            
            # Update stock
            check_q = text("SELECT id, quantity FROM stock WHERE facility_id = :fid AND drug_id = :did LIMIT 1")
            existing = await db.execute(check_q, {"fid": fid, "did": did})
            existing_row = existing.first()
            
            if existing_row:
                new_qty = existing_row[1] - qty if mtype == 'dispense' else existing_row[1] + qty
                if new_qty < 0: new_qty = 0
                
                update_q = text("UPDATE stock SET quantity = :new_qty, last_updated = now() WHERE id = :id")
                await db.execute(update_q, {"new_qty": new_qty, "id": existing_row[0]})
            else:
                if mtype == 'receive':
                    insert_q = text("""
                        INSERT INTO stock (facility_id, drug_id, batch_no, quantity, expiry_date, trust_score)
                        VALUES (:fid, :did, :batch, :qty, now() + interval '1 year', 1.0)
                    """)
                    await db.execute(insert_q, {"fid": fid, "did": did, "batch": batch, "qty": qty})
            
            # Add transaction
            tx_q = text("""
                INSERT INTO transactions (facility_id, drug_id, batch_no, quantity, type, occurred_at, source)
                VALUES (:fid, :did, :batch, :qty, :type, now(), 'sync')
            """)
            await db.execute(tx_q, {"fid": fid, "did": did, "batch": batch, "qty": qty, "type": mtype})
            
            applied += 1
            
        await db.commit()
        return {"applied": applied, "conflicts": conflicts}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transfers/approve", response_model=ApproveTransfersResponse)
async def approve_transfers(
    request: ApproveTransfersRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Approve proposed transfer plan or selected transfers.
    Writes rows to transfers table with status='approved' and generates records.
    """
    approved_count = 0

    if request.transfers:
        for t in request.transfers:
            insert_q = text("""
                INSERT INTO transfers (
                    from_facility_id, to_facility_id, drug_id, quantity,
                    status, proposed_at, approved_at, approved_by_role,
                    distance_km, cost_paise, plan_id
                ) VALUES (
                    :from_fid, :to_fid, :did, :qty,
                    'approved', NOW(), NOW(), 'cmho',
                    :dist, :cost, :plan_id
                )
            """)
            await db.execute(insert_q, {
                "from_fid": t.from_facility_id,
                "to_fid": t.to_facility_id,
                "did": t.drug_id,
                "qty": t.quantity,
                "dist": t.distance_km,
                "cost": t.cost_paise,
                "plan_id": request.plan_id,
            })
            approved_count += 1

    elif request.transfer_ids:
        update_q = text("""
            UPDATE transfers
            SET status = 'approved', approved_at = NOW(), approved_by_role = 'cmho'
            WHERE id = ANY(:tids)
        """)
        res = await db.execute(update_q, {"tids": request.transfer_ids})
        approved_count = res.rowcount or len(request.transfer_ids)

    return ApproveTransfersResponse(
        status="approved",
        plan_id=request.plan_id,
        approved_count=approved_count,
    )


@router.get("/transfers", response_model=TransferListResponse)
async def list_transfers(
    facility_id: Optional[int] = Query(None, alias="facilityId"),
    status: Optional[str] = None,
    plan_id: Optional[str] = Query(None, alias="planId"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List recorded transfers with facility and drug details.
    """
    query = text("""
        SELECT
            t.id,
            t.plan_id,
            t.from_facility_id,
            f1.name AS from_name,
            t.to_facility_id,
            f2.name AS to_name,
            t.drug_id,
            d.name AS drug_name,
            t.quantity,
            t.status,
            t.proposed_at,
            t.approved_at,
            t.approved_by_role,
            t.distance_km,
            t.cost_paise
        FROM transfers t
        JOIN facilities f1 ON f1.id = t.from_facility_id
        JOIN facilities f2 ON f2.id = t.to_facility_id
        JOIN drugs d ON d.id = t.drug_id
        WHERE (CAST(:fid AS int) IS NULL OR t.from_facility_id = :fid OR t.to_facility_id = :fid)
          AND (CAST(:status AS text) IS NULL OR CAST(t.status AS text) = :status)
          AND (CAST(:plan_id AS text) IS NULL OR t.plan_id = :plan_id)
        ORDER BY t.proposed_at DESC
        LIMIT :limit OFFSET :offset
    """)

    count_q = text("""
        SELECT COUNT(*)
        FROM transfers t
        WHERE (CAST(:fid AS int) IS NULL OR t.from_facility_id = :fid OR t.to_facility_id = :fid)
          AND (CAST(:status AS text) IS NULL OR CAST(t.status AS text) = :status)
          AND (CAST(:plan_id AS text) IS NULL OR t.plan_id = :plan_id)
    """)

    params = {
        "fid": facility_id,
        "status": status,
        "plan_id": plan_id,
        "limit": limit,
        "offset": offset,
    }

    res = await db.execute(query, params)
    rows = res.mappings().all()

    total_res = await db.execute(count_q, {
        "fid": facility_id,
        "status": status,
        "plan_id": plan_id,
    })
    total = total_res.scalar() or 0

    items = [
        TransferItem(
            id=r["id"],
            plan_id=r["plan_id"],
            from_facility_id=r["from_facility_id"],
            from_name=r["from_name"],
            to_facility_id=r["to_facility_id"],
            to_name=r["to_name"],
            drug_id=r["drug_id"],
            drug_name=r["drug_name"],
            quantity=r["quantity"],
            status=r["status"],
            proposed_at=r["proposed_at"],
            approved_at=r["approved_at"],
            approved_by_role=r["approved_by_role"],
            distance_km=r["distance_km"],
            cost_paise=r["cost_paise"],
        )
        for r in rows
    ]

    return TransferListResponse(items=items, total=total)

