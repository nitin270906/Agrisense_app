"""Rules engine turning predictions into actions a farmer can take today.

Deliberately rules, not a model. Advice that changes what someone does with
their land and their water has to be explainable line by line — "irrigate 60 mm"
must trace back to a leaching requirement someone can check, not to a gradient.
The ML supplies the forecast; these rules decide what to do about it.

Every recommendation carries a number and a deadline. "Monitor salinity" is not
advice; "apply 68 mm of leaching irrigation within 10 days, or wheat yield falls
about 14%" is.
"""
from __future__ import annotations

from math import ceil

from app.ml.crop_profiles import CROP_SPECS, get_crop, get_soil
from app.ml.physics import leaching_requirement, maas_hoffman_relative_yield
from app.ml.predictor import PredictionResult
from app.models import Field, Recommendation
from app.models.enums import RecommendationCategory as Cat
from app.models.enums import Severity
from app.weather.base import WeatherSeries

# Fraction of the crop's salt threshold at which we start warning.
WARN_FRACTION = 0.75

# Depth of water needed to leach, as a fraction of root depth, to remove ~80% of
# salts. Coarse soils flush efficiently; clays need far more water (FAO-29).
LEACHING_K = {
    "sandy": 0.30, "sandy_loam": 0.33, "loam": 0.38,
    "clay_loam": 0.42, "clay": 0.48,
}

# Rain within this window can substitute for an irrigation event.
RAIN_LOOKAHEAD_DAYS = 5


# Practical ceiling on a single irrigation event, limited by infiltration. Beyond
# this the water ponds or runs off instead of percolating, so it leaches nothing.
MAX_EVENT_MM = {
    "sandy": 100.0, "sandy_loam": 90.0, "loam": 75.0,
    "clay_loam": 65.0, "clay": 50.0,
}


def _leaching_plan(field: Field, current_ec: float, target_ec: float) -> tuple[float, float, int]:
    """Total leaching water needed, split into practical irrigation events.

    Returns ``(total_mm, per_event_mm, event_count)``.

    Reclaiming a saline field genuinely takes a lot of water — FAO-29's leaching
    curves put it at roughly a third of the root-zone depth to remove 80% of
    salts. But that total cannot be applied at once: a single 250 mm irrigation
    on clay loam ponds and runs off, leaching nothing. Real practice splits it
    across several events over weeks, so the advice is expressed that way.
    """
    if current_ec <= target_ec:
        return 0.0, 0.0, 0
    spec = get_crop(field.crop)
    k = LEACHING_K.get(field.soil_texture, 0.40)
    reduction = (current_ec - target_ec) / current_ec
    total = k * spec.root_depth_m * 1000.0 * reduction

    per_event = MAX_EVENT_MM.get(field.soil_texture, 75.0)
    events = max(1, ceil(total / per_event))
    # Even out the split so the last event isn't a token amount.
    per_event = round(total / events, 0)
    return round(total, 0), per_event, events


def _forecast_rain(weather: WeatherSeries, days: int = RAIN_LOOKAHEAD_DAYS) -> float:
    return round(sum(d.precip_mm for d in weather.forecast[:days]), 1)


def _more_tolerant_crops(current_ec: float, current_crop: str) -> list[str]:
    """Crops whose salt threshold clears the field's projected salinity."""
    return [
        spec.display_name
        for spec in CROP_SPECS.values()
        if spec.crop != current_crop and spec.salt_threshold_a >= current_ec
    ]


