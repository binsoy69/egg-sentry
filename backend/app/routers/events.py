from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_device, get_current_user
from app.models import CountSnapshot, Device, EggDetection
from app.schemas import EventIngestRequest, EventIngestResponse
from app.services import (
    build_history_record,
    count_for_day,
    current_local_date,
    ensure_aware,
    evaluate_uncertain_detection_alert,
    get_device_by_identifier,
    query_detections,
)


router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResponse, status_code=201)
def ingest_events(
    payload: EventIngestRequest,
    db: Session = Depends(get_db),
    current_device: Device = Depends(get_current_device),
):
    if payload.device_id != current_device.device_id:
        raise HTTPException(status_code=400, detail="Device ID does not match authenticated device")

    db.add(
        CountSnapshot(
            device_id=current_device.id,
            total_count=payload.total_count,
            size_breakdown=payload.size_breakdown,
            captured_at=payload.timestamp,
        )
    )

    events_created = 0
    for egg in payload.new_eggs:
        db.add(
            EggDetection(
                device_id=current_device.id,
                size=egg.size,
                confidence=egg.confidence,
                bbox_area_normalized=egg.bbox_area_normalized,
                detected_at=egg.detected_at,
            )
        )
        events_created += 1

    current_device.last_heartbeat = payload.timestamp
    db.add(current_device)
    db.flush()
    evaluate_uncertain_detection_alert(db, current_device)
    db.commit()
    return EventIngestResponse(
        events_created=events_created,
        daily_total=count_for_day(db, current_device, current_local_date()),
    )


@router.get("")
def list_events(
    device_id: str | None = Query(default=None),
    size_class: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    skip: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = get_device_by_identifier(db, device_id) if device_id else None
    detections = query_detections(db, device=device, start=start_date, end=end_date)
    if size_class:
        detections = [item for item in detections if item.size == size_class]
    detections = sorted(detections, key=lambda item: ensure_aware(item.detected_at), reverse=True)
    page = detections[skip : skip + limit]
    for item in page:
        _ = item.device
    return [build_history_record(item).model_dump() for item in page]
