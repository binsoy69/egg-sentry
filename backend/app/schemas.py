from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None = None
    is_active: bool
    created_at: datetime


class DeviceHeartbeatRequest(BaseModel):
    device_id: str
    timestamp: datetime
    current_count: int = Field(ge=0, default=0)
    status: str = "ok"


class DeviceHeartbeatResponse(BaseModel):
    acknowledged: bool = True


class DeviceUpdateRequest(BaseModel):
    name: str | None = None
    location: str | None = None
    num_cages: int | None = Field(default=None, ge=1)
    num_chickens: int | None = Field(default=None, ge=1)
    min_size_threshold: float | None = Field(default=None, gt=0)
    max_size_threshold: float | None = Field(default=None, gt=0)
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    is_active: bool | None = None


class DeviceConfigToggleRequest(BaseModel):
    is_active: bool


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    name: str
    location: str | None = None
    num_cages: int
    num_chickens: int
    min_size_threshold: float
    max_size_threshold: float
    confidence_threshold: float
    last_heartbeat: datetime | None = None
    is_active: bool
    created_at: datetime
    is_online: bool
    status: Literal["online", "offline"]
    today_count: int = 0
    is_config_active: bool


class EventEggCreate(BaseModel):
    size: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    bbox_area_normalized: float | None = Field(default=None, ge=0.0)
    detected_at: datetime


class EventIngestRequest(BaseModel):
    device_id: str
    timestamp: datetime
    total_count: int = Field(ge=0)
    new_eggs: list[EventEggCreate] = Field(default_factory=list)
    size_breakdown: dict[str, int] | None = None


class EventIngestResponse(BaseModel):
    accepted: bool = True
    events_created: int
    daily_total: int


class BestDay(BaseModel):
    date: str | None = None
    count: int = 0


class TopSize(BaseModel):
    size: str | None = None
    count: int = 0
    size_display: str | None = None


class DashboardDeviceSummary(BaseModel):
    id: int
    device_id: str
    name: str
    location: str | None = None
    num_cages: int
    num_chickens: int
    today_count: int
    is_online: bool
    status: Literal["online", "offline"]


class DashboardSummaryResponse(BaseModel):
    today_eggs: int
    all_time_eggs: int
    best_day: BestDay
    top_size: TopSize
    device: DashboardDeviceSummary | None = None
    total_today: int
    previous_day_total: int
    size_distribution: dict[str, int]


class PeriodStatsResponse(BaseModel):
    period: str | None = None
    month: str | None = None
    year: int | None = None
    total_eggs: int
    avg_per_day: float


class DailyChartPoint(BaseModel):
    date: str
    count: int


class DailyChartResponse(BaseModel):
    data: list[DailyChartPoint]


class CompatibilityPeriodDistResponse(BaseModel):
    period: str
    daily_data: list[DailyChartPoint]


class SizeDistributionItem(BaseModel):
    size: str
    display: str
    count: int


class SizeDistributionResponse(BaseModel):
    data: list[SizeDistributionItem]


class HistoryRecord(BaseModel):
    id: int
    date: str
    size: str
    size_display: str
    detected_at: str
    confidence: float | None = None
    timestamp: str
    device_id: str
    estimated_size: str
    count: int = 1
    image_url: str | None = None


class HistoryResponse(BaseModel):
    total_records: int
    page: int
    limit: int
    records: list[HistoryRecord]


class AlertRead(BaseModel):
    id: int
    type: str
    severity: str
    message: str
    created_at: datetime
    dismissed: bool
    device_id: str | None = None


class AlertsResponse(BaseModel):
    alerts: list[AlertRead]
    total: int


class AlertDismissResponse(BaseModel):
    id: int
    dismissed: bool
    dismissed_at: datetime | None = None


class SeedResponse(BaseModel):
    users_created: int
    devices_created: int
    details: dict[str, Any]
