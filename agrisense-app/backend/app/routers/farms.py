"""Farm and field CRUD."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories import core as repo
from app.schemas import FarmCreate, FarmOut, FieldCreate, FieldOut

router = APIRouter(tags=["farms"])


@router.get("/farms", response_model=list[FarmOut])
def list_farms(db: Session = Depends(get_db)) -> list[FarmOut]:
    counts = repo.count_fields_by_farm(db)
    out = []
    for farm in repo.list_farms(db):
        payload = FarmOut.model_validate(farm)
        payload.field_count = counts.get(farm.id, 0)
        out.append(payload)
    return out


@router.post("/farms", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmCreate, db: Session = Depends(get_db)) -> FarmOut:
    return FarmOut.model_validate(repo.create_farm(db, **payload.model_dump()))


@router.get("/farms/{farm_id}", response_model=FarmOut)
def get_farm(farm_id: int, db: Session = Depends(get_db)) -> FarmOut:
    farm = repo.get_farm(db, farm_id)
    if farm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Farm {farm_id} not found")
    payload = FarmOut.model_validate(farm)
    payload.field_count = len(farm.fields)
    return payload


@router.get("/fields", response_model=list[FieldOut])
def list_fields(
    farm_id: int | None = Query(default=None), db: Session = Depends(get_db)
) -> list[FieldOut]:
    return [FieldOut.model_validate(f) for f in repo.list_fields(db, farm_id)]


@router.post("/fields", response_model=FieldOut, status_code=status.HTTP_201_CREATED)
def create_field(payload: FieldCreate, db: Session = Depends(get_db)) -> FieldOut:
    if repo.get_farm(db, payload.farm_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Farm {payload.farm_id} not found")

    data = payload.model_dump()
    # Enums carry into the DB as their string values.
    data["soil_texture"] = payload.soil_texture.value
    data["drainage_class"] = payload.drainage_class.value
    return FieldOut.model_validate(repo.create_field(db, **data))


@router.get("/fields/{field_id}", response_model=FieldOut)
def get_field(field_id: int, db: Session = Depends(get_db)) -> FieldOut:
    field = repo.get_field(db, field_id)
    if field is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Field {field_id} not found")
    return FieldOut.model_validate(field)
