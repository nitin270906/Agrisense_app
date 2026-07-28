"""Train the four forecasting models and write versioned artifacts.

Evaluation choices worth defending
---------------------------------
**Whole fields are held out, never rows.** Consecutive days within a field are
near-identical, so a random row split lets the model see 5 May while predicting
6 May and reports an R2 that means nothing. Splitting on `field_id` measures the
question that actually matters: how well does this work on a farm we have never
seen?

**Every model is scored against a naive baseline.** For salinity that baseline is
persistence — "next week's ECe equals today's sensor reading" — which is a
genuinely strong predictor. An R2 of 0.95 is only impressive if persistence
scores worse, and reporting the comparison is the difference between a metric
and a marketing number.

**Zero-inflated targets are scored twice.** Water stress is zero ~86% of the
time because crops are unstressed most days. A model that always predicts zero
would post a respectable overall R2 while being useless for the only cases a
farmer cares about, so the tail is scored separately.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBRegressor

from app.config import ARTIFACTS_DIR
from app.ml.features import FEATURE_COLUMNS, TARGET_COLUMNS
from app.ml.generate import DATA_DIR, generate

MODEL_VERSION = "1.0.0"

XGB_PARAMS = dict(
    n_estimators=600,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.85,
    colsample_bytree=0.85,
    min_child_weight=5,
    reg_lambda=1.5,
    objective="reg:squarederror",
    tree_method="hist",
    random_state=42,
    early_stopping_rounds=40,
    eval_metric="rmse",
)

# Quantile models for prediction intervals (p10 / p90). Lighter than the point
# model — intervals don't need to be as sharp as the central estimate.
XGB_QUANTILE_PARAMS = dict(
    n_estimators=400,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.85,
    colsample_bytree=0.85,
    min_child_weight=5,
    objective="reg:quantileerror",
    tree_method="hist",
    random_state=42,
)

# Target -> the naive predictor it must beat to justify its existence.
# "no_change" is the persistence baseline expressed for a delta target: assume
# next month's salinity equals this month's. It is a genuinely hard bar.
BASELINES = {
    "target_salinity_delta_30d": "no_change",
    "target_water_stress": "mean",
    "target_irrigation_mm": "mean",
    "target_health": "mean",
}


def _baseline_prediction(target: str, X: pd.DataFrame, y_train: pd.Series) -> np.ndarray:
    if BASELINES[target] == "no_change":
        return np.zeros(len(X))
    return np.full(len(X), float(y_train.mean()))


def _evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "r2": round(float(r2_score(y_true, y_pred)), 4),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
        "rmse": round(float(np.sqrt(np.mean((y_true - y_pred) ** 2))), 4),
    }


def train_quantile(
    target: str, alpha: float,
    X_tr: pd.DataFrame, y_tr: pd.Series,
) -> XGBRegressor:
    """Train a quantile regressor for a prediction interval endpoint."""
    params = {**XGB_QUANTILE_PARAMS, "quantile_alpha": alpha}
    model = XGBRegressor(**params)
    cut = int(len(X_tr) * 0.85)
    model.fit(X_tr.iloc[:cut], y_tr.iloc[:cut], verbose=False)
    return model


def train_one(
    target: str,
    X_tr: pd.DataFrame, y_tr: pd.Series,
    X_te: pd.DataFrame, y_te: pd.Series,
) -> tuple[XGBRegressor, dict]:
    """Fit one target and return the model plus its full metric block."""
    # Carve a validation slice out of training for early stopping. The test set
    # stays untouched so the reported numbers remain out-of-sample.
    cut = int(len(X_tr) * 0.85)
    model = XGBRegressor(**XGB_PARAMS)
    model.fit(
        X_tr.iloc[:cut], y_tr.iloc[:cut],
        eval_set=[(X_tr.iloc[cut:], y_tr.iloc[cut:])],
        verbose=False,
    )

    pred = model.predict(X_te)
    # Clamp to each target's physical range. The salinity delta is deliberately
    # left unclamped below zero: a negative change is the signal that leaching
    # is working, and flooring it at zero would erase every improving field.
    if target == "target_water_stress":
        pred = np.clip(pred, 0.0, 1.0)
    elif target == "target_health":
        pred = np.clip(pred, 0.0, 100.0)
    elif target == "target_irrigation_mm":
        pred = np.clip(pred, 0.0, None)

    metrics = {
        "overall": _evaluate(y_te.to_numpy(), pred),
        "baseline": _evaluate(y_te.to_numpy(), _baseline_prediction(target, X_te, y_tr)),
        "best_iteration": int(getattr(model, "best_iteration", 0) or 0),
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
    }

    # Score the non-zero tail separately where the target is zero-inflated.
    # abs() so a signed target (the salinity delta) is handled correctly.
    nz = np.abs(y_te.to_numpy()) > 1e-6
    zero_share = float(1.0 - nz.mean())
    if zero_share > 0.25 and nz.sum() > 50:
        metrics["nonzero_tail"] = _evaluate(y_te.to_numpy()[nz], pred[nz])
        metrics["zero_share"] = round(zero_share, 4)

    importance = sorted(
        zip(FEATURE_COLUMNS, model.feature_importances_.tolist(), strict=True),
        key=lambda kv: kv[1], reverse=True,
    )
    metrics["top_features"] = [
        {"feature": f, "importance": round(float(v), 4)} for f, v in importance[:12]
    ]
    return model, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train salinity/stress models.")
    parser.add_argument("--fields", type=int, default=400)
    parser.add_argument("--regenerate", action="store_true",
                        help="Rebuild the synthetic dataset before training.")
    args = parser.parse_args()

    data_path = DATA_DIR / "training.parquet"
    if args.regenerate or not data_path.exists():
        print(f"Generating synthetic dataset ({args.fields} fields)...")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        df = generate(args.fields)
        df.to_parquet(data_path, index=False)
    else:
        df = pd.read_parquet(data_path)
    print(f"Dataset: {len(df):,} rows, {df.field_id.nunique()} fields\n")

    X = df[FEATURE_COLUMNS]
    groups = df["field_id"]

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, groups=groups))
    print(f"Hold-out split by field: {groups.iloc[train_idx].nunique()} train fields / "
          f"{groups.iloc[test_idx].nunique()} test fields (no overlap)\n")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    all_metrics: dict[str, dict] = {}

    for target in TARGET_COLUMNS:
        y = df[target]
        model, metrics = train_one(
            target,
            X.iloc[train_idx], y.iloc[train_idx],
            X.iloc[test_idx], y.iloc[test_idx],
        )
        all_metrics[target] = metrics
        joblib.dump(model, ARTIFACTS_DIR / f"{target}.joblib")

        # Quantile models for p10/p90 prediction intervals.
        for alpha, suffix in ((0.1, "q10"), (0.9, "q90")):
            q_model = train_quantile(target, alpha, X.iloc[train_idx], y.iloc[train_idx])
            joblib.dump(q_model, ARTIFACTS_DIR / f"{target}_{suffix}.joblib")

        o, b = metrics["overall"], metrics["baseline"]
        verdict = "beats baseline" if o["mae"] < b["mae"] else "!! NO BETTER THAN BASELINE"
        print(f"{target}")
        print(f"   model     R2={o['r2']:+.4f}  MAE={o['mae']:.4f}  RMSE={o['rmse']:.4f}")
        print(f"   baseline  R2={b['r2']:+.4f}  MAE={b['mae']:.4f}   ({BASELINES[target]})")
        if "nonzero_tail" in metrics:
            t = metrics["nonzero_tail"]
            print(f"   non-zero tail ({(1 - metrics['zero_share']) * 100:.0f}% of rows)  "
                  f"R2={t['r2']:+.4f}  MAE={t['mae']:.4f}")
        print(f"   -> {verdict}\n")

    manifest = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_columns": FEATURE_COLUMNS,
        "targets": TARGET_COLUMNS,
        "n_rows": int(len(df)),
        "n_fields": int(df.field_id.nunique()),
        "split": "GroupShuffleSplit by field_id (whole fields held out)",
        "data_provenance": (
            "Physics-simulated from FAO-56 water balance, Maas-Hoffman salt "
            "tolerance and a root-zone salt mass balance. Not field-measured."
        ),
        "metrics": all_metrics,
    }
    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(manifest, indent=2))
    print(f"Artifacts written to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
