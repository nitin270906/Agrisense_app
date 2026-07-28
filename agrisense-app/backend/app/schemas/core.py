"""Pydantic request/response models — the API's public contract."""
from __future__ import annotations

from datetime import date as Date
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    DrainageClass,
    RecommendationCategory,
    RiskLevel,
    Severity,
    SoilTexture,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- reference -------------------------------------------------------------- #
class CropProfileOut(ORMModel):
    crop: str
    display_name: str
    salt_threshold_a: float
    salt_slope_b: float
    root_depth_m: float
    season_days: int
    tolerance_label: str


# --- farms ------------------------------------------------------------------ #
class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    owner: str = Field(min_length=1, max_length=120)
    region: str
    state: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class FarmOut(ORMModel):
    id: int
    name: str
    owner: str
    region: str
    state: str
    lat: float
    lon: float
    field_count: int = 0


# --- fields ----------------------------------------------------------------- #
class FieldCreate(BaseModel):
    farm_id: int
    name: str = Field(min_length=1, max_length=120)
    crop: str
    area_ha: float = Field(gt=0, le=10_000)
    soil_texture: SoilTexture
    drainage_class: DrainageClass
    planting_date: Date
    irrigation_water_ec: float = Field(ge=0, le=20, description="dS/m")
    water_table_depth_m: float = Field(gt=0, le=100)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class FieldOut(ORMModel):
    id: int
    farm_id: int
    name: str
    crop: str
    area_ha: float
    soil_texture: str
    drainage_class: str
    planting_date: Date
    irrigation_water_ec: float
    water_table_depth_m: float
    lat: float
    lon: float


# --- sensor readings -------------------------------------------------------- #
class ReadingCreate(BaseModel):
    ts: datetime | None = None
    soil_ec: float = Field(ge=0, le=50, description="dS/m")
    soil_moisture_pct: float = Field(ge=0, le=60)
    soil_temp_c: float = Field(ge=-10, le=70)
    ph: float = Field(ge=3, le=11)
    irrigation_mm: float = Field(default=0.0, ge=0, le=500)
    source: str = "sensor"


class ReadingOut(ORMModel):
    id: int
    field_id: int
    ts: datetime
    soil_ec: float
    soil_moisture_pct: float
    soil_temp_c: float
    ph: float
    irrigation_mm: float
    source: str


# --- weather ---------------------------------------------------------------- #
class WeatherDayOut(BaseModel):
    date: Date
    t_mean_c: float
    t_max_c: float
    t_min_c: float
    precip_mm: float
    et0_mm: float
    humidity_pct: float
    wind_ms: float
    is_forecast: bool


class WeatherOut(BaseModel):
    lat: float
    lon: float
    provider: str
    from_cache: bool = False
    stale: bool = False
    days: list[WeatherDayOut]


# --- predictions ------------------------------------------------------------ #
class DriverOut(BaseModel):
    feature: str
    label: str
    value: float
    importance: float


class PredictionOut(ORMModel):
    id: int | None = None
    field_id: int
    ts: datetime
    horizon_days: int
    salinity_ec: float
    salinity_delta: float = 0.0
    water_stress_index: float
    irrigation_need_mm: float
    health_score: float
    risk_level: RiskLevel
    confidence: float
    model_version: str
    drivers: list[DriverOut] = []
    salinity_ec_p10: float | None = None
    salinity_ec_p90: float | None = None


class ForecastPoint(BaseModel):
    date: Date
    salinity_ec: float
    water_stress_index: float
    health_score: float
    is_forecast: bool = True


# --- recommendations -------------------------------------------------------- #
class RecommendationOut(ORMModel):
    id: int | None = None
    field_id: int
    category: RecommendationCategory
    severity: Severity
    title: str
    message: str
    action_mm: float | None = None
    priority: int


# --- simulation -------------------------------------------------------------- #
class SimulationRequest(BaseModel):
    """What-if levers a farmer can actually pull."""

    irrigation_mm: float = Field(default=0.0, ge=0, le=300,
                                 description="Water applied per event (mm)")
    irrigation_water_ec: float | None = Field(default=None, ge=0, le=20,
                                              description="Override water salinity (dS/m)")
    irrigation_interval_days: int = Field(default=7, ge=1, le=60)
    rainfall_scenario: float = Field(default=1.0, ge=0.0, le=3.0,
                                     description="Multiplier on forecast rainfall")
    horizon_days: int = Field(default=30, ge=7, le=120)
    drainage_class: DrainageClass | None = None


class SimulationPoint(BaseModel):
    day: int
    date: Date
    salinity_ec: float
    water_stress_index: float
    health_score: float
    soil_moisture_pct: float


class SimulationResult(BaseModel):
    baseline: list[SimulationPoint]
    scenario: list[SimulationPoint]
    salinity_change: float
    health_change: float
    water_applied_mm: float
    summary: str


# --- dashboard --------------------------------------------------------------- #
class FieldSummary(BaseModel):
    field_id: int
    field_name: str
    farm_id: int
    farm_name: str
    crop: str
    area_ha: float
    lat: float = 0.0
    lon: float = 0.0
    salinity_ec: float
    salinity_delta: float
    water_stress_index: float
    irrigation_need_mm: float
    health_score: float
    risk_level: RiskLevel
    top_action: str | None = None
    sparkline: list[float] = []


class DashboardSummary(BaseModel):
    total_fields: int
    total_area_ha: float
    fields_at_risk: int
    critical_alerts: int
    avg_salinity_ec: float
    avg_health_score: float
    total_irrigation_need_mm: float
    risk_breakdown: dict[str, int]
    fields: list[FieldSummary]


# --- model info -------------------------------------------------------------- #
class ModelInfo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    trained_at: str | None = None
    loaded: bool
    n_rows: int | None = None
    n_fields: int | None = None
    split: str | None = None
    data_provenance: str | None = None
    feature_count: int = 0
    metrics: dict = {}


class HealthOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    model_loaded: bool
    model_version: str
    weather_provider: str
    database: str
