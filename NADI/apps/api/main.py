"""
NADI API — FastAPI application.

Demo mode is a first-class feature: no auth, role switcher in header,
auto-seed on startup if DB is empty. Phase 2: auto-compute forecasts.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Allow imports from this directory
sys.path.insert(0, os.path.dirname(__file__))

from db import async_engine, AsyncSessionLocal
from models import Base, Facility, Forecast
from routes import router as api_router, compute_all_forecasts


@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup: create tables, auto-seed if empty, compute forecasts."""
    # Create tables (safe if they already exist)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Check if DB needs seeding
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select, func
        result = await session.execute(select(func.count()).select_from(Facility))
        count = result.scalar()
        if count == 0:
            print("DB is empty — run 'python data/seed.py --reset' to seed.")
        else:
            # Auto-compute forecasts if forecasts table is empty
            fc_result = await session.execute(select(func.count()).select_from(Forecast))
            fc_count = fc_result.scalar()
            if fc_count == 0:
                print("Computing initial forecasts...")
                computed = await compute_all_forecasts(session)
                print(f"  Computed {computed} forecasts.")

    yield

    # Shutdown
    await async_engine.dispose()


app = FastAPI(
    title="NADI API",
    description="Predicts PHC capacity shortages and proposes transfers.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Demo mode — no auth
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes (Phase 1 + Phase 2)
app.include_router(api_router)


@app.get("/api/health")
async def health():
    """Health check."""
    return {"status": "ok", "phase": 2}
