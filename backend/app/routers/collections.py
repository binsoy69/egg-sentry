from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import CountSnapshot, User
from app.schemas import CollectionCreateRequest, CollectionCreateResponse
from app.services import (
    build_collection_entry,
    collected_count_for_day,
    create_collection,
    current_count_for_device,
    current_local_date,
    get_device_by_identifier,
    get_primary_device,
    utc_now,
)


router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionCreateResponse, status_code=status.HTTP_201_CREATED)
def collect_eggs(
    payload: CollectionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = get_device_by_identifier(db, payload.device_id) if payload.device_id else get_primary_device(db)
    if not device:
        raise HTTPException(status_code=404, detail="No device found")

    before_count = current_count_for_device(db, device)
    if before_count <= 0:
        raise HTTPException(status_code=400, detail="No eggs available to collect")

    collected_at = utc_now()
    entry = create_collection(
        db,
        device=device,
        collected_count=before_count,
        before_count=before_count,
        after_count=0,
        source="manual",
        collected_at=collected_at,
        user=current_user,
    )
    db.add(
        CountSnapshot(
            device_id=device.id,
            total_count=0,
            size_breakdown=None,
            captured_at=collected_at,
        )
    )
    db.commit()
    db.refresh(entry)

    today = current_local_date()
    collected_today = collected_count_for_day(db, device, today)
    return CollectionCreateResponse(
        entry=build_collection_entry(entry),
        current_eggs=0,
        collected_today=collected_today,
        total_today=collected_today,
    )
