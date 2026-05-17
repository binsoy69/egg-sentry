from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import SIZE_ORDER
from app.database import get_db
from app.dependencies import get_current_user, get_history_editor_user
from app.models import EggCollection, User
from app.schemas import (
    HistoryCollectionMutationRequest,
    HistoryCollectionRecord,
    HistoryCollectionsResponse,
    HistoryResponse,
)
from app.services import (
    app_tz,
    build_collection_history_records,
    create_collection,
    ensure_aware,
    get_device_by_identifier,
    localize,
    normalize_collection_size_breakdown,
    query_collections,
    resolve_collection_size_breakdowns,
)


router = APIRouter(prefix="/history", tags=["history"])


def _resolve_bounds(
    *,
    from_date: date | None,
    to_date: date | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime | None, datetime | None]:
    resolved_start = start_date or from_date
    resolved_end = end_date or to_date
    tz = app_tz()
    start = datetime.combine(resolved_start, time.min, tzinfo=tz).astimezone(timezone.utc) if resolved_start else None
    end = (
        datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
        if resolved_end
        else None
    )
    return start, end


def _resolve_requested_device(db: Session, device_id: str | None):
    if not device_id:
        return None
    device = get_device_by_identifier(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _get_collection(db: Session, collection_id: int) -> EggCollection:
    collection = db.execute(select(EggCollection).where(EggCollection.id == collection_id)).scalar_one_or_none()
    if not collection:
        raise HTTPException(status_code=404, detail="History collection entry not found")
    _ = collection.device
    return collection


def _total_count(size_breakdown: dict[str, int]) -> int:
    return sum(int(size_breakdown.get(size, 0)) for size in SIZE_ORDER)


def _positive_size_breakdown(size_breakdown: dict[str, int]) -> dict[str, int]:
    return {size: int(size_breakdown.get(size, 0)) for size in SIZE_ORDER if int(size_breakdown.get(size, 0)) > 0}


def _full_size_breakdown(size_breakdown: dict[str, int] | None) -> dict[str, int]:
    return {size: int((size_breakdown or {}).get(size, 0)) for size in SIZE_ORDER}


def _serialize_collection(
    collection: EggCollection,
    size_breakdown: dict[str, int] | None = None,
) -> HistoryCollectionRecord:
    resolved_breakdown = normalize_collection_size_breakdown(
        collection.collected_count,
        size_breakdown if size_breakdown is not None else collection.size_breakdown,
    )
    local_dt = localize(collection.collected_at)
    return HistoryCollectionRecord(
        id=collection.id,
        device_id=collection.device.device_id if collection.device else "",
        count=collection.collected_count,
        source="manual" if collection.source == "manual" else "automatic",
        size_breakdown=_full_size_breakdown(resolved_breakdown),
        collected_at=ensure_aware(collection.collected_at),
        collected_at_display=local_dt.strftime("%b %d, %Y, %I:%M %p"),
    )


@router.get("", response_model=HistoryResponse)
def get_history(
    device_id: str | None = Query(default=None),
    size: str | None = Query(default=None),
    size_class: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    start, end = _resolve_bounds(from_date=from_date, to_date=to_date, start_date=start_date, end_date=end_date)
    device = get_device_by_identifier(db, device_id) if device_id else None
    filter_size = size_class or (None if size == "all" else size)
    collections = query_collections(db, device=device, start=start, end=end)
    resolved_breakdowns = resolve_collection_size_breakdowns(db, collections)
    records = []
    for collection in reversed(collections):
        records.extend(build_collection_history_records(collection, resolved_breakdowns.get(collection.id)))
    if filter_size:
        records = [item for item in records if item.size == filter_size]
    total_records = len(records)
    start_idx = (page - 1) * limit
    page_items = records[start_idx : start_idx + limit]
    return HistoryResponse(
        total_records=total_records,
        page=page,
        limit=limit,
        records=page_items,
    )


@router.get("/collections", response_model=HistoryCollectionsResponse)
def get_history_collections(
    device_id: str | None = Query(default=None),
    size: str | None = Query(default=None),
    size_class: str | None = Query(default=None),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_history_editor_user),
):
    start, end = _resolve_bounds(from_date=from_date, to_date=to_date, start_date=start_date, end_date=end_date)
    device = _resolve_requested_device(db, device_id)
    filter_size = size_class or (None if size == "all" else size)
    if filter_size and filter_size not in SIZE_ORDER:
        raise HTTPException(status_code=422, detail="Invalid size filter")

    collections = list(reversed(query_collections(db, device=device, start=start, end=end)))
    resolved_breakdowns = resolve_collection_size_breakdowns(db, collections)
    if filter_size:
        collections = [
            collection
            for collection in collections
            if int((resolved_breakdowns.get(collection.id) or {}).get(filter_size, 0)) > 0
        ]

    total_records = len(collections)
    start_idx = (page - 1) * limit
    page_items = collections[start_idx : start_idx + limit]
    return HistoryCollectionsResponse(
        total_records=total_records,
        page=page,
        limit=limit,
        records=[_serialize_collection(item, resolved_breakdowns.get(item.id)) for item in page_items],
    )


@router.post(
    "/collections",
    response_model=HistoryCollectionRecord,
    status_code=status.HTTP_201_CREATED,
)
def create_history_collection(
    payload: HistoryCollectionMutationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_history_editor_user),
):
    device = _resolve_requested_device(db, payload.device_id)
    count = _total_count(payload.size_breakdown)
    entry = create_collection(
        db,
        device=device,
        collected_count=count,
        before_count=count,
        after_count=0,
        source="manual",
        collected_at=payload.collected_at,
        size_breakdown=_positive_size_breakdown(payload.size_breakdown),
        user=current_user,
        correct_size_bias=False,
    )
    db.commit()
    db.refresh(entry)
    return _serialize_collection(entry)


@router.patch("/collections/{collection_id}", response_model=HistoryCollectionRecord)
def update_history_collection(
    collection_id: int,
    payload: HistoryCollectionMutationRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_history_editor_user),
):
    collection = _get_collection(db, collection_id)
    device = _resolve_requested_device(db, payload.device_id)
    count = _total_count(payload.size_breakdown)

    collection.device_id = device.id
    collection.collected_count = count
    collection.before_count = count
    collection.after_count = 0
    collection.collected_at = ensure_aware(payload.collected_at)
    collection.size_breakdown = normalize_collection_size_breakdown(count, _positive_size_breakdown(payload.size_breakdown))
    db.add(collection)
    db.commit()
    db.refresh(collection)
    _ = collection.device
    return _serialize_collection(collection)


@router.delete("/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_collection(
    collection_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_history_editor_user),
):
    collection = _get_collection(db, collection_id)
    db.delete(collection)
    db.commit()
    return None
