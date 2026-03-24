from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import HistoryResponse
from app.services import app_tz, build_history_record, get_device_by_identifier, query_detections


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
    detections = query_detections(db, device=device, start=start, end=end)
    if filter_size:
        detections = [item for item in detections if item.size == filter_size]
    detections = sorted(detections, key=lambda item: item.detected_at, reverse=True)
    total_records = len(detections)
    start_idx = (page - 1) * limit
    page_items = detections[start_idx : start_idx + limit]
    for item in page_items:
        _ = item.device
    return HistoryResponse(
        total_records=total_records,
        page=page,
        limit=limit,
        records=[build_history_record(item) for item in page_items],
    )
