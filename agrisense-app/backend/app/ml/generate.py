"""Synthetic training-data generator driven by the physics simulator.

Every row is produced by running `physics.FieldState` forward one day under
synthetic but climatologically realistic weather. The models therefore learn the
FAO-56 / Maas-Hoffman relationships rather than memorising a lookup table.

Two design choices carry most of the realism:

1. **Irrigation regimes are sampled, not idealised.** A perfectly irrigated field
   never experiences water stress by construction (Ks = 1 whenever depletion is
   below RAW), so idealised scheduling would collapse the water-stress target to
   a constant. Real farmers in NW India irrigate on *warabandi* — a fixed
   rotational canal turn every 7-21 days regardless of crop need — or apply
   deficit amounts when water is short. Those regimes are what create the stress
   distribution the model must learn.

2. **Initial salinity is sampled from a skewed distribution.** Salinisation is a
   multi-decade legacy process, not something that develops within one season.
   Seeding fields across the full USDA range reflects real landscapes, where
   degraded and healthy plots sit side by side.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.crop_profiles import CROP_SPECS, SOIL_SPECS, get_crop
from app.ml.features import SALINITY_HORIZON_DAYS, TARGET_COLUMNS, build_features
from app.ml.physics import FieldState, hargreaves_et0

DATA_DIR = Path(__file__).resolve().parent / "data"

# Weighted toward constrained supply, which is the Indian reality: roughly half
# of the net sown area is rainfed, and canal tail-enders routinely miss turns.
# An idealised mix would leave the water-stress target almost entirely zero.
IRRIGATION_REGIMES = ("reliable", "warabandi", "deficit", "delayed", "rainfed")
REGIME_WEIGHTS = (0.10, 0.30, 0.20, 0.15, 0.25)


def synthetic_weather(doy: int, lat: float, rng: np.random.Generator) -> dict[str, float]:
    """One day of climatologically plausible NW-India weather.

    Sinusoidal temperature peaking in May, with a sharp SW monsoon rainfall
    season from mid-June to September. Humidity tracks the monsoon.
    """
    # Temperature: peak near doy 130 (May), trough near doy 15 (January).
    t_mean = 24.0 + 10.0 * math.sin(2 * math.pi * (doy - 100) / 365.0)
    t_mean += rng.normal(0, 2.0) - (lat - 26.0) * 0.35  # cooler further north
    swing = 12.0 + rng.normal(0, 1.5)
    t_max = t_mean + swing / 2
    t_min = t_mean - swing / 2

    # Monsoon window (approx. 15 June - 30 September).
    in_monsoon = 166 <= doy <= 273
    if in_monsoon:
        rain_prob, scale = 0.42, 14.0
        humidity = rng.uniform(65, 92)
    else:
        rain_prob, scale = 0.05, 4.0
        humidity = rng.uniform(28, 60)

    precip = float(rng.exponential(scale)) if rng.random() < rain_prob else 0.0
    wind = float(abs(rng.normal(2.2, 1.0)))

    et0 = hargreaves_et0(t_mean, t_max, t_min, lat, doy)
    # Humid, still days evaporate less than the temperature-only estimate implies.
    et0 *= 1.0 - 0.35 * (humidity / 100.0)

    return {
        "t_mean": t_mean, "t_max": t_max, "t_min": t_min,
        "precip_mm": precip, "et0_mm": max(0.2, et0),
        "humidity_pct": humidity, "wind_ms": wind,
    }


def _irrigation_for_regime(
    regime: str, need_mm: float, day: int, turn_days: int, deficit_frac: float,
    turn_depth_mm: float, reliability: float,
    state: FieldState, rng: np.random.Generator,
) -> float:
    """Water actually applied today, given the farmer's water access pattern.

    The regimes model *supply*, not demand. This is the distinction that makes
    the water-stress target meaningful: a crop stresses when the water it needs
    and the water it can get diverge.
    """
    if regime == "rainfed":
        return 0.0
    if regime == "reliable":
        return need_mm
    if regime == "warabandi":
        # A warabandi turn delivers a fixed depth on a fixed roster, decoupled
        # from what the crop actually needs that day. Tail-end farmers also miss
        # turns outright when upstream users over-draw.
        if day % turn_days != 0:
            return 0.0
        if rng.random() > reliability:
            return 0.0  # turn missed
        return turn_depth_mm
    if regime == "deficit":
        return need_mm * deficit_frac
    if regime == "delayed":
        raw = state.taw * state.spec.depletion_fraction
        return need_mm if state.depletion_mm > raw * 1.35 else 0.0
    return need_mm


def simulate_field(field_id: int, rng: np.random.Generator) -> pd.DataFrame:
    """Run one virtual field through a full growing season, one day at a time."""
    crop = str(rng.choice(list(CROP_SPECS.keys())))
    spec = get_crop(crop)
    soil_texture = str(rng.choice(list(SOIL_SPECS.keys())))
    drainage = str(rng.choice(["poor", "moderate", "good"], p=[0.3, 0.45, 0.25]))

    lat = float(rng.uniform(21.0, 31.5))          # Gujarat -> Punjab
    water_table = float(np.clip(rng.lognormal(1.1, 0.6), 0.8, 14.0))
    irrigation_ec = float(np.clip(rng.lognormal(-0.2, 0.7), 0.2, 6.0))

    # Legacy salinity: most land is fine, a long tail is badly degraded.
    initial_ece = float(np.clip(rng.lognormal(0.55, 0.85), 0.2, 18.0))

    regime = str(rng.choice(IRRIGATION_REGIMES, p=REGIME_WEIGHTS))
    turn_days = int(rng.integers(7, 22))
    deficit_frac = float(rng.uniform(0.3, 0.75))
    turn_depth_mm = float(rng.uniform(40.0, 90.0))   # depth delivered per canal turn
    reliability = float(rng.uniform(0.55, 1.0))      # chance a scheduled turn arrives

    state = FieldState(
        crop=crop,
        soil_texture=soil_texture,
        drainage_class=drainage,
        root_depth_m=spec.root_depth_m,
        irrigation_water_ec=irrigation_ec,
        water_table_depth_m=water_table,
        groundwater_ec=float(np.clip(rng.normal(4.0, 1.8), 0.5, 12.0)),
    )
    state.set_initial_ece(initial_ece)
    state.depletion_mm = float(rng.uniform(0, state.taw * 0.4))

    start_doy = int(rng.integers(1, 366))
    n_days = min(spec.season_days, 240)
    rows = []

    for day in range(n_days):
        doy = (start_doy + day - 1) % 365 + 1
        wx = synthetic_weather(doy, lat, rng)

        need = state.irrigation_need()
        applied = _irrigation_for_regime(
            regime, need, day, turn_days, deficit_frac,
            turn_depth_mm, reliability, state, rng,
        )

        res = state.step(
            precip_mm=wx["precip_mm"],
            et0_mm=wx["et0_mm"],
            t_max_c=wx["t_max"],
            days_after_planting=day,
            irrigation_mm=applied,
        )

        # Sensors are imperfect: add measurement noise to what the model sees,
        # while targets stay on the clean physical value. This is what stops the
        # model from trivially inverting its own inputs.
        rows.append({
            "field_id": field_id,
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=day),
            "crop": crop,
            "soil_texture": soil_texture,
            "drainage_class": drainage,
            "root_depth_m": spec.root_depth_m,
            "irrigation_water_ec": irrigation_ec,
            "water_table_depth_m": water_table,
            "lat": lat,
            "days_after_planting": day,
            **wx,
            "soil_ec": max(0.05, res.ece + rng.normal(0, 0.12)),
            "soil_moisture_pct": max(1.0, res.soil_moisture_pct + rng.normal(0, 0.8)),
            "soil_temp_c": wx["t_mean"] + rng.normal(0, 1.2),
            "ph": float(np.clip(rng.normal(7.6 + 0.06 * res.ece, 0.35), 5.5, 9.8)),
            "days_since_irrigation": state.days_since_irrigation,
            "irrigation_mm": applied,
            # --- targets (clean physics, no noise) ---
            "_ece_true": res.ece,
            "target_water_stress": res.water_stress_index,
            "target_irrigation_mm": res.irrigation_need_mm,
            "target_health": res.health_score,
        })

    df = pd.DataFrame(rows)
    # Forecast the 30-day *change* in ECe rather than its level. Predicting the
    # level is trivially won by persistence; predicting the change is the part
    # that carries information. See features.SALINITY_HORIZON_DAYS.
    df["target_salinity_delta_30d"] = (
        df["_ece_true"].shift(-SALINITY_HORIZON_DAYS) - df["_ece_true"]
    )

    # Forward-looking weather: what is the rain and evaporative demand in the
    # 7/14 days ahead? These are available here because the simulation has the
    # full time series. At serving time they come from Open-Meteo's forecast.
    df["precip_next_7d"] = df["precip_mm"].shift(-7).fillna(0.0)
    df["et0_next_7d"] = df["et0_mm"].shift(-7).fillna(0.0)
    df["et0_next_14d"] = df["et0_mm"].shift(-14).fillna(0.0)

    return (
        df.dropna(subset=["target_salinity_delta_30d"]).drop(columns=["_ece_true"])
    )


def generate(n_fields: int = 400, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = [simulate_field(i, rng) for i in range(n_fields)]
    raw = pd.concat(frames, ignore_index=True)

    raw = raw.sort_values(["field_id", "date"]).reset_index(drop=True)
    features = build_features(raw).reset_index(drop=True)

    # field_id rides along (not a feature) so training can hold out whole fields.
    # Adjacent days within a field are near-duplicates; a random row split would
    # leak the answer across the boundary and inflate every metric.
    dataset = pd.concat(
        [raw[["field_id"]], features, raw[TARGET_COLUMNS]], axis=1
    )
    return dataset.dropna()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic training data.")
    parser.add_argument("--fields", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=str(DATA_DIR / "training.parquet"))
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = generate(args.fields, args.seed)

    out = Path(args.out)
    try:
        df.to_parquet(out, index=False)
    except Exception:  # pyarrow not installed — CSV is a fine fallback
        out = out.with_suffix(".csv")
        df.to_csv(out, index=False)

    print(f"Generated {len(df):,} rows x {df.shape[1]} cols -> {out}")
    print("\nTarget distributions:")
    print(df[TARGET_COLUMNS].describe().T[["mean", "std", "min", "50%", "max"]].round(2))


if __name__ == "__main__":
    main()
