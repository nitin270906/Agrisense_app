"""What-if simulation: run the field forward under two irrigation strategies.

This is where the tool stops being a dashboard and becomes a decision aid. A
farmer's real question is not "what is my salinity" but "what happens if I use
the canal water instead of the tubewell", and that is a counterfactual no
forecast can answer on its own.

Both paths run through the same `FieldState`, so baseline and scenario differ
only in the levers the user moved.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ml.crop_profiles import get_crop
from app.ml.physics import FieldState
from app.models import Field
from app.repositories import core as repo
from app.schemas import SimulationPoint, SimulationRequest, SimulationResult
from app.weather.base import WeatherSeries
from app.weather.service import get_weather


def _make_state(field: Field, start_ec: float, water_ec: float,
                drainage: str) -> FieldState:
    spec = get_crop(field.crop)
    state = FieldState(
        crop=field.crop,
        soil_texture=field.soil_texture,
        drainage_class=drainage,
        root_depth_m=spec.root_depth_m,
        irrigation_water_ec=water_ec,
        water_table_depth_m=field.water_table_depth_m,
    )
    state.set_initial_ece(start_ec)
    return state


def _run(
    field: Field, state: FieldState, weather: WeatherSeries, horizon: int,
    *, rain_multiplier: float = 1.0,
    fixed_irrigation_mm: float | None = None, interval_days: int = 7,
) -> list[SimulationPoint]:
    """Advance a field state day by day and record the trajectory."""
    today = datetime.now(timezone.utc).date()
    dap = max(0, (today - field.planting_date).days)
    forecast = weather.forecast or weather.days[-14:]
    points: list[SimulationPoint] = []

    for i in range(horizon):
        wx = forecast[i % len(forecast)] if forecast else None
        precip = (wx.precip_mm if wx else 0.0) * rain_multiplier
        et0 = wx.et0_mm if wx else 4.0
        t_max = wx.t_max_c if wx else 32.0

        if fixed_irrigation_mm is None:
            irrigation = state.irrigation_need()          # baseline: irrigate on demand
        else:
            irrigation = fixed_irrigation_mm if i % interval_days == 0 else 0.0

        res = state.step(
            precip_mm=precip, et0_mm=et0, t_max_c=t_max,
            days_after_planting=dap + i, irrigation_mm=irrigation,
        )
        points.append(SimulationPoint(
            day=i + 1,
            date=today + timedelta(days=i + 1),
            salinity_ec=round(res.ece, 2),
            water_stress_index=round(res.water_stress_index, 3),
            health_score=round(res.health_score, 1),
            soil_moisture_pct=round(res.soil_moisture_pct, 1),
        ))
    return points


def _summarise(
    field: Field, req: SimulationRequest,
    baseline: list[SimulationPoint], scenario: list[SimulationPoint],
) -> str:
    spec = get_crop(field.crop)
    b, s = baseline[-1], scenario[-1]
    d_ec = s.salinity_ec - b.salinity_ec
    d_health = s.health_score - b.health_score

    if abs(d_ec) < 0.05 and abs(d_health) < 1.0:
        return (
            f"Over {req.horizon_days} days this plan lands within a rounding error of "
            f"the current approach — salinity {s.salinity_ec:.1f} dS/m either way."
        )

    salt_dir = "higher" if d_ec > 0 else "lower"
    health_dir = "better" if d_health > 0 else "worse"
    verdict = (
        f"After {req.horizon_days} days salinity ends at {s.salinity_ec:.1f} dS/m, "
        f"{abs(d_ec):.2f} dS/m {salt_dir} than carrying on as now, and crop health is "
        f"{abs(d_health):.0f} points {health_dir} ({s.health_score:.0f} vs "
        f"{b.health_score:.0f})."
    )
    if s.salinity_ec > spec.salt_threshold_a:
        verdict += (
            f" That still leaves the field above {spec.display_name.lower()}'s "
            f"{spec.salt_threshold_a:.1f} dS/m tolerance."
        )
    elif b.salinity_ec > spec.salt_threshold_a >= s.salinity_ec:
        verdict += (
            f" Crucially, it pulls the field back under the "
            f"{spec.salt_threshold_a:.1f} dS/m tolerance limit."
        )
    return verdict


async def simulate(db: Session, field: Field, req: SimulationRequest) -> SimulationResult:
    """Compare the user's scenario against carrying on unchanged."""
    readings = repo.list_readings(db, field.id, days=14)
    current_ec = readings[-1].soil_ec if readings else 2.0
    weather = await get_weather(db, field.lat, field.lon)

    baseline = _run(
        field,
        _make_state(field, current_ec, field.irrigation_water_ec, field.drainage_class),
        weather, req.horizon_days,
    )

    scenario = _run(
        field,
        _make_state(
            field, current_ec,
            req.irrigation_water_ec if req.irrigation_water_ec is not None
            else field.irrigation_water_ec,
            req.drainage_class.value if req.drainage_class else field.drainage_class,
        ),
        weather, req.horizon_days,
        rain_multiplier=req.rainfall_scenario,
        fixed_irrigation_mm=req.irrigation_mm,
        interval_days=req.irrigation_interval_days,
    )

    events = sum(1 for i in range(req.horizon_days) if i % req.irrigation_interval_days == 0)
    return SimulationResult(
        baseline=baseline,
        scenario=scenario,
        salinity_change=round(scenario[-1].salinity_ec - baseline[-1].salinity_ec, 2),
        health_change=round(scenario[-1].health_score - baseline[-1].health_score, 1),
        water_applied_mm=round(req.irrigation_mm * events, 1),
        summary=_summarise(field, req, baseline, scenario),
    )
