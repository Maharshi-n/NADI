"""
Create all tables from models.py.
Run directly: python migration.py
"""

import sys
import os

# Allow imports from this directory
sys.path.insert(0, os.path.dirname(__file__))

from db import sync_engine
from models import Base


def create_all():
    """Create all tables. Safe to run repeatedly — skips existing tables."""
    print("Creating tables...")
    Base.metadata.create_all(bind=sync_engine)
    table_names = sorted(Base.metadata.tables.keys())
    print(f"  {len(table_names)} tables: {', '.join(table_names)}")
    print("Done.")


def drop_all():
    """Drop all tables. Destructive — use with care."""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=sync_engine)
    print("Done.")


if __name__ == "__main__":
    if "--drop" in sys.argv:
        drop_all()
    create_all()