def generate_recommendations(
    field: Field, prediction: PredictionResult, weather: WeatherSeries
) -> list[Recommendation]:
    """Produce a severity-ranked action list for one field."""
    spec = get_crop(field.crop)
    soil = get_soil(field.soil_texture)
    ec = prediction.salinity_ec
    threshold = spec.salt_threshold_a
    recs: list[Recommendation] = []

    rain_soon = _forecast_rain(weather)
    yield_pct = maas_hoffman_relative_yield(ec, threshold, spec.salt_slope_b)
    yield_loss = round(100.0 - yield_pct, 1)

    # --- 1. Salinity above the crop's tolerance --------------------------- #
    if ec > threshold:
        target = threshold * 0.8
        total_mm, per_event_mm, events = _leaching_plan(field, ec, target)
        soil_label = field.soil_texture.replace("_", " ")
        plan = (
            f"Apply about {per_event_mm:.0f} mm of low-salinity water now"
            if events == 1
            else (
                f"Apply about {per_event_mm:.0f} mm of low-salinity water now, then repeat "
                f"{events - 1} more time{'s' if events > 2 else ''} at roughly weekly "
                f"intervals ({total_mm:.0f} mm in total)"
            )
        )
        recs.append(Recommendation(
            field_id=field.id,
            category=Cat.LEACHING.value,
            severity=Severity.CRITICAL.value if yield_loss > 20 else Severity.URGENT.value,
            title=f"Leach salt now — {yield_loss:.0f}% yield at risk",
            message=(
                f"Projected salinity is {ec:.1f} dS/m against a tolerance of "
                f"{threshold:.1f} dS/m for {spec.display_name.lower()}. At this level "
                f"expect roughly {yield_loss:.0f}% yield loss. {plan}. Splitting it matters "
                f"on {soil_label} soil — more than about "
                f"{MAX_EVENT_MM.get(field.soil_texture, 75.0):.0f} mm at once ponds and runs "
                f"off instead of carrying salt below the root zone."
            ),
            action_mm=per_event_mm,
            priority=1,
        ))
    elif ec > threshold * WARN_FRACTION:
        headroom = threshold - ec
        recs.append(Recommendation(
            field_id=field.id,
            category=Cat.LEACHING.value,
            severity=Severity.WARNING.value,
            title=f"Approaching salt tolerance — {headroom:.1f} dS/m of headroom",
            message=(
                f"Salinity is forecast at {ec:.1f} dS/m, closing on the "
                f"{threshold:.1f} dS/m threshold where {spec.display_name.lower()} starts "
                f"losing yield. Add roughly "
                f"{leaching_requirement(field.irrigation_water_ec, threshold) * 100:.0f}% "
                f"extra water to each irrigation to keep salts moving downward."
            ),
            action_mm=None,
            priority=3,
        ))

    # --- 2. Irrigation scheduling ----------------------------------------- #
    need = prediction.irrigation_need_mm
    if need > 5:
        if rain_soon >= need * 0.6:
            recs.append(Recommendation(
                field_id=field.id,
                category=Cat.IRRIGATION.value,
                severity=Severity.INFO.value,
                title=f"Hold irrigation — {rain_soon:.0f} mm rain expected",
                message=(
                    f"The field needs about {need:.0f} mm, but {rain_soon:.0f} mm of rain "
                    f"is forecast within {RAIN_LOOKAHEAD_DAYS} days. Waiting saves the "
                    f"water and the fuel, and rainfall is salt-free so it leaches the "
                    f"root zone rather than adding to the salt load."
                ),
                action_mm=0.0,
                priority=4,
            ))
        else:
            urgency = (
                Severity.URGENT.value if prediction.water_stress_index > 0.3
                else Severity.WARNING.value
            )
            recs.append(Recommendation(
                field_id=field.id,
                category=Cat.IRRIGATION.value,
                severity=urgency,
                title=f"Irrigate {need:.0f} mm within 3 days",
                message=(
                    f"Soil water is drawn down and only {rain_soon:.0f} mm of rain is "
                    f"forecast. Apply about {need:.0f} mm to refill the root zone. "
                    f"This figure already includes the extra depth needed to carry salt "
                    f"below the roots given your water at "
                    f"{field.irrigation_water_ec:.1f} dS/m."
                ),
                action_mm=need,
                priority=2,
            ))

    # --- 3. Water stress already present ---------------------------------- #
    if prediction.water_stress_index > 0.4:
        pct = prediction.water_stress_index * 100
        recs.append(Recommendation(
            field_id=field.id,
            category=Cat.IRRIGATION.value,
            severity=Severity.CRITICAL.value if pct > 65 else Severity.URGENT.value,
            title=f"Crop under water stress ({pct:.0f}%)",
            message=(
                f"The crop is transpiring below its potential, which cuts yield directly. "
                f"Salinity makes this worse: dissolved salt raises the osmotic pull of the "
                f"soil solution, so the same moisture is harder for roots to take up. "
                f"Irrigate as soon as water is available."
            ),
            action_mm=None,
            priority=1,
        ))

    # --- 4. Structural drivers -------------------------------------------- #
    if field.water_table_depth_m < 2.5 and field.drainage_class == "poor":
        recs.append(Recommendation(
            field_id=field.id,
            category=Cat.DRAINAGE.value,
            severity=Severity.WARNING.value,
            title="Install subsurface drainage",
            message=(
                f"The water table sits {field.water_table_depth_m:.1f} m down with poor "
                f"drainage, so saline groundwater is wicking upward into the root zone as "
                f"the surface dries. No irrigation schedule fixes this. Subsurface tile "
                f"drains or an open ditch to lower the table below 2.5 m is the durable "
                f"remedy."
            ),
            action_mm=None,
            priority=5,
        ))

    if ec > 4.0 and soil.leaching_efficiency < 0.65:
        recs.append(Recommendation(
            field_id=field.id,
            category=Cat.AMENDMENT.value,
            severity=Severity.WARNING.value,
            title="Apply gypsum to improve infiltration",
            message=(
                f"Heavy {field.soil_texture.replace('_', ' ')} soil leaches poorly, so "
                f"applied water struggles to carry salt downward. Gypsum "
                f"(calcium sulphate, roughly 2-5 t/ha) displaces sodium on the clay and "
                f"restores structure, which makes every later leaching irrigation work "
                f"harder. Add organic matter alongside it."
            ),
            action_mm=None,
            priority=6,
        ))

    # --- 5. The crop is simply wrong for this land ------------------------ #
    if ec > threshold * 1.5:
        alternatives = _more_tolerant_crops(ec, field.crop)
        if alternatives:
            recs.append(Recommendation(
                field_id=field.id,
                category=Cat.CROP_CHOICE.value,
                severity=Severity.WARNING.value,
                title="Consider a salt-tolerant crop next season",
                message=(
                    f"At {ec:.1f} dS/m this field is well past what "
                    f"{spec.display_name.lower()} tolerates ({threshold:.1f} dS/m), and "
                    f"reclamation takes seasons. {', '.join(alternatives[:3])} would hold "
                    f"yield on this land while the salt is worked down."
                ),
                action_mm=None,
                priority=7,
            ))

    # --- 6. Nothing wrong — say so plainly -------------------------------- #
    if not recs:
        recs.append(Recommendation(
            field_id=field.id,
            category=Cat.MONITORING.value,
            severity=Severity.INFO.value,
            title="Field is healthy — no action needed",
            message=(
                f"Salinity is forecast at {ec:.1f} dS/m, comfortably under the "
                f"{threshold:.1f} dS/m limit for {spec.display_name.lower()}, and soil "
                f"water is adequate. Keep the current irrigation pattern and re-check "
                f"after the next rainfall."
            ),
            action_mm=None,
            priority=9,
        ))

    return sorted(recs, key=lambda r: r.priority)
