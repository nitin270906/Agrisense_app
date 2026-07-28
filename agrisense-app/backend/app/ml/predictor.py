"""Model loading and inference.

Artifacts are loaded once at process start and held in a module-level singleton;
re-reading joblib files per request would dominate response time.

The critical correctness property here is that inference calls the *same*
`build_features` as training. The caller hands over a time-ordered window of
recent field-days and this module takes the final row, so every rolling
aggregate is computed by identical code on both sides.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock

import joblib
import numpy as np
import pandas as pd

from app.config import ARTIFACTS_DIR
from app.ml.features import (
    FEATURE_COLUMNS,
    SALINITY_HORIZON_DAYS,
    TARGET_COLUMNS,
    build_features,
)
from app.ml.physics import salinity_risk_level

logger = logging.getLogger(__name__)

# Human-readable names for the features surfaced as "why" on each prediction.
FEATURE_LABELS: dict[str, str] = {
    "soil_ec": "current soil salinity",
    "soil_ec_delta_7d": "recent salinity trend",
    "soil_moisture_pct": "soil moisture",
    "irrigation_water_ec": "salinity of irrigation water",
    "water_table_depth_m": "depth to water table",
    "capillary_potential": "capillary rise from groundwater",
    "salt_load_index": "accumulated salt loading",
    "salt_applied_30d": "salt applied via irrigation (30d)",
    "leaching_balance_30d": "net leaching balance (30d)",
    "irrigation_depth_30d": "irrigation applied (30d)",
    "irrigation_events_30d": "irrigation frequency (30d)",
    "et0_30d": "evaporative demand (30d)",
    "et0_7d": "evaporative demand (7d)",
    "precip_7d": "rainfall (7d)",
    "precip_30d": "rainfall (30d)",
    "water_balance_7d": "rainfall minus evaporation (7d)",
    "water_balance_30d": "rainfall minus evaporation (30d)",
    "aridity_index_7d": "aridity",
    "drainage_factor": "field drainage",
    "days_since_irrigation": "days since last irrigation",
    "kc_current": "crop stage water demand",
    "season_progress": "growth stage",
    "crop_salt_threshold": "crop salt tolerance",
    "t_max_7d": "recent peak temperature",
    "soil_theta_fc": "soil water-holding capacity",
}


@dataclass(frozen=True)
class PredictionResult:
    salinity_ec: float          # forecast ECe at the horizon (dS/m)
    salinity_delta: float       # change from today (dS/m)
    water_stress_index: float   # 0-1
    irrigation_need_mm: float
    health_score: float         # 0-100
    risk_level: str
    confidence: float           # 0-1
    horizon_days: int
    model_version: str
    drivers: list[dict]
    salinity_ec_p10: float | None = None   # 10th percentile forecast
    salinity_ec_p90: float | None = None   # 90th percentile forecast

    def to_dict(self) -> dict:
        return asdict(self)


class Predictor:
    """Lazily-loaded holder for the four regressors and their manifest."""

    def __init__(self, artifacts_dir: Path = ARTIFACTS_DIR) -> None:
        self._dir = artifacts_dir
        self._models: dict[str, object] = {}
        self._q_models: dict[str, dict[str, object]] = {}  # target -> {"q10": m, "q90": m}
        self._manifest: dict = {}
        self._lock = Lock()
        self._loaded = False

    # -- lifecycle ---------------------------------------------------------- #
    def load(self) -> bool:
        """Load artifacts. Returns False (without raising) if any are missing.

        A missing-artifact case must degrade to the physics fallback rather than
        crash the API — the app has to boot even on a machine where training has
        not been run yet.
        """
        with self._lock:
            if self._loaded:
                return True
            try:
                for target in TARGET_COLUMNS:
                    path = self._dir / f"{target}.joblib"
                    if not path.exists():
                        logger.warning("Model artifact missing: %s", path)
                        return False
                    self._models[target] = joblib.load(path)

                manifest_path = self._dir / "metrics.json"
                if manifest_path.exists():
                    self._manifest = json.loads(manifest_path.read_text())

                # Quantile models are optional — they don't exist until the
                # user has run at least one training pass with the new code.
                for target in TARGET_COLUMNS:
                    q_map: dict[str, object] = {}
                    for suffix in ("q10", "q90"):
                        q_path = self._dir / f"{target}_{suffix}.joblib"
                        if q_path.exists():
                            q_map[suffix] = joblib.load(q_path)
                    if q_map:
                        self._q_models[target] = q_map

                self._loaded = True
                logger.info("Loaded %d models (v%s)", len(self._models), self.model_version)
                return True
            except Exception:
                logger.exception("Failed to load model artifacts")
                self._models.clear()
                return False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_version(self) -> str:
        return str(self._manifest.get("model_version", "0.0.0"))

    @property
    def manifest(self) -> dict:
        return self._manifest

    # -- inference ---------------------------------------------------------- #
    def _confidence(self, target: str, history_days: int) -> float:
        """Confidence from held-out skill, discounted when history is thin.

        Deliberately not a probability. It is a transparency signal: a field
        with four days of readings genuinely supports a weaker claim than one
        with two months, and the UI should say so rather than imply false
        precision.
        """
        metrics = self._manifest.get("metrics", {}).get(target, {})
        r2 = float(metrics.get("overall", {}).get("r2", 0.5))
        base = max(0.05, min(0.95, r2))
        # Rolling windows are 30 days wide; below that, features are incomplete.
        coverage = min(1.0, history_days / 30.0)
        return round(base * (0.55 + 0.45 * coverage), 3)

    def _drivers(self, target: str, row: pd.Series, top_n: int = 3) -> list[dict]:
        """Top contributing features, as plain-language 'why' strings."""
        model = self._models.get(target)
        if model is None:
            return []
        importances = getattr(model, "feature_importances_", None)
        if importances is None:
            return []

        ranked = sorted(
            zip(FEATURE_COLUMNS, importances.tolist(), strict=True),
            key=lambda kv: kv[1], reverse=True,
        )
        out = []
        for name, weight in ranked[:top_n]:
            out.append({
                "feature": name,
                "label": FEATURE_LABELS.get(name, name.replace("_", " ")),
                "value": round(float(row.get(name, 0.0)), 3),
                "importance": round(float(weight), 4),
            })
        return out

    def predict(self, history: pd.DataFrame) -> PredictionResult:
        """Predict for the most recent day in a field's history window.

        Parameters
        ----------
        history
            Time-ordered rows with `features.RAW_COLUMNS`, ideally the last 30+
            days for the rolling windows to be fully populated.
        """
        if not self._loaded and not self.load():
            raise RuntimeError("Model artifacts unavailable")
        if history.empty:
            raise ValueError("predict() requires at least one row of history")

        feats = build_features(history)
        x = feats.iloc[[-1]]           # single-row frame keeps column names
        row = x.iloc[0]

        raw_preds: dict[str, float] = {}
        for target in TARGET_COLUMNS:
            raw_preds[target] = float(self._models[target].predict(x)[0])

        current_ec = float(history.iloc[-1]["soil_ec"])
        delta = raw_preds["target_salinity_delta_30d"]
        forecast_ec = max(0.0, current_ec + delta)

        water_stress = float(np.clip(raw_preds["target_water_stress"], 0.0, 1.0))
        irrigation = max(0.0, raw_preds["target_irrigation_mm"])
        health = float(np.clip(raw_preds["target_health"], 0.0, 100.0))

        # Risk is driven by the forecast, not today's reading -- warning about a
        # threshold crossing before it happens is the entire point of the tool.
        risk = salinity_risk_level(forecast_ec)

        confidence = float(np.mean([
            self._confidence(t, len(history)) for t in TARGET_COLUMNS
        ]))

        # Prediction intervals from quantile regressors (if trained).
        salinity_p10: float | None = None
        salinity_p90: float | None = None
        q_map = self._q_models.get("target_salinity_delta_30d", {})
        if "q10" in q_map and "q90" in q_map:
            delta_p10 = float(q_map["q10"].predict(x)[0])
            delta_p90 = float(q_map["q90"].predict(x)[0])
            salinity_p10 = round(max(0.0, current_ec + delta_p10), 2)
            salinity_p90 = round(max(0.0, current_ec + delta_p90), 2)

        return PredictionResult(
            salinity_ec=round(forecast_ec, 2),
            salinity_delta=round(delta, 3),
            water_stress_index=round(water_stress, 3),
            irrigation_need_mm=round(irrigation, 1),
            health_score=round(health, 1),
            risk_level=risk,
            confidence=round(confidence, 3),
            horizon_days=SALINITY_HORIZON_DAYS,
            model_version=self.model_version,
            drivers=self._drivers("target_salinity_delta_30d", row),
            salinity_ec_p10=salinity_p10,
            salinity_ec_p90=salinity_p90,
        )


predictor = Predictor()
