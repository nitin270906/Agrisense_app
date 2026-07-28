"""Field-scoped intelligence: readings, weather, predictions, advice, what-ifs."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Field
from app.repositories import core as repo
from app.schemas import (
    ForecastPoint,
    PredictionOut,
    ReadingCreate,
    ReadingOut,
    RecommendationOut,
    SimulationRequest,
    SimulationResult,
    WeatherOut,
)
from app.services.prediction import forecast_trajectory, predict_field
from app.services.recommendation import generate_recommendations
from app.services.simulation import simulate
from app.weather.service import get_weather

router = APIRouter(prefix="/fields/{field_id}", tags=["insights"])


def _require_field(db: Session, field_id: int) -> Field:
    field = repo.get_field(db, field_id)
    if field is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Field {field_id} not found")
    return field


# --- sensor readings -------------------------------------------------------- #
@router.get("/readings", response_model=list[ReadingOut])
def list_readings(
    field_id: int, days: int = Query(default=90, ge=1, le=365),
    db: Session = Depends(get_db),
) -> list[ReadingOut]:
    _require_field(db, field_id)
    return [ReadingOut.model_validate(r) for r in repo.list_readings(db, field_id, days)]


@router.post("/readings", response_model=ReadingOut, status_code=status.HTTP_201_CREATED)
def add_reading(
    field_id: int, payload: ReadingCreate, db: Session = Depends(get_db)
) -> ReadingOut:
    _require_field(db, field_id)
    data = payload.model_dump()
    data["ts"] = data.get("ts") or datetime.now(timezone.utc)
    return ReadingOut.model_validate(repo.add_reading(db, field_id, **data))


# --- weather ---------------------------------------------------------------- #
@router.get("/weather", response_model=WeatherOut)
async def field_weather(
    field_id: int,
    refresh: bool = Query(default=False, description="Bypass the cache"),
    db: Session = Depends(get_db),
) -> WeatherOut:
    field = _require_field(db, field_id)
    series = await get_weather(db, field.lat, field.lon, force_refresh=refresh)
    return WeatherOut(
        lat=field.lat, lon=field.lon, provider=series.provider,
        from_cache=series.from_cache, stale=series.stale,
        days=[d.to_dict() for d in series.days],
    )


# --- predictions ------------------------------------------------------------ #
def _to_prediction_out(field_id: int, result, prediction_id: int | None = None) -> PredictionOut:
    return PredictionOut(
        id=prediction_id,
        field_id=field_id,
        ts=datetime.now(timezone.utc),
        horizon_days=result.horizon_days,
        salinity_ec=result.salinity_ec,
        salinity_delta=result.salinity_delta,
        water_stress_index=result.water_stress_index,
        irrigation_need_mm=result.irrigation_need_mm,
        health_score=result.health_score,
        risk_level=result.risk_level,
        confidence=result.confidence,
        model_version=result.model_version,
        drivers=result.drivers,
        salinity_ec_p10=result.salinity_ec_p10,
        salinity_ec_p90=result.salinity_ec_p90,
    )


@router.post("/predict", response_model=PredictionOut)
async def run_prediction(field_id: int, db: Session = Depends(get_db)) -> PredictionOut:
    field = _require_field(db, field_id)
    result = await predict_field(db, field, persist=True)
    return _to_prediction_out(field_id, result)


@router.get("/predictions/latest", response_model=PredictionOut)
async def latest_prediction(field_id: int, db: Session = Depends(get_db)) -> PredictionOut:
    """Most recent stored prediction, computing one on demand if none exists."""
    field = _require_field(db, field_id)
    stored = repo.latest_prediction(db, field_id)
    if stored is None:
        result = await predict_field(db, field, persist=True)
        return _to_prediction_out(field_id, result)

    return PredictionOut(
        id=stored.id,
        field_id=stored.field_id,
        ts=stored.ts,
        horizon_days=stored.horizon_days,
        salinity_ec=stored.salinity_ec,
        salinity_delta=0.0,
        water_stress_index=stored.water_stress_index,
        irrigation_need_mm=stored.irrigation_need_mm,
        health_score=stored.health_score,
        risk_level=stored.risk_level,
        confidence=stored.confidence,
        model_version=stored.model_version,
        drivers=json.loads(stored.drivers or "[]"),
    )


@router.get("/forecast", response_model=list[ForecastPoint])
async def field_forecast(
    field_id: int, days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
) -> list[ForecastPoint]:
    field = _require_field(db, field_id)
    points = await forecast_trajectory(db, field, days)
    return [ForecastPoint(**p) for p in points]


# --- recommendations -------------------------------------------------------- #
@router.get("/recommendations", response_model=list[RecommendationOut])
async def field_recommendations(
    field_id: int, db: Session = Depends(get_db)
) -> list[RecommendationOut]:
    field = _require_field(db, field_id)
    result = await predict_field(db, field, persist=False)
    weather = await get_weather(db, field.lat, field.lon)
    recs = generate_recommendations(field, result, weather)
    repo.replace_recommendations(db, field_id, recs)
    return [RecommendationOut.model_validate(r) for r in recs]


# --- simulation ------------------------------------------------------------- #
@router.post("/simulate", response_model=SimulationResult)
async def run_simulation(
    field_id: int, payload: SimulationRequest, db: Session = Depends(get_db)
) -> SimulationResult:
    field = _require_field(db, field_id)
    return await simulate(db, field, payload)
