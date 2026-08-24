"""
SQLAlchemy ORM models — every table from DATA_MODEL.md.

All tables created in Phase 0 even if not used until later phases.
Schema is frozen after Phase 0; additive columns OK, renames/drops
require a HANDOFF.md warning.
"""

from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

class Facility(Base):
    """PHCs, CHCs, warehouses."""
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    type = Column(
        Enum("phc", "chc", "dh", "warehouse", name="facility_type"),
        nullable=False,
    )
    district = Column(String(100), nullable=False)
    block = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    hfr_code = Column(String(50), nullable=True)
    beds_total = Column(Integer, nullable=False, default=0)
    cold_chain_capable = Column(Boolean, nullable=False, default=False)
    population_served = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Drug(Base):
    """The master drug list. Nothing outside this table can enter stock."""
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    salt = Column(String(200), nullable=False)
    strength = Column(String(50), nullable=False)
    form = Column(String(50), nullable=False)
    unit = Column(
        Enum("tab", "cap", "sachet", "vial", "ml", name="drug_unit"),
        nullable=False,
    )
    category = Column(String(100), nullable=False)
    is_essential = Column(Boolean, nullable=False, default=False)
    is_cold_chain = Column(Boolean, nullable=False, default=False)
    shelf_life_months = Column(Integer, nullable=False, default=24)
    atc_class = Column(String(20), nullable=True)


class Stock(Base):
    """Current holdings, one row per facility/drug/batch."""
    __tablename__ = "stock"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    batch_no = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    expiry_date = Column(Date, nullable=False)
    last_updated = Column(DateTime, nullable=False, server_default=func.now())
    trust_score = Column(Float, nullable=False, default=1.0)

    __table_args__ = (
        Index("ix_stock_facility_drug", "facility_id", "drug_id"),
    )


