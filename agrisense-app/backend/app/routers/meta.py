"""Health, model transparency and reference data."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.ml.features import FEATURE_COLUMNS
from app.ml.predictor import predictor
from app.repositories import core as repo
from app.schemas import CropProfileOut, HealthOut, ModelInfo

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
        database = "ok"
    except Exception as exc:  # pragma: no cover - surfaced in the response
        database = f"error: {exc}"

    return HealthOut(
        status="ok",
        model_loaded=predictor.is_loaded,
        model_version=predictor.model_version,
        weather_provider=settings.weather_provider,
        database=database,
    )


@router.get("/model/info", response_model=ModelInfo)
def model_info() -> ModelInfo:
    """Full model provenance — metrics, split strategy and data origin.

    Exposed as a first-class endpoint rather than buried in a README because the
    honest disclosure that these models are trained on physics-simulated data
    belongs in the product, not just the docs.
    """
    manifest = predictor.manifest
    return ModelInfo(
        model_version=predictor.model_version,
        trained_at=manifest.get("trained_at"),
        loaded=predictor.is_loaded,
        n_rows=manifest.get("n_rows"),
        n_fields=manifest.get("n_fields"),
        split=manifest.get("split"),
        data_provenance=manifest.get("data_provenance"),
        feature_count=len(FEATURE_COLUMNS),
        metrics=manifest.get("metrics", {}),
    )


@router.get("/meta/crops", response_model=list[CropProfileOut])
def list_crops(db: Session = Depends(get_db)) -> list[CropProfileOut]:
    return [CropProfileOut.model_validate(c) for c in repo.list_crop_profiles(db)]
