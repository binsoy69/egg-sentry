from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_device, get_current_user
from app.models import Device
from app.schemas import (
    DeviceConfigToggleRequest,
    DeviceHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceRead,
    DeviceUpdateRequest,
)
from app.services import count_for_day, current_local_date, evaluate_alerts, get_device_by_identifier, status_for_device


router = APIRouter(prefix="/devices", tags=["devices"])


def _serialize_device(db: Session, device: Device) -> DeviceRead:
    is_online, status = status_for_device(device)
    return DeviceRead(
        id=device.id,
        device_id=device.device_id,
        name=device.name,
        location=device.location,
        num_cages=device.num_cages,
        num_chickens=device.num_chickens,
        min_size_threshold=device.min_size_threshold,
        max_size_threshold=device.max_size_threshold,
        confidence_threshold=device.confidence_threshold,
        last_heartbeat=device.last_heartbeat,
        is_active=device.is_active,
        created_at=device.created_at,
        is_online=is_online,
        status=status,
        today_count=count_for_day(db, device, current_local_date()),
        is_config_active=device.is_active,
    )


@router.post("/heartbeat", response_model=DeviceHeartbeatResponse)
def heartbeat(
    payload: DeviceHeartbeatRequest,
    db: Session = Depends(get_db),
    current_device: Device = Depends(get_current_device),
):
    if payload.device_id != current_device.device_id:
        raise HTTPException(status_code=400, detail="Device ID does not match authenticated device")
    current_device.last_heartbeat = payload.timestamp
    db.add(current_device)
    evaluate_alerts(db, current_device)
    db.commit()
    return DeviceHeartbeatResponse()


@router.get("", response_model=list[DeviceRead])
def list_devices(db: Session = Depends(get_db), _=Depends(get_current_user)):
    devices = list(db.execute(select(Device).order_by(Device.id.asc())).scalars().all())
    evaluate_alerts(db)
    db.commit()
    return [_serialize_device(db, device) for device in devices]


@router.get("/{identifier}", response_model=DeviceRead)
def get_device(identifier: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    device = get_device_by_identifier(db, identifier)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    evaluate_alerts(db, device)
    db.commit()
    return _serialize_device(db, device)


@router.put("/{identifier}", response_model=DeviceRead)
def update_device(
    identifier: str,
    payload: DeviceUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = get_device_by_identifier(db, identifier)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, field, value)

    db.add(device)
    db.commit()
    db.refresh(device)
    return _serialize_device(db, device)


@router.put("/{identifier}/config", response_model=DeviceRead)
def toggle_device_config(
    identifier: str,
    payload: DeviceConfigToggleRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = get_device_by_identifier(db, identifier)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.is_active = payload.is_active
    db.add(device)
    db.commit()
    db.refresh(device)
    return _serialize_device(db, device)
