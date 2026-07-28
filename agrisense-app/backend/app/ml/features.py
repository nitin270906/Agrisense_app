"""Canonical feature construction — imported by BOTH training and serving.

Train/serve skew is the classic way an ML demo silently breaks: the training
script computes a 7-day rainfall sum one way, the API computes it another, and
the model quietly receives inputs it never saw. The defence here is that there
is exactly one implementation, `build_features`, and both paths call it with a
time-ordered frame of the same raw columns.

Design note: categorical inputs (crop, soil texture, drainage) are encoded as
their *physical constants* rather than one-hot dummies. Encoding wheat as
"salt threshold 6.0 dS/m, root depth 1.5 m" instead of an opaque indicator means
the model learns the underlying agronomic relationship — and a crop the model
has never seen still yields sensible predictions, because it is described in the
same physical vocabulary.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.ml.crop_profiles import get_crop, get_drainage_factor, get_soil
from app.ml.physics import crop_coefficient

# Raw columns every caller must supply, time-ordered ascending per field.
RAW_COLUMNS = [
    "field_id", "date", "crop", "soil_texture", "drainage_class",
    "root_depth_m", "irrigation_water_ec", "water_table_depth_m", "lat",
    "days_after_planting",
    "t_mean", "t_max", "t_min", "precip_mm", "et0_mm", "humidity_pct", "wind_ms",
    "soil_ec", "soil_moisture_pct", "soil_temp_c", "ph", "days_since_irrigation",
    "irrigation_mm",
]

# Canonical model input order. Changing this list invalidates saved artifacts,
# so it is versioned alongside them via metrics.json.
FEATURE_COLUMNS = [
    # --- live sensor state ---
    "soil_ec", "soil_ec_delta_7d", "soil_moisture_pct", "soil_temp_c", "ph",
    # --- weather, current and aggregated ---
    "t_mean_1d", "t_max_1d", "t_mean_7d", "t_max_7d",
    "precip_1d", "precip_7d", "precip_30d",
    "et0_1d", "et0_7d", "et0_30d",
    "humidity_7d", "wind_7d",
    # --- derived water balance ---
    "water_balance_7d", "water_balance_30d", "aridity_index_7d",
    # --- phenology ---
    "days_after_planting", "season_progress", "kc_current",
    # --- crop physiology (physical encoding, not one-hot) ---
    "crop_salt_threshold", "crop_salt_slope", "crop_root_depth", "crop_depletion_p",
    # --- soil hydraulics ---
    "soil_theta_fc", "soil_theta_wp", "soil_infiltration", "soil_leach_efficiency",
    "drainage_factor",
    # --- salinisation drivers ---
    "irrigation_water_ec", "water_table_depth_m", "capillary_potential",
    "salt_load_index", "days_since_irrigation",
    "irrigation_depth_30d", "irrigation_events_30d", "salt_applied_30d",
    "leaching_balance_30d",
    "lat",
    # --- forward-looking weather (Open-Meteo 16-day forecast at serve time;
    #     actual future values from the simulation during training) ---
    "precip_next_7d", "et0_next_7d", "et0_next_14d", "forecast_water_balance_7d",
]

# The salinity target is a 30-day *change*, not a level. Two reasons, both of
# which showed up empirically before this was changed:
#
#   1. Predicting the level is a rigged game. Soil ECe moves slowly, so "next
#      week equals today" scores R2=0.987 on its own -- and the trained model
#      lost to it. Forecasting the delta puts the naive baseline at "no change"
#      and measures whether the model adds anything real.
#   2. Over 7 days ECe drifts ~0.05 dS/m, which is below sensor noise. At 30
#      days the signal clears the noise floor, and a month is also the horizon
#      on which a farmer can actually schedule a leaching irrigation.
SALINITY_HORIZON_DAYS = 30

TARGET_COLUMNS = [
    "target_salinity_delta_30d",
    "target_water_stress",
    "target_irrigation_mm",
    "target_health",
]

_ROLLING_WINDOWS = (7, 30)


def _rolling(df: pd.DataFrame, col: str, window: int, how: str) -> pd.Series:
    """Backward-looking per-field rolling stat, aligned to the original index.

    `min_periods=1` is deliberate: a field with only three days of history should
    still get a prediction rather than a NaN, which matters when a farmer
    registers a new field mid-season.

    Uses `groupby(...)[col].transform(...)` rather than `groupby.apply` so the
    result keeps the caller's index and never reorders rows — an apply-based
    version silently misaligned features against targets.
    """
    def _agg(s: pd.Series) -> pd.Series:
        r = s.rolling(window=window, min_periods=1)
        return r.sum() if how == "sum" else r.mean()

    return df.groupby("field_id")[col].transform(_agg)


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn time-ordered raw observations into the model feature matrix.

    Parameters
    ----------
    raw
        One row per field-day, containing at least ``RAW_COLUMNS``, sorted by
        ``field_id`` then ``date``. Serving passes a short window (~30 days) and
        uses only the final row; training passes the full history.

    Returns
    -------
    DataFrame with exactly ``FEATURE_COLUMNS``, same index as ``raw``.
    """
    missing = [c for c in RAW_COLUMNS if c not in raw.columns]
    if missing:
        raise ValueError(f"build_features missing required columns: {missing}")

    df = raw.sort_values(["field_id", "date"]).copy()

    # --- weather aggregates -------------------------------------------------
    df["t_mean_1d"] = df["t_mean"]
    df["t_max_1d"] = df["t_max"]
    df["precip_1d"] = df["precip_mm"]
    df["et0_1d"] = df["et0_mm"]

    for w in _ROLLING_WINDOWS:
        df[f"precip_{w}d"] = _rolling(df, "precip_mm", w, "sum")
        df[f"et0_{w}d"] = _rolling(df, "et0_mm", w, "sum")

    df["t_mean_7d"] = _rolling(df, "t_mean", 7, "mean")
    df["t_max_7d"] = _rolling(df, "t_max", 7, "mean")
    df["humidity_7d"] = _rolling(df, "humidity_pct", 7, "mean")
    df["wind_7d"] = _rolling(df, "wind_ms", 7, "mean")

    # --- sensor dynamics ----------------------------------------------------
    # The 7-day change in soil EC is the single most informative salinity
    # feature: absolute EC says where you are, the delta says where you're going.
    df["soil_ec_delta_7d"] = (
        df["soil_ec"] - df.groupby("field_id")["soil_ec"].shift(7)
    ).fillna(0.0)

    # --- derived water balance ---------------------------------------------
    df["water_balance_7d"] = df["precip_7d"] - df["et0_7d"]
    df["water_balance_30d"] = df["precip_30d"] - df["et0_30d"]
    df["aridity_index_7d"] = df["et0_7d"] / (df["precip_7d"] + 1.0)

    # --- crop / soil / drainage constants ----------------------------------
    specs = df["crop"].map(get_crop)
    df["crop_salt_threshold"] = specs.map(lambda s: s.salt_threshold_a)
    df["crop_salt_slope"] = specs.map(lambda s: s.salt_slope_b)
    df["crop_root_depth"] = specs.map(lambda s: s.root_depth_m)
    df["crop_depletion_p"] = specs.map(lambda s: s.depletion_fraction)
    season = specs.map(lambda s: s.season_days).astype(float)
    df["season_progress"] = (df["days_after_planting"] / season).clip(0.0, 1.0)
    df["kc_current"] = [
        crop_coefficient(sp, int(d))
        for sp, d in zip(specs, df["days_after_planting"], strict=False)
    ]

    soils = df["soil_texture"].map(get_soil)
    df["soil_theta_fc"] = soils.map(lambda s: s.theta_fc)
    df["soil_theta_wp"] = soils.map(lambda s: s.theta_wp)
    df["soil_infiltration"] = soils.map(lambda s: s.infiltration_mm_hr)
    df["soil_leach_efficiency"] = soils.map(lambda s: s.leaching_efficiency)
    df["drainage_factor"] = df["drainage_class"].map(get_drainage_factor)

    # --- engineered salinisation drivers -----------------------------------
    # Capillary potential: how strongly a shallow water table can wick salt into
    # the root zone. Mirrors the exponential decay in physics.capillary_rise so
    # the model gets the mechanism as an input rather than having to rediscover it.
    gap = (df["water_table_depth_m"] - df["crop_root_depth"]).clip(lower=0.0)
    df["capillary_potential"] = np.exp(-gap / 0.7)

    # Cumulative salt arriving via irrigation: concentration x evaporative demand.
    df["salt_load_index"] = df["irrigation_water_ec"] * df["et0_30d"]

    # --- irrigation history -------------------------------------------------
    # How a field was watered over the past month is the strongest available
    # clue to how it will be watered over the next one, and applied water is the
    # main salt import pathway. Without these the 30-day salinity forecast is
    # being asked to guess the farmer's behaviour from weather alone.
    df["irrigation_depth_30d"] = _rolling(df, "irrigation_mm", 30, "sum")
    df["irrigation_events_30d"] = _rolling(
        df.assign(_evt=(df["irrigation_mm"] > 0).astype(float)), "_evt", 30, "sum"
    )
    df["salt_applied_30d"] = df["irrigation_depth_30d"] * df["irrigation_water_ec"]

    # Net leaching balance: water in beyond what the atmosphere took back. When
    # positive, water percolates and carries salt down; when negative, salt
    # concentrates in the root zone. This is the salinisation mechanism in one number.
    df["leaching_balance_30d"] = (
        df["precip_30d"] + df["irrigation_depth_30d"] - df["et0_30d"]
    )

    # --- forward-looking weather features ----------------------------------
    # At serving time these come from Open-Meteo's 16-day forecast (injected
    # by build_history_frame). During training they are filled from the actual
    # future simulation values. Both paths call this same function, so the
    # feature is computed identically. Falls back to 0 when absent (e.g.
    # ingest_csv or a field with no forecast data).
    for _fc in ("precip_next_7d", "et0_next_7d", "et0_next_14d"):
        if _fc not in df.columns:
            df[_fc] = 0.0
    df["forecast_water_balance_7d"] = df["precip_next_7d"] - df["et0_next_7d"]

    out = df[FEATURE_COLUMNS].astype(float)
    return out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
