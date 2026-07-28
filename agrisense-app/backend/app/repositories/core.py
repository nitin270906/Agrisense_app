"""Repository layer — the only place that talks to SQLAlchemy.

Routers and services never build queries themselves. That boundary is what keeps
the "SQLite now, Postgres later" claim honest: swapping the backend means
rewriting this file and nothing above it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    CropProfile,
    Farm,
    Field,
    Prediction,
    Recommendation,
    SensorReading,
)


# --- crop profiles ---------------------------------------------------------- #
def list_crop_profiles(db: Session) -> list[CropProfile]:
    return list(db.scalars(select(CropProfile).order_by(CropProfile.display_name)))


def get_crop_profile(db: Session, crop: str) -> CropProfile | None:
    return db.get(CropProfile, crop)


# --- farms ------------------------------------------------------------------ #
def list_farms(db: Session) -> list[Farm]:
    return list(db.scalars(select(Farm).order_by(Farm.name)))


def get_farm(db: Session, farm_id: int) -> Farm | None:
    return db.get(Farm, farm_id)


def create_farm(db: Session, **kwargs) -> Farm:
    farm = Farm(**kwargs)
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


def count_fields_by_farm(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(Field.farm_id, func.count(Field.id)).group_by(Field.farm_id)
    ).all()
    return {farm_id: count for farm_id, count in rows}


# --- fields ----------------------------------------------------------------- #
def list_fields(db: Session, farm_id: int | None = None) -> list[Field]:
    stmt = select(Field).order_by(Field.name)
    if farm_id is not None:
        stmt = stmt.where(Field.farm_id == farm_id)
    return list(db.scalars(stmt))


def get_field(db: Session, field_id: int) -> Field | None:
    return db.get(Field, field_id)


def create_field(db: Session, **kwargs) -> Field:
    field = Field(**kwargs)
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


# --- sensor readings -------------------------------------------------------- #
def list_readings(db: Session, field_id: int, days: int = 90) -> list[SensorReading]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(SensorReading)
        .where(SensorReading.field_id == field_id, SensorReading.ts >= cutoff)
        .order_by(SensorReading.ts)
    )
    return list(db.scalars(stmt))


def latest_reading(db: Session, field_id: int) -> SensorReading | None:
    stmt = (
        select(SensorReading)
        .where(SensorReading.field_id == field_id)
        .order_by(SensorReading.ts.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def add_reading(db: Session, field_id: int, **kwargs) -> SensorReading:
    reading = SensorReading(field_id=field_id, **kwargs)
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def bulk_add_readings(db: Session, readings: list[SensorReading]) -> None:
    db.add_all(readings)
    db.commit()


# --- predictions ------------------------------------------------------------ #
def save_prediction(db: Session, **kwargs) -> Prediction:
    prediction = Prediction(**kwargs)
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def latest_prediction(db: Session, field_id: int) -> Prediction | None:
    stmt = (
        select(Prediction)
        .where(Prediction.field_id == field_id)
        .order_by(Prediction.ts.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def latest_predictions_for_fields(db: Session, field_ids: list[int]) -> dict[int, Prediction]:
    """Most recent prediction per field, in one pass.

    Avoids the N+1 query that would otherwise fire once per field when the
    dashboard renders a farm with dozens of plots.
    """
    if not field_ids:
        return {}
    newest = (
        select(Prediction.field_id, func.max(Prediction.ts).label("ts"))
        .where(Prediction.field_id.in_(field_ids))
        .group_by(Prediction.field_id)
        .subquery()
    )
    stmt = select(Prediction).join(
        newest,
        (Prediction.field_id == newest.c.field_id) & (Prediction.ts == newest.c.ts),
    )
    return {p.field_id: p for p in db.scalars(stmt)}


def list_predictions(db: Session, field_id: int, days: int = 90) -> list[Prediction]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(Prediction)
        .where(Prediction.field_id == field_id, Prediction.ts >= cutoff)
        .order_by(Prediction.ts)
    )
    return list(db.scalars(stmt))


# --- recommendations -------------------------------------------------------- #
def replace_recommendations(
    db: Session, field_id: int, recommendations: list[Recommendation]
) -> list[Recommendation]:
    """Swap in a fresh recommendation set for a field.

    Recommendations are derived state, not history: stale advice sitting next to
    current advice is worse than no advice, so the previous set is cleared.
    """
    db.execute(delete(Recommendation).where(Recommendation.field_id == field_id))
    db.add_all(recommendations)
    db.commit()
    return recommendations


def list_recommendations(db: Session, field_id: int) -> list[Recommendation]:
    stmt = (
        select(Recommendation)
        .where(Recommendation.field_id == field_id)
        .order_by(Recommendation.priority)
    )
    return list(db.scalars(stmt))


def list_all_recommendations(db: Session, limit: int = 20) -> list[Recommendation]:
    stmt = select(Recommendation).order_by(Recommendation.priority).limit(limit)
    return list(db.scalars(stmt))
