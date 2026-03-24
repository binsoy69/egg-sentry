from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.config import get_settings
from app.models import Device, User


settings = get_settings()


def seed_defaults(db: Session) -> dict[str, int | str]:
    created_users = 0
    created_devices = 0

    defaults = [
        (settings.seed_admin_username, settings.seed_admin_password, settings.seed_admin_display_name),
        (settings.seed_viewer_username, settings.seed_viewer_password, settings.seed_viewer_display_name),
    ]
    for username, password, display_name in defaults:
        existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing:
            continue
        db.add(
            User(
                username=username,
                password_hash=get_password_hash(password),
                display_name=display_name,
                is_active=True,
            )
        )
        created_users += 1

    existing_device = db.execute(select(Device).where(Device.device_id == settings.seed_device_id)).scalar_one_or_none()
    if not existing_device:
        db.add(
            Device(
                device_id=settings.seed_device_id,
                api_key=settings.seed_device_api_key,
                name=settings.seed_device_name,
                location=settings.seed_device_location,
                num_cages=settings.seed_device_num_cages,
                num_chickens=settings.seed_device_num_chickens,
                min_size_threshold=40.0,
                max_size_threshold=80.0,
                confidence_threshold=0.85,
                is_active=True,
            )
        )
        created_devices += 1

    db.commit()
    return {
        "users_created": created_users,
        "devices_created": created_devices,
        "seed_device_id": settings.seed_device_id,
        "seed_admin_username": settings.seed_admin_username,
        "seed_viewer_username": settings.seed_viewer_username,
    }
