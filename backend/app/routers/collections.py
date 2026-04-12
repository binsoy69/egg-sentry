from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import CountSnapshot, EggCollection, User
from app.schemas import (
    CollectionCreateRequest,
    CollectionCreateResponse,
    CollectionMutationResponse,
    CollectionUpdateRequest,
)
from app.services import (
    build_collection_entry,
    collected_count_for_day,
    create_collection,
    current_count_for_device,
    current_local_date,
    get_device_by_identifier,
    get_primary_device,
    latest_snapshot_for_device,
    local_day_bounds,
    normalize_collection_size_breakdown,
    reconcile_day_detections_to_target,
    utc_now,
)


router = APIRouter(prefix="/collections", tags=["collections"])


def _resolve_device(db: Session, device_id: str | None):
    device = get_device_by_identifier(db, device_id) if device_id else get_primary_device(db)
    if not device:
        raise HTTPException(status_code=404, detail="No device found")
    return device


def _today_collection(db: Session, collection_id: int) -> EggCollection:
    start, end = local_day_bounds(current_local_date())
    collection = db.execute(
        select(EggCollection).where(
            EggCollection.id == collection_id,
            EggCollection.collected_at >= start,
            EggCollection.collected_at < end,
        )
    ).scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="Today's collection entry not found")
    _ = collection.device
    return collection


def _today_collections_for_device(db: Session, device_id: str | None) -> list[EggCollection]:
    device = _resolve_device(db, device_id)
    start, end = local_day_bounds(current_local_date())
    collections = list(
        db.execute(
            select(EggCollection).where(
                EggCollection.device_id == device.id,
                EggCollection.collected_at >= start,
                EggCollection.collected_at < end,
            )
        )
        .scalars()
        .all()
    )
    for collection in collections:
        _ = collection.device
    return collections


def _mutation_response(
    db: Session,
    *,
    device,
    message: str,
    affected_count: int,
    entry: EggCollection | None = None,
) -> CollectionMutationResponse:
    db.flush()
    today = current_local_date()
    collected_today = collected_count_for_day(db, device, today)
    reconcile_day_detections_to_target(
        db,
        device=device,
        target_date=today,
        target_total=collected_today,
        dry_run=False,
    )
    db.commit()
    if entry:
        db.refresh(entry)
    return CollectionMutationResponse(
        message=message,
        affected_count=affected_count,
        entry=build_collection_entry(entry) if entry else None,
        current_eggs=current_count_for_device(db, device),
        collected_today=collected_today,
        total_today=collected_today,
    )


@router.post("", response_model=CollectionCreateResponse, status_code=status.HTTP_201_CREATED)
def collect_eggs(
    payload: CollectionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = _resolve_device(db, payload.device_id)

    before_count = current_count_for_device(db, device)
    if before_count <= 0:
        raise HTTPException(status_code=400, detail="No eggs available to collect")

    collected_at = utc_now()
    latest_snapshot = latest_snapshot_for_device(db, device)
    entry = create_collection(
        db,
        device=device,
        collected_count=before_count,
        before_count=before_count,
        after_count=0,
        source="manual",
        collected_at=collected_at,
        size_breakdown=latest_snapshot.size_breakdown if latest_snapshot else None,
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
    reconcile_day_detections_to_target(
        db,
        device=device,
        target_date=today,
        target_total=collected_today,
        dry_run=False,
    )
    db.commit()
    total_today = collected_today
    return CollectionCreateResponse(
        entry=build_collection_entry(entry),
        current_eggs=0,
        collected_today=collected_today,
        total_today=total_today,
    )


@router.delete("/today", response_model=CollectionMutationResponse)
def clear_today_collections(
    device_id: str | None = None,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    collections = _today_collections_for_device(db, device_id)
    device = _resolve_device(db, device_id)
    affected_count = len(collections)
    for collection in collections:
        db.delete(collection)
    return _mutation_response(
        db,
        device=device,
        message="Cleared today's collection entries.",
        affected_count=affected_count,
    )


@router.patch("/{collection_id}", response_model=CollectionMutationResponse)
def update_collection(
    collection_id: int,
    payload: CollectionUpdateRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    collection = _today_collection(db, collection_id)
    device = collection.device
    count = int(payload.count)
    collection.collected_count = count
    collection.before_count = count
    collection.after_count = 0
    collection.size_breakdown = normalize_collection_size_breakdown(count, collection.size_breakdown)
    db.add(collection)
    return _mutation_response(
        db,
        device=device,
        message="Updated today's collection entry.",
        affected_count=1,
        entry=collection,
    )


@router.delete("/{collection_id}", response_model=CollectionMutationResponse)
def delete_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    collection = _today_collection(db, collection_id)
    device = collection.device
    db.delete(collection)
    return _mutation_response(
        db,
        device=device,
        message="Deleted today's collection entry.",
        affected_count=1,
    )
