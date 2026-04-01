from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import HistoryResponse
from app.services import (
    app_tz,
    build_collection_history_records,
    get_device_by_identifier,
    query_collections,
    resolve_collection_size_breakdowns,
)


router = APIRouter(prefix="/history", tags=["history"])


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
    resolved_start = start_date or from_date
    resolved_end = end_date or to_date
    tz = app_tz()
    start = datetime.combine(resolved_start, time.min, tzinfo=tz).astimezone(timezone.utc) if resolved_start else None
    end = (
        datetime.combine(resolved_end + timedelta(days=1), time.min, tzinfo=tz).astimezone(timezone.utc)
        if resolved_end
        else None
    )
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
