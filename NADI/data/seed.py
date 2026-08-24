"""
NADI seed loader — loads generated JSON into Postgres.
Idempotent. Use --reset to truncate and re-seed.

Usage:
    python data/seed.py --reset          # wipe and reload
    python data/seed.py                  # insert only if tables are empty
    python data/seed.py --generate       # regenerate then seed
"""

import argparse, json, os, sys
from datetime import date, datetime

# Add apps/api to path for model imports
API_DIR = os.path.join(os.path.dirname(__file__), "..", "apps", "api")
sys.path.insert(0, os.path.abspath(API_DIR))

from db import sync_engine, SyncSessionLocal
from models import (
    Base, Facility, Drug, Stock, Transaction, Transfer,
    BedEvent, StaffDaily, Footfall, DiseaseSignal, SeasonFactor,
    Forecast, CapacityScore, FlRound, FlClient, Anomaly,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "generated")

TABLE_MAP = {
    "facilities": Facility,
    "drugs": Drug,
    "stock": Stock,
    "transactions": Transaction,
    "staff_daily": StaffDaily,
    "bed_events": BedEvent,
    "footfall": Footfall,
    "disease_signal": DiseaseSignal,
    "season_factor": SeasonFactor,
}

# Fields that need date/datetime parsing
DATETIME_FIELDS = {"occurred_at", "recorded_at", "proposed_at", "approved_at", "computed_at",
                   "started_at", "completed_at", "detected_at", "last_updated"}
DATE_FIELDS = {"date", "week_start", "expiry_date"}


def parse_row(row):
    """Convert date/datetime strings to Python objects."""
    parsed = {}
    for k, v in row.items():
        if v is None:
            parsed[k] = None
        elif k in DATETIME_FIELDS and isinstance(v, str):
            parsed[k] = datetime.fromisoformat(v)
        elif k in DATE_FIELDS and isinstance(v, str):
            parsed[k] = date.fromisoformat(v)
        else:
            parsed[k] = v
    return parsed


def load_json(name):
    path = os.path.join(DATA_DIR, f"{name}.json")
    if not os.path.exists(path):
        print(f"  SKIP {name}: {path} not found")
        return []
    with open(path) as f:
        return json.load(f)


def reset_db():
    """Drop and recreate all tables."""
    print("Resetting database...")
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)
    print("  Tables recreated.")


def seed():
    """Load generated data into the database."""
    # Ensure tables exist
    Base.metadata.create_all(bind=sync_engine)

    session = SyncSessionLocal()
    try:
        # Check if already seeded
        existing = session.query(Facility).count()
        if existing > 0:
            print(f"  Database already has {existing} facilities. Use --reset to re-seed.")
            return

        total = 0
        for table_name, model_cls in TABLE_MAP.items():
            rows = load_json(table_name)
            if not rows:
                continue
            objects = [model_cls(**parse_row(r)) for r in rows]
            session.bulk_save_objects(objects)
            session.flush()
            count = len(objects)
            total += count
            print(f"  {table_name}: {count} rows")

        session.commit()
        print(f"\nSeeded {total} total rows.")

        # Report counts
        print("\nRow counts:")
        for table_name, model_cls in TABLE_MAP.items():
            count = session.query(model_cls).count()
            print(f"  {table_name}: {count}")

    except Exception as e:
        session.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed NADI database")
    parser.add_argument("--reset", action="store_true", help="Truncate all tables before seeding")
    parser.add_argument("--generate", action="store_true", help="Run generator before seeding")
    parser.add_argument("--seed-val", type=int, default=42, help="RNG seed for generator")
    args = parser.parse_args()

    if args.generate:
        print("Running generator...")
        sys.path.insert(0, os.path.dirname(__file__))
        from generator import generate, save
        data = generate(args.seed_val)
        save(data, DATA_DIR)
        print()

    if args.reset:
        reset_db()

    print("Seeding database...")
    seed()
    print("Done.")
