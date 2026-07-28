"""SQLAlchemy entities for the salinity forecaster.

Kept in one module because the seven tables form a single tightly-coupled
aggregate; splitting them across files would cost more in import ceremony than
it buys in clarity at this size.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CropProfile(Base):
    """Agronomic reference constants — real published values, not invented.

    `salt_threshold_a` / `salt_slope_b` are the Maas-Hoffman salt tolerance
    parameters: relative yield = 100 - b * (ECe - a) for ECe > a.
    `kc_*` are FAO-56 crop coefficients by growth stage.

    These live in the database rather than in code so an agronomist can correct
    them without a redeploy, and so the values are auditable.
    """

    __tablename__ = "crop_profiles"

    crop: Mapped[str] = mapped_column(String(40), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(60))
    kc_init: Mapped[float] = mapped_column(Float)
    kc_mid: Mapped[float] = mapped_column(Float)
    kc_late: Mapped[float] = mapped_column(Float)
    root_depth_m: Mapped[float] = mapped_column(Float)
    depletion_fraction: Mapped[float] = mapped_column(Float)  # FAO-56 "p"
    salt_threshold_a: Mapped[float] = mapped_column(Float)    # dS/m
    salt_slope_b: Mapped[float] = mapped_column(Float)        # % yield loss per dS/m
    season_days: Mapped[int] = mapped_column(Integer)
    tolerance_label: Mapped[str] = mapped_column(String(30))


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    owner: Mapped[str] = mapped_column(String(120))
    region: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    fields: Mapped[list["Field"]] = relationship(
        back_populates="farm", cascade="all, delete-orphan", lazy="selectin"
    )


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    crop: Mapped[str] = mapped_column(String(40), index=True)
    area_ha: Mapped[float] = mapped_column(Float)
    soil_texture: Mapped[str] = mapped_column(String(20))
    drainage_class: Mapped[str] = mapped_column(String(20))
    planting_date: Mapped[datetime] = mapped_column(Date)
    irrigation_water_ec: Mapped[float] = mapped_column(Float)   # dS/m of applied water
    water_table_depth_m: Mapped[float] = mapped_column(Float)   # drives capillary rise
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    farm: Mapped[Farm] = relationship(back_populates="fields")
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="field", cascade="all, delete-orphan"
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (Index("ix_readings_field_ts", "field_id", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    soil_ec: Mapped[float] = mapped_column(Float)            # dS/m
    soil_moisture_pct: Mapped[float] = mapped_column(Float)  # volumetric %
    soil_temp_c: Mapped[float] = mapped_column(Float)
    ph: Mapped[float] = mapped_column(Float)
    # Water applied that day (mm). Irrigation is the main salt import pathway,
    # so the 30-day applied depth is one of the strongest salinity predictors.
    irrigation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(20), default="sensor")

    field: Mapped[Field] = relationship(back_populates="readings")


class WeatherSnapshot(Base):
    """Cached weather rows, keyed by rounded lat/lon so nearby fields share cache."""

    __tablename__ = "weather_snapshots"
    __table_args__ = (Index("ix_weather_loc_ts_kind", "lat", "lon", "ts", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    ts: Mapped[datetime] = mapped_column(DateTime)
    kind: Mapped[str] = mapped_column(String(12))  # current | forecast | history

    temp_c: Mapped[float] = mapped_column(Float, default=0.0)
    temp_max_c: Mapped[float] = mapped_column(Float, default=0.0)
    temp_min_c: Mapped[float] = mapped_column(Float, default=0.0)
    precip_mm: Mapped[float] = mapped_column(Float, default=0.0)
    et0_mm: Mapped[float] = mapped_column(Float, default=0.0)
    humidity_pct: Mapped[float] = mapped_column(Float, default=0.0)
    wind_ms: Mapped[float] = mapped_column(Float, default=0.0)
    soil_moisture_m3: Mapped[float] = mapped_column(Float, default=0.0)
    soil_temp_c: Mapped[float] = mapped_column(Float, default=0.0)

    provider: Mapped[str] = mapped_column(String(30))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_field_ts", "field_id", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    horizon_days: Mapped[int] = mapped_column(Integer, default=7)

    salinity_ec: Mapped[float] = mapped_column(Float)
    water_stress_index: Mapped[float] = mapped_column(Float)
    irrigation_need_mm: Mapped[float] = mapped_column(Float)
    health_score: Mapped[float] = mapped_column(Float)

    risk_level: Mapped[str] = mapped_column(String(12))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    model_version: Mapped[str] = mapped_column(String(30), default="0.0.0")
    drivers: Mapped[str] = mapped_column(Text, default="[]")  # JSON: top feature drivers

    recommendations: Mapped[list["Recommendation"]] = relationship(
        back_populates="prediction", cascade="all, delete-orphan"
    )


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (Index("ix_recs_field_ts", "field_id", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"))
    prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=True
    )
    ts: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    category: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(12))
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    action_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)

    prediction: Mapped[Prediction | None] = relationship(back_populates="recommendations")
