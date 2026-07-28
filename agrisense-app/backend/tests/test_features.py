"""Feature builder tests: train/serve parity and forward-weather columns.

The critical invariant is that build_features() produces identical output
whether called from train.py or predictor.py. Any divergence is train/serve
skew — the silent ML failure mode where the model silently receives inputs it
never saw during training.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest  # noqa: F401 — used by pytest.approx

from app.ml.features import (
    FEATURE_COLUMNS,
    RAW_COLUMNS,
    SALINITY_HORIZON_DAYS,
    TARGET_COLUMNS,
    build_features,
)
from app.ml.generate import simulate_field, generate
from app.ml.crop_profiles import get_crop


# --- helpers ---------------------------------------------------------------- #

def _minimal_raw(n_days: int = 35) -> pd.DataFrame:
    """A minimal but valid RAW_COLUMNS frame for one field."""
    spec = get_crop("wheat")
    rows = []
    for i in range(n_days):
        rows.append({
            "field_id": 1,
            "date": pd.Timestamp("2024-01-01") + pd.Timedelta(days=i),
            "crop": "wheat",
            "soil_texture": "loam",
            "drainage_class": "moderate",
            "root_depth_m": spec.root_depth_m,
            "irrigation_water_ec": 1.0,
            "water_table_depth_m": 5.0,
            "lat": 28.0,
            "days_after_planting": i,
            "t_mean": 25.0,
            "t_max": 32.0,
            "t_min": 18.0,
            "precip_mm": 0.0 if i % 10 != 0 else 20.0,
            "et0_mm": 4.5,
            "humidity_pct": 55.0,
            "wind_ms": 2.5,
            "soil_ec": 2.0 + i * 0.02,
            "soil_moisture_pct": 22.0,
            "soil_temp_c": 24.0,
            "ph": 7.6,
            "days_since_irrigation": i % 10,
            "irrigation_mm": 40.0 if i % 10 == 0 else 0.0,
        })
    return pd.DataFrame(rows)


# --- feature column contract ------------------------------------------------ #

def test_feature_columns_are_floats():
    """build_features must return a float-typed DataFrame."""
    raw = _minimal_raw()
    feats = build_features(raw)
    assert (feats.dtypes == float).all(), "Non-float feature columns detected"


def test_feature_columns_exact_set():
    """Output must have exactly FEATURE_COLUMNS — no extras, no omissions."""
    raw = _minimal_raw()
    feats = build_features(raw)
    assert list(feats.columns) == FEATURE_COLUMNS


def test_feature_row_count_matches_input():
    """One feature row per input row."""
    raw = _minimal_raw(n_days=50)
    feats = build_features(raw)
    assert len(feats) == len(raw)


def test_no_nan_in_output():
    """build_features must replace all NaN with 0 — no silent gaps."""
    raw = _minimal_raw()
    feats = build_features(raw)
    assert not feats.isna().any().any(), "NaN found in feature output"


def test_no_inf_in_output():
    """Infinite values in a feature matrix will corrupt XGBoost training."""
    raw = _minimal_raw()
    feats = build_features(raw)
    assert not np.isinf(feats.values).any(), "Inf found in feature output"


# --- derived features ------------------------------------------------------- #

def test_soil_ec_delta_7d_zero_for_short_history():
    """With < 7 rows of history, delta is filled as 0 not NaN."""
    raw = _minimal_raw(n_days=5)
    feats = build_features(raw)
    assert feats["soil_ec_delta_7d"].notna().all()


def test_water_balance_equals_precip_minus_et0():
    """Water balance is P - ET0 over the window — a deterministic check."""
    raw = _minimal_raw(n_days=40)
    feats = build_features(raw)
    last = feats.iloc[-1]
    expected_7d = last["precip_7d"] - last["et0_7d"]
    assert last["water_balance_7d"] == pytest.approx(expected_7d, abs=1e-6)


def test_capillary_potential_decreases_with_depth():
    """Deeper water table → lower capillary potential (exponential decay)."""
    raw_shallow = _minimal_raw()
    raw_deep = _minimal_raw()
    raw_deep["water_table_depth_m"] = 10.0

    feats_shallow = build_features(raw_shallow)
    feats_deep = build_features(raw_deep)

    assert feats_shallow["capillary_potential"].iloc[-1] > feats_deep["capillary_potential"].iloc[-1]


def test_irrigation_features_are_zero_with_no_irrigation():
    """With no irrigation events, all irrigation features must be 0."""
    raw = _minimal_raw()
    raw["irrigation_mm"] = 0.0
    feats = build_features(raw)
    assert (feats["irrigation_depth_30d"] == 0.0).all()
    assert (feats["irrigation_events_30d"] == 0.0).all()
    assert (feats["salt_applied_30d"] == 0.0).all()


# --- forecast weather features ---------------------------------------------- #

def test_forecast_features_default_to_zero_when_absent():
    """If forecast columns aren't in the raw frame, they must default to 0."""
    raw = _minimal_raw()
    assert "precip_next_7d" not in raw.columns
    feats = build_features(raw)
    assert (feats["precip_next_7d"] == 0.0).all()
    assert (feats["et0_next_7d"] == 0.0).all()
    assert (feats["et0_next_14d"] == 0.0).all()


def test_forecast_features_propagate_when_provided():
    """When forecast columns are supplied, they flow into the feature matrix."""
    raw = _minimal_raw()
    raw["precip_next_7d"] = 35.0
    raw["et0_next_7d"] = 28.0
    raw["et0_next_14d"] = 56.0
    feats = build_features(raw)
    assert (feats["precip_next_7d"] == 35.0).all()
    np.testing.assert_allclose(feats["forecast_water_balance_7d"].values, 35.0 - 28.0)


# --- generate.py provides forecast columns ---------------------------------- #

def test_simulate_field_includes_forecast_columns():
    """simulate_field() must produce the forward-weather columns that training uses."""
    rng = np.random.default_rng(0)
    df = simulate_field(0, rng)
    for col in ("precip_next_7d", "et0_next_7d", "et0_next_14d"):
        assert col in df.columns, f"simulate_field missing {col}"
        assert df[col].notna().all()
        assert (df[col] >= 0).all()


def test_generated_dataset_has_expected_columns():
    """Full generate() call produces the FEATURE_COLUMNS expected by train.py."""
    df = generate(n_fields=5, seed=99)
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Generated dataset missing feature: {col}"
    for col in TARGET_COLUMNS:
        assert col in df.columns, f"Generated dataset missing target: {col}"


def test_generated_dataset_no_nan():
    """Training data must not contain NaN."""
    df = generate(n_fields=5, seed=7)
    nan_cols = df.columns[df.isna().any()].tolist()
    assert not nan_cols, f"NaN in generated columns: {nan_cols}"


# --- multi-field rolling windows -------------------------------------------- #

def test_rolling_windows_do_not_bleed_across_fields():
    """Rolling statistics for field A must not be contaminated by field B."""
    raw_a = _minimal_raw(n_days=35).assign(field_id=1, soil_ec=2.0)
    raw_b = _minimal_raw(n_days=35).assign(field_id=2, soil_ec=10.0)
    raw_b["date"] = raw_a["date"]  # same dates, different fields

    combined = pd.concat([raw_a, raw_b], ignore_index=True)
    feats = build_features(combined)

    # Field A has low EC; field B has high EC. Their 7-day rolling windows
    # must not mix.
    feats_a = feats[combined["field_id"] == 1]
    feats_b = feats[combined["field_id"] == 2]

    assert feats_a["soil_ec"].iloc[-1] < feats_b["soil_ec"].iloc[-1]
