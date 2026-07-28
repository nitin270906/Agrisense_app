"""Portfolio aggregation for the landing dashboard.

Serves the latest persisted predictions immediately when they are fresh enough,
only running full inference when they are stale. On a nine-field farm, a cold
load runs all nine inferences concurrently; subsequent loads within the freshness
window return in database time (~30 ms) instead of waiting on nine weather calls.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import Field, Prediction
from app.repositories import core as repo
from app.schemas import DashboardSummary, FieldSummary
from app.services.prediction import predict_field
from app.services.recommendation import generate_recommendations
from app.weather.service import get_weather

logger = logging.getLogger(__name__)

SPARKLINE_POINTS = 20
_FRESH_MINUTES = 45   # predictions younger than this are served without re-inference


def _sparkline(db: Session, field_id: int) -> list[float]:
    """Down-sample 90 days of soil EC to a fixed-length series for the card."""
    readings = repo.list_readings(db, field_id, days=90)
    if not readings:
        return []
    values = [r.soil_ec for r in readings]
    if len(values) <= SPARKLINE_POINTS:
        return [round(v, 2) for v in values]
    step = len(values) / SPARKLINE_POINTS
    return [round(values[int(i * step)], 2) for i in range(SPARKLINE_POINTS)]


def _is_fresh(pred: Prediction) -> bool:
    ts = pred.ts if pred.ts.tzinfo else pred.ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts) < timedelta(minutes=_FRESH_MINUTES)


async def _summarise_field(
    db: Session, field: Field, cached: Prediction | None
) -> FieldSummary | None:
    try:
        if cached is not None and _is_fresh(cached):
            # Fast path: latest persisted prediction is recent — skip re-inference.
            # Delta is approximated as (salinity_ec - previous reading EC) when
            # available; the chart still shows the trend correctly.
            recent_readings = repo.list_readings(db, field.id, days=2)
            prev_ec = recent_readings[-2].soil_ec if len(recent_readings) >= 2 else cached.salinity_ec
            delta = cached.salinity_ec - prev_ec

            stored_recs = repo.list_recommendations(db, field.id)
            top_action = stored_recs[0].title if stored_recs else None

            return FieldSummary(
                field_id=field.id,
                field_name=field.name,
                farm_id=field.farm_id,
                farm_name=field.farm.name if field.farm else "",
                crop=field.crop,
                area_ha=field.area_ha,
                lat=field.lat,
                lon=field.lon,
                salinity_ec=cached.salinity_ec,
                salinity_delta=round(delta, 3),
                water_stress_index=cached.water_stress_index,
                irrigation_need_mm=cached.irrigation_need_mm,
                health_score=cached.health_score,
                risk_level=cached.risk_level,
                top_action=top_action,
                sparkline=_sparkline(db, field.id),
            )

        # Slow path: run full inference and persist.
        prediction = await predict_field(db, field, persist=True)
        weather = await get_weather(db, field.lat, field.lon)
        recs = generate_recommendations(field, prediction, weather)
        repo.replace_recommendations(db, field.id, recs)

        return FieldSummary(
            field_id=field.id,
            field_name=field.name,
            farm_id=field.farm_id,
            farm_name=field.farm.name if field.farm else "",
            crop=field.crop,
            area_ha=field.area_ha,
            lat=field.lat,
            lon=field.lon,
            salinity_ec=prediction.salinity_ec,
            salinity_delta=prediction.salinity_delta,
            water_stress_index=prediction.water_stress_index,
            irrigation_need_mm=prediction.irrigation_need_mm,
            health_score=prediction.health_score,
            risk_level=prediction.risk_level,
            top_action=recs[0].title if recs else None,
            sparkline=_sparkline(db, field.id),
        )
    except Exception:
        # One bad field must not blank the whole dashboard.
        logger.exception("Failed to summarise field %s", field.id)
        return None


async def build_summary(db: Session, farm_id: int | None = None) -> DashboardSummary:
    fields = repo.list_fields(db, farm_id)
    if not fields:
        return DashboardSummary(
            total_fields=0, total_area_ha=0.0, fields_at_risk=0, critical_alerts=0,
            avg_salinity_ec=0.0, avg_health_score=0.0, total_irrigation_need_mm=0.0,
            risk_breakdown={}, fields=[],
        )

    # Fetch all latest predictions in one pass, then decide per-field whether
    # they are fresh enough to use directly (fast path) or need re-inference.
    cached_preds = repo.latest_predictions_for_fields(db, [f.id for f in fields])
    results = await asyncio.gather(
        *(_summarise_field(db, f, cached_preds.get(f.id)) for f in fields)
    )
    summaries = [s for s in results if s is not None]

    if not summaries:
        return DashboardSummary(
            total_fields=len(fields), total_area_ha=sum(f.area_ha for f in fields),
            fields_at_risk=0, critical_alerts=0, avg_salinity_ec=0.0,
            avg_health_score=0.0, total_irrigation_need_mm=0.0,
            risk_breakdown={}, fields=[],
        )

    breakdown: dict[str, int] = {}
    for s in summaries:
        key = s.risk_level.value if hasattr(s.risk_level, "value") else str(s.risk_level)
        breakdown[key] = breakdown.get(key, 0) + 1

    at_risk = breakdown.get("high", 0) + breakdown.get("critical", 0)

    return DashboardSummary(
        total_fields=len(summaries),
        total_area_ha=round(sum(s.area_ha for s in summaries), 1),
        fields_at_risk=at_risk,
        critical_alerts=breakdown.get("critical", 0),
        avg_salinity_ec=round(sum(s.salinity_ec for s in summaries) / len(summaries), 2),
        avg_health_score=round(sum(s.health_score for s in summaries) / len(summaries), 1),
        total_irrigation_need_mm=round(sum(s.irrigation_need_mm for s in summaries), 0),
        risk_breakdown=breakdown,
        # Worst first: the dashboard should open on the field that needs attention.
        fields=sorted(summaries, key=lambda s: (-s.salinity_ec, -s.water_stress_index)),
    )
