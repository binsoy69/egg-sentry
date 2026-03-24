from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Alert
from app.schemas import AlertDismissResponse, AlertRead, AlertsResponse
from app.services import evaluate_alerts


router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertsResponse)
def list_alerts(
    status: str = Query(default="active", pattern="^(active|all|dismissed)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    evaluate_alerts(db)
    db.commit()

    stmt = select(Alert).order_by(Alert.created_at.desc())
    if status == "active":
        stmt = stmt.where(Alert.is_dismissed.is_(False))
    elif status == "dismissed":
        stmt = stmt.where(Alert.is_dismissed.is_(True))

    alerts = list(db.execute(stmt).scalars().all())
    total = len(alerts)
    start = (page - 1) * limit
    items = alerts[start : start + limit]
    return AlertsResponse(
        total=total,
        alerts=[
            AlertRead(
                id=alert.id,
                type=alert.type,
                severity=alert.severity,
                message=alert.message,
                created_at=alert.created_at,
                dismissed=alert.is_dismissed,
                device_id=alert.device.device_id if alert.device else None,
            )
            for alert in items
        ],
    )


@router.put("/{alert_id}/dismiss", response_model=AlertDismissResponse)
def dismiss_alert(alert_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    alert = db.execute(select(Alert).where(Alert.id == alert_id)).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_dismissed = True
    alert.dismissed_at = datetime.now(timezone.utc)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return AlertDismissResponse(id=alert.id, dismissed=alert.is_dismissed, dismissed_at=alert.dismissed_at)
