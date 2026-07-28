"""Portfolio-level dashboard aggregation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import core as repo
from app.schemas import DashboardSummary, RecommendationOut
from app.services.dashboard import build_summary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    farm_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    return await build_summary(db, farm_id)


@router.get("/alerts", response_model=list[RecommendationOut])
def dashboard_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[RecommendationOut]:
    """Cross-field alerts, most urgent first.

    Reads the recommendations persisted by the last summary run rather than
    recomputing, so opening the alerts panel is instant.
    """
    return [
        RecommendationOut.model_validate(r)
        for r in repo.list_all_recommendations(db, limit)
    ]