class Transaction(Base):
    """
    The event log everything is derived from.
    occurred_at vs recorded_at enables backdated-edit detection (Phase 7).
    prev_hash/hash form the append-only chain.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    batch_no = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    type = Column(
        Enum(
            "receive", "dispense", "transfer_in", "transfer_out",
            "adjust", "expire",
            name="transaction_type",
        ),
        nullable=False,
    )
    occurred_at = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, nullable=False, server_default=func.now())
    recorded_by_role = Column(String(50), nullable=True)
    source = Column(
        Enum("app", "scan", "sync", "seed", name="transaction_source"),
        nullable=False,
        default="seed",
    )
    prev_hash = Column(String(64), nullable=True)
    hash = Column(String(64), nullable=True)

    __table_args__ = (
        Index(
            "ix_transactions_facility_drug_date",
            "facility_id", "drug_id", "occurred_at",
            postgresql_ops={"occurred_at": "DESC"},
        ),
    )


class Transfer(Base):
    """Transfer proposals and their lifecycle."""
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    from_facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    to_facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(
        Enum(
            "proposed", "approved", "dispatched", "received", "rejected",
            name="transfer_status",
        ),
        nullable=False,
        default="proposed",
    )
    proposed_at = Column(DateTime, nullable=False, server_default=func.now())
    approved_at = Column(DateTime, nullable=True)
    approved_by_role = Column(String(50), nullable=True)
    distance_km = Column(Float, nullable=True)
    cost_paise = Column(Integer, nullable=True)
    plan_id = Column(String(50), nullable=True)


# ---------------------------------------------------------------------------
# Capacity (Phase 5)
# ---------------------------------------------------------------------------

class BedEvent(Base):
    """Occupancy is derived from events, never typed directly."""
    __tablename__ = "bed_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    type = Column(
        Enum("admit", "discharge", name="bed_event_type"),
        nullable=False,
    )
    occurred_at = Column(DateTime, nullable=False)
    recorded_at = Column(DateTime, nullable=False, server_default=func.now())


class StaffDaily(Base):
    """Role counts only. Never individual identities."""
    __tablename__ = "staff_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    date = Column(Date, nullable=False)
    role = Column(
        Enum("doctor", "pharmacist", "nurse", "anm", "lab", name="staff_role"),
        nullable=False,
    )
    required = Column(Integer, nullable=False, default=1)
    present = Column(Integer, nullable=False, default=1)
    source = Column(
        Enum("system", "checkin", "inferred", name="staff_source"),
        nullable=False,
        default="system",
    )


class Footfall(Base):
    __tablename__ = "footfall"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    date = Column(Date, nullable=False)
    patients = Column(Integer, nullable=False, default=0)
    referrals_out = Column(Integer, nullable=False, default=0)
    referrals_in = Column(Integer, nullable=False, default=0)


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class DiseaseSignal(Base):
    __tablename__ = "disease_signal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district = Column(String(100), nullable=False)
    condition = Column(String(100), nullable=False)
    week_start = Column(Date, nullable=False)
    case_count = Column(Integer, nullable=False, default=0)
    source = Column(String(50), nullable=True)

    __table_args__ = (
        Index(
            "ix_disease_signal_district_week",
            "district", "week_start",
            postgresql_ops={"week_start": "DESC"},
        ),
    )


class SeasonFactor(Base):
    """Lookup, not learned."""
    __tablename__ = "season_factor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    drug_category = Column(String(100), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    factor = Column(Float, nullable=False, default=1.0)


# ---------------------------------------------------------------------------
# Derived / cache
# ---------------------------------------------------------------------------

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=False)
    computed_at = Column(DateTime, nullable=False, server_default=func.now())
    predicted_daily_rate = Column(Float, nullable=True)
    days_to_stockout = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)
    driver_label = Column(String(200), nullable=True)
    method_used = Column(String(50), nullable=True)

    __table_args__ = (
        Index("ix_forecasts_facility_stockout", "facility_id", "days_to_stockout"),
    )


class CapacityScore(Base):
    __tablename__ = "capacity_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    computed_at = Column(DateTime, nullable=False, server_default=func.now())
    medicine_score = Column(Float, nullable=True)
    bed_score = Column(Float, nullable=True)
    staff_score = Column(Float, nullable=True)
    cbi = Column(Float, nullable=True)
    bottleneck = Column(
        Enum("medicine", "beds", "staff", name="bottleneck_type"),
        nullable=True,
    )


# ---------------------------------------------------------------------------
# Federation (Phase 6)
# ---------------------------------------------------------------------------

class FlRound(Base):
    __tablename__ = "fl_rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    round_no = Column(Integer, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    aggregation_method = Column(String(50), nullable=True)
    clients_participating = Column(Integer, nullable=True)
    bytes_transferred = Column(Integer, nullable=True)
    tensor_count = Column(Integer, nullable=True)
    global_accuracy = Column(Float, nullable=True)
    baseline_accuracy = Column(Float, nullable=True)
    # Zero columns exist so the UI reads them from the DB, not hardcoded
    patient_records_transferred = Column(Integer, nullable=False, default=0)
    stock_rows_transferred = Column(Integer, nullable=False, default=0)


class FlClient(Base):
    __tablename__ = "fl_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state_name = Column(String(100), nullable=False)
    sample_count = Column(Integer, nullable=True)
    last_round = Column(Integer, nullable=True)
    model_version = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)


# ---------------------------------------------------------------------------
# Trust (Phase 7)
# ---------------------------------------------------------------------------

class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"), nullable=False)
    drug_id = Column(Integer, ForeignKey("drugs.id"), nullable=True)
    detected_at = Column(DateTime, nullable=False, server_default=func.now())
    rule = Column(
        Enum(
            "benford", "impossible_rate", "backdated", "expiry_cluster",
            name="anomaly_rule",
        ),
        nullable=False,
    )
    confidence = Column(Float, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    note = Column(Text, nullable=True)
