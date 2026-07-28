"""Prediction service: assemble model inputs, run inference, persist results.

The interesting work here is the join. The model needs one row per field-day
carrying both sensor state and weather, but the two arrive from different places
at different cadences: readings come from the database, weather from a cached
provider call. This module reconciles them onto a single daily index and hands
the result to the shared feature builder.

If artifacts are missing, inference degrades to the physics simulator rather
than failing. A demo that shows physics-derived numbers is infinitely better
than one showing a stack trace.
"""
from __future__ import annotations

import json
import logging
from datetime import date as Date
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.ml.crop_profiles import get_crop
from app.ml.features import RAW_COLUMNS, SALINITY_HORIZON_DAYS
from app.ml.physics import FieldState, crop_health_score, salinity_risk_level
from app.ml.predictor import PredictionResult, predictor
from app.models import Field
from app.repositories import core as repo
from app.weather.base import WeatherSeries
from app.weather.service import get_weather

logger = logging.getLogger(__name__)

MIN_HISTORY_DAYS = 3


def build_history_frame(
    field: Field, readings: list, weather: WeatherSeries
) -> pd.DataFrame:
    """Join sensor readings with weather into the model's raw input frame.

    Weather is indexed by date and looked up per reading. Where a reading has no
    matching weather day (a gap in the cache, or history older than the
    provider's 92-day window) the nearest available day is substituted, which
    keeps the rolling windows continuous instead of punching holes in them.
    """
    if not readings:
        return pd.DataFrame(columns=RAW_COLUMNS)

    wx_by_date: dict[Date, object] = {d.date: d for d in weather.days}
    wx_dates = sorted(wx_by_date)

    def nearest_weather(target: Date):
        if not wx_dates:
            return None
        if target in wx_by_date:
            return wx_by_date[target]
        return wx_by_date[min(wx_dates, key=lambda d: abs((d - target).days))]

    spec = get_crop(field.crop)
    rows = []
    last_irrigation_day: Date | None = None

    for reading in readings:
        day = reading.ts.date()
        wx = nearest_weather(day)
        if wx is None:
            continue

        if reading.irrigation_mm > 0:
            last_irrigation_day = day
        days_since = (day - last_irrigation_day).days if last_irrigation_day else 30

        rows.append({
            "field_id": field.id,
            "date": pd.Timestamp(day),
            "crop": field.crop,
            "soil_texture": field.soil_texture,
            "drainage_class": field.drainage_class,
            "root_depth_m": spec.root_depth_m,
            "irrigation_water_ec": field.irrigation_water_ec,
            "water_table_depth_m": field.water_table_depth_m,
            "lat": field.lat,
            "days_after_planting": max(0, (day - field.planting_date).days),
            "t_mean": wx.t_mean_c,
            "t_max": wx.t_max_c,
            "t_min": wx.t_min_c,
            "precip_mm": wx.precip_mm,
            "et0_mm": wx.et0_mm,
            "humidity_pct": wx.humidity_pct,
            "wind_ms": wx.wind_ms,
            "soil_ec": reading.soil_ec,
            "soil_moisture_pct": reading.soil_moisture_pct,
            "soil_temp_c": reading.soil_temp_c,
            "ph": reading.ph,
            "days_since_irrigation": days_since,
            "irrigation_mm": reading.irrigation_mm,
        })

    frame = pd.DataFrame(rows, columns=RAW_COLUMNS)
    if frame.empty:
        return frame

    # Inject forward-looking weather from the forecast window. Only the final
    # row needs these — the rolling windows in build_features use only the last
    # row anyway — so historical rows stay zero rather than leaking future info.
    fcast = weather.forecast or []
    frame["precip_next_7d"] = 0.0
    frame["et0_next_7d"] = 0.0
    frame["et0_next_14d"] = 0.0
    last = frame.index[-1]
    frame.at[last, "precip_next_7d"] = sum(d.precip_mm for d in fcast[:7])
    frame.at[last, "et0_next_7d"] = sum(d.et0_mm for d in fcast[:7])
    frame.at[last, "et0_next_14d"] = sum(d.et0_mm for d in fcast[:14])
    return frame


