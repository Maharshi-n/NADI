import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def main():
    engine = create_async_engine('postgresql+asyncpg://nadi:nadi@db:5432/nadi')
    async with engine.connect() as conn:
        q = text('''
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
        SELECT f.id, w.worst_days
        FROM facilities f
        LEFT JOIN worst w ON f.id = w.facility_id
        ORDER BY w.worst_days ASC
        LIMIT 5;
        ''')
        res = await conn.execute(q)
        rows = res.mappings().all()
        for r in rows:
            print(f"ID: {r['id']}, worst: {r['worst_days']}, type: {type(r['worst_days'])}")

asyncio.run(main())
