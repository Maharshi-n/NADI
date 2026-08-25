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
    Risk queue — ranked ascending by days of cover.
    Phase 1: days_to_stockout = days_of_cover (no forecasting yet).
    Bottleneck is always 'medicine' at this stage.
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
            c.days_of_cover AS days_to_stockout
        FROM cover c
        JOIN facilities f ON f.id = c.facility_id
        JOIN drugs d ON d.id = c.drug_id
        WHERE c.days_of_cover IS NOT NULL
          AND (CAST(:district AS text) IS NULL OR f.district = :district)
        ORDER BY c.days_of_cover ASC
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
            confidence=None,  # Phase 1: no forecasting
            driver=None,      # Phase 1: no forecasting
            bottleneck="medicine",  # Phase 1: always medicine
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
