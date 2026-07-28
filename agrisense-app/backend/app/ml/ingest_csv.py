"""Drop-in path for real field data.

The models currently learn from simulated data because no public dataset pairs
soil-salinity time series with weather at field scale. This module is the seam
where measured data replaces that, *without* touching the feature builder or the
training script: it maps an arbitrary CSV onto `features.RAW_COLUMNS`, validates
it, and writes the same parquet `train.py` already consumes.

Usage
-----
    python -m app.ml.ingest_csv data/field_records.csv \\
        --map soil_ec=EC_dSm --map date=sample_date --crop-default wheat

Anything the CSV does not supply is filled from a documented default, and the
report prints exactly which columns were substituted — silently defaulting a
column the model leans on would quietly degrade every prediction.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from app.ml.crop_profiles import get_crop
from app.ml.features import RAW_COLUMNS, SALINITY_HORIZON_DAYS, TARGET_COLUMNS, build_features
from app.ml.generate import DATA_DIR
from app.ml.physics import (
    FieldState,
    crop_health_score,
    hargreaves_et0,
    water_stress_coefficient,
)

# Substituted when a column is absent. Deliberately conservative: a wrong default
# on a high-importance feature is worse than an obviously neutral one.
DEFAULTS: dict[str, object] = {
    "crop": "wheat",
    "soil_texture": "loam",
    "drainage_class": "moderate",
    "irrigation_water_ec": 1.0,
    "water_table_depth_m": 6.0,
    "lat": 28.0,
    "days_after_planting": 60,
    "humidity_pct": 55.0,
    "wind_ms": 2.0,
    "ph": 7.6,
    "irrigation_mm": 0.0,
    "days_since_irrigation": 7,
    "soil_moisture_pct": 22.0,
}


def _parse_mapping(pairs: list[str]) -> dict[str, str]:
    mapping = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--map expects canonical=source, got {pair!r}")
        canonical, source = pair.split("=", 1)
        mapping[canonical.strip()] = source.strip()
    return mapping


def normalise(
    df: pd.DataFrame, mapping: dict[str, str], crop_default: str
) -> tuple[pd.DataFrame, list[str]]:
    """Coerce an arbitrary frame into RAW_COLUMNS, reporting substitutions."""
    out = pd.DataFrame(index=df.index)
    substituted: list[str] = []

    for column in RAW_COLUMNS:
        source = mapping.get(column, column)
        if source in df.columns:
            out[column] = df[source]
            continue

        if column == "field_id":
            out[column] = 1
        elif column == "date":
            raise SystemExit(
                "A date column is required. Map it with --map date=<your column>."
            )
        elif column == "crop":
            out[column] = crop_default
            substituted.append(column)
        elif column == "root_depth_m":
            out[column] = np.nan  # derived below from the crop
        elif column in ("t_mean", "t_max", "t_min", "et0_mm", "precip_mm", "soil_temp_c"):
            out[column] = np.nan  # derived or interpolated below
            substituted.append(column)
        else:
            out[column] = DEFAULTS.get(column, 0.0)
            substituted.append(column)

    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values(["field_id", "date"])

    # Root depth always follows the crop rather than being guessed.
    out["root_depth_m"] = out["crop"].map(lambda c: get_crop(str(c)).root_depth_m)

    # Fill temperature gaps, then reconstruct anything still missing.
    for col in ("t_mean", "t_max", "t_min"):
        if out[col].isna().all():
            out[col] = {"t_mean": 24.0, "t_max": 31.0, "t_min": 17.0}[col]
        else:
            out[col] = out[col].interpolate().bfill().ffill()

    out["precip_mm"] = pd.to_numeric(out["precip_mm"], errors="coerce").fillna(0.0)

    # ET0 is the strongest driver in the model. If the source lacks it, estimate
    # with Hargreaves rather than defaulting to a constant.
    if out["et0_mm"].isna().all():
        out["et0_mm"] = [
            hargreaves_et0(tm, tx, tn, float(lat), int(pd.Timestamp(d).dayofyear))
            for tm, tx, tn, lat, d in zip(
                out["t_mean"], out["t_max"], out["t_min"], out["lat"], out["date"], strict=True
            )
        ]
    else:
        out["et0_mm"] = out["et0_mm"].interpolate().bfill().ffill()

    if out["soil_temp_c"].isna().all():
        out["soil_temp_c"] = out["t_mean"]
    else:
        out["soil_temp_c"] = out["soil_temp_c"].interpolate().bfill().ffill()

    if "soil_ec" not in df.columns and "soil_ec" not in mapping:
        raise SystemExit(
            "A soil EC column is required. Map it with --map soil_ec=<your column>."
        )

    return out.reset_index(drop=True), sorted(set(substituted))


def derive_targets(raw: pd.DataFrame) -> pd.DataFrame:
    """Attach training targets to measured data.

    Salinity change is observed directly. Water stress, irrigation need and
    health are not measurable from an EC probe, so they are reconstructed with
    the same physics used elsewhere — which keeps them consistent with the
    simulated corpus rather than introducing a second, incompatible definition.
    """
    frames = []
    for _, group in raw.groupby("field_id", sort=False):
        g = group.sort_values("date").copy()

        g["target_salinity_delta_30d"] = (
            g["soil_ec"].shift(-SALINITY_HORIZON_DAYS) - g["soil_ec"]
        )

        stress, need, health = [], [], []
        for row in g.itertuples():
            spec = get_crop(str(row.crop))
            state = FieldState(
                crop=str(row.crop),
                soil_texture=str(row.soil_texture),
                drainage_class=str(row.drainage_class),
                root_depth_m=float(row.root_depth_m),
                irrigation_water_ec=float(row.irrigation_water_ec),
                water_table_depth_m=float(row.water_table_depth_m),
            )
            state.set_initial_ece(float(row.soil_ec))

            # Infer depletion from the measured moisture reading.
            soil = state.soil
            theta = float(row.soil_moisture_pct) / 100.0
            depletion = max(0.0, (soil.theta_fc - theta) * 1000.0 * float(row.root_depth_m))
            state.depletion_mm = min(depletion, state.taw)

            ks = water_stress_coefficient(state.depletion_mm, state.taw, spec.depletion_fraction)
            stress.append(round(1.0 - ks, 4))
            need.append(state.irrigation_need())
            health.append(round(crop_health_score(float(row.soil_ec), ks, float(row.t_max), spec), 2))

        g["target_water_stress"] = stress
        g["target_irrigation_mm"] = need
        g["target_health"] = health
        frames.append(g)

    return pd.concat(frames, ignore_index=True).dropna(subset=["target_salinity_delta_30d"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a real field-data CSV for training.")
    parser.add_argument("csv", type=str, help="Path to the source CSV")
    parser.add_argument("--map", action="append", default=[],
                        help="canonical=source column mapping; repeatable")
    parser.add_argument("--crop-default", type=str, default="wheat")
    parser.add_argument("--out", type=str, default=str(DATA_DIR / "training_real.parquet"))
    args = parser.parse_args()

    source = Path(args.csv)
    if not source.exists():
        raise SystemExit(f"No such file: {source}")

    df = pd.read_csv(source)
    print(f"Read {len(df):,} rows x {df.shape[1]} columns from {source.name}")

    raw, substituted = normalise(df, _parse_mapping(args.map), args.crop_default)
    print(f"Normalised to {len(raw):,} rows across {raw.field_id.nunique()} field(s)")

    if substituted:
        print("\n  Columns filled from defaults (verify these before trusting the model):")
        for column in substituted:
            print(f"    - {column}: {DEFAULTS.get(column, 'derived')}")

    with_targets = derive_targets(raw)
    if with_targets.empty:
        raise SystemExit(
            f"No rows survived target derivation — the series needs more than "
            f"{SALINITY_HORIZON_DAYS} days per field to compute a 30-day change."
        )

    features = build_features(with_targets).reset_index(drop=True)
    dataset = pd.concat(
        [with_targets[["field_id"]].reset_index(drop=True), features,
         with_targets[TARGET_COLUMNS].reset_index(drop=True)],
        axis=1,
    ).dropna()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(out, index=False)

    print(f"\nWrote {len(dataset):,} training rows -> {out}")
    print(f"Train on it with:\n  python -m app.ml.train  "
          f"(after pointing DATA_DIR/training.parquet at this file)")


if __name__ == "__main__":
    sys.exit(main())
