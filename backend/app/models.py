from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    collections: Mapped[list["EggCollection"]] = relationship(back_populates="user")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    api_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    num_cages: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    num_chickens: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    age_of_chicken_total_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_of_chicken_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    min_size_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=40.0, server_default="40")
    max_size_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=80.0, server_default="80")
    confidence_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.85, server_default="0.85"
    )
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    detections: Mapped[list["EggDetection"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    snapshots: Mapped[list["CountSnapshot"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    collections: Mapped[list["EggCollection"]] = relationship(back_populates="device", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="device")


class EggDetection(Base):
    __tablename__ = "egg_detections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    size: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_area_normalized: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="detections")


class CountSnapshot(Base):
    __tablename__ = "count_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    size_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    device: Mapped[Device] = relationship(back_populates="snapshots")


class EggCollection(Base):
    __tablename__ = "egg_collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    collected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    before_count: Mapped[int] = mapped_column(Integer, nullable=False)
    after_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    source: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    size_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    device: Mapped[Device] = relationship(back_populates="collections")
    user: Mapped[User | None] = relationship(back_populates="collections")


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped[Device | None] = relationship(back_populates="alerts")