def _physics_fallback(field: Field, readings: list, weather: WeatherSeries) -> PredictionResult:
    """Derive the four outputs from the simulator when models are unavailable."""
    spec = get_crop(field.crop)
    latest = readings[-1] if readings else None
    current_ec = latest.soil_ec if latest else 2.0

    state = FieldState(
        crop=field.crop,
        soil_texture=field.soil_texture,
        drainage_class=field.drainage_class,
        root_depth_m=spec.root_depth_m,
        irrigation_water_ec=field.irrigation_water_ec,
        water_table_depth_m=field.water_table_depth_m,
    )
    state.set_initial_ece(current_ec)

    forecast_days = weather.forecast or weather.days[-7:]
    dap = max(0, (datetime.now(timezone.utc).date() - field.planting_date).days)
    result = None
    for i, wx in enumerate(forecast_days[:SALINITY_HORIZON_DAYS]):
        result = state.step(
            precip_mm=wx.precip_mm, et0_mm=wx.et0_mm, t_max_c=wx.t_max_c,
            days_after_planting=dap + i,
            irrigation_mm=state.irrigation_need(),
        )

    if result is None:
        health = crop_health_score(current_ec, 1.0, 30.0, spec)
        return PredictionResult(
            salinity_ec=round(current_ec, 2), salinity_delta=0.0,
            water_stress_index=0.0, irrigation_need_mm=0.0,
            health_score=round(health, 1), risk_level=salinity_risk_level(current_ec),
            confidence=0.25, horizon_days=SALINITY_HORIZON_DAYS,
            model_version="physics-fallback", drivers=[],
        )

    return PredictionResult(
        salinity_ec=round(result.ece, 2),
        salinity_delta=round(result.ece - current_ec, 3),
        water_stress_index=round(result.water_stress_index, 3),
        irrigation_need_mm=round(result.irrigation_need_mm, 1),
        health_score=round(result.health_score, 1),
        risk_level=result.risk_level,
        confidence=0.35,
        horizon_days=SALINITY_HORIZON_DAYS,
        model_version="physics-fallback",
        drivers=[],
    )


async def predict_field(db: Session, field: Field, *, persist: bool = True) -> PredictionResult:
    """Run a full prediction for one field."""
    readings = repo.list_readings(db, field.id, days=120)
    weather = await get_weather(db, field.lat, field.lon)

    if len(readings) < MIN_HISTORY_DAYS:
        logger.info("Field %s has %d readings; using physics fallback",
                    field.id, len(readings))
        result = _physics_fallback(field, readings, weather)
    else:
        history = build_history_frame(field, readings, weather)
        try:
            result = predictor.predict(history)
        except Exception:
            logger.exception("Model inference failed for field %s; falling back", field.id)
            result = _physics_fallback(field, readings, weather)

    if persist:
        repo.save_prediction(
            db,
            field_id=field.id,
            ts=datetime.now(timezone.utc),
            horizon_days=result.horizon_days,
            salinity_ec=result.salinity_ec,
            water_stress_index=result.water_stress_index,
            irrigation_need_mm=result.irrigation_need_mm,
            health_score=result.health_score,
            risk_level=result.risk_level,
            confidence=result.confidence,
            model_version=result.model_version,
            drivers=json.dumps(result.drivers),
        )
    return result


async def forecast_trajectory(
    db: Session, field: Field, days: int = 30
) -> list[dict]:
    """Day-by-day projected salinity/stress/health for the trend chart.

    Uses the simulator rather than the ML models: the models predict a single
    horizon, whereas a chart needs a continuous path. Both share the same
    physics, so the trajectory ends where the model's point forecast lands.
    """
    spec = get_crop(field.crop)
    readings = repo.list_readings(db, field.id, days=30)
    weather = await get_weather(db, field.lat, field.lon)
    current_ec = readings[-1].soil_ec if readings else 2.0

    state = FieldState(
        crop=field.crop,
        soil_texture=field.soil_texture,
        drainage_class=field.drainage_class,
        root_depth_m=spec.root_depth_m,
        irrigation_water_ec=field.irrigation_water_ec,
        water_table_depth_m=field.water_table_depth_m,
    )
    state.set_initial_ece(current_ec)

    forecast_days = weather.forecast
    today = datetime.now(timezone.utc).date()
    dap = max(0, (today - field.planting_date).days)
    points = []

    for i in range(days):
        # Beyond the provider's forecast window, cycle the available days as a
        # climatological proxy rather than inventing weather.
        wx = forecast_days[i % len(forecast_days)] if forecast_days else None
        precip = wx.precip_mm if wx else 0.0
        et0 = wx.et0_mm if wx else 4.0
        t_max = wx.t_max_c if wx else 32.0

        res = state.step(
            precip_mm=precip, et0_mm=et0, t_max_c=t_max,
            days_after_planting=dap + i,
            irrigation_mm=state.irrigation_need(),
        )
        points.append({
            "date": today + timedelta(days=i + 1),
            "salinity_ec": round(res.ece, 2),
            "water_stress_index": round(res.water_stress_index, 3),
            "health_score": round(res.health_score, 1),
            "is_forecast": True,
        })

    return points
