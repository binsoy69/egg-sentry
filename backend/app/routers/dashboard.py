from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.schemas import (
    CompatibilityPeriodDistResponse,
    DailyChartResponse,
    DashboardDeviceSummary,
    DashboardSummaryResponse,
    PeriodStatsResponse,
    SizeDistributionItem,
    SizeDistributionResponse,
)
from app.services import (
    aggregate_sizes,
    app_tz,
    average_per_day,
    best_day_from_detections,
    build_collection_entry,
    collected_count_for_day,
    count_for_day,
    current_count_for_device,
    current_local_date,
    daily_chart_points,
    evaluate_alerts,
    get_device_by_identifier,
    get_primary_device,
    list_collections_for_day,
    month_bounds,
    query_detections,
    size_display,
    status_for_device,
    top_size_from_detections,
    week_of_month_bounds,
    year_bounds,
)


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _resolve_device(db: Session, device_id: str | None):
    device = get_device_by_identifier(db, device_id) if device_id else get_primary_device(db)
    if not device:
        raise HTTPException(status_code=404, detail="No device found")
    return device


@router.get("/summary", response_model=DashboardSummaryResponse)
def summary(
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    evaluate_alerts(db, device)
    db.commit()

    all_detections = query_detections(db, device=device)
    today = current_local_date()
    current_count = current_count_for_device(db, device)
    collected_today = collected_count_for_day(db, device, today)
    today_count = count_for_day(db, device, today)
    previous_day_total = count_for_day(db, device, today - timedelta(days=1))
    best_date, best_count = best_day_from_detections(all_detections)
    top_size, top_size_count = top_size_from_detections(all_detections)
    size_counts = aggregate_sizes(all_detections)
    is_online, status = status_for_device(device)
    collection_history = list_collections_for_day(db, device, today)

    device_summary = DashboardDeviceSummary(
        id=device.id,
        device_id=device.device_id,
        name=device.name,
        location=device.location,
        num_cages=device.num_cages,
        num_chickens=device.num_chickens,
        today_count=today_count,
        current_count=current_count,
        collected_today=collected_today,
        is_online=is_online,
        status=status,
    )
    return DashboardSummaryResponse(
        today_eggs=today_count,
        all_time_eggs=len(all_detections),
        current_eggs=current_count,
        collected_today=collected_today,
        best_day={"date": best_date.isoformat() if best_date else None, "count": best_count},
        top_size={"size": top_size, "count": top_size_count, "size_display": size_display(top_size)},
        device=device_summary,
        total_today=today_count,
        previous_day_total=previous_day_total,
        size_distribution={size_display(size): count for size, count in size_counts.items() if count > 0},
        collection_history=[build_collection_entry(item) for item in collection_history],
    )


@router.get("/weekly", response_model=PeriodStatsResponse)
def weekly(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=3000),
    week: int = Query(..., ge=1, le=6),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    start, end, first_day, last_day = week_of_month_bounds(year, month, week)
    detections = query_detections(db, device=device, start=start, end=end)
    total = len(detections)
    days = max((last_day - first_day).days + 1, 1)
    return PeriodStatsResponse(
        period=f"Week {week} ({first_day.day:02d}-{last_day.day:02d})",
        month=first_day.strftime("%b"),
        year=year,
        total_eggs=total,
        avg_per_day=average_per_day(total, days),
    )


@router.get("/monthly", response_model=PeriodStatsResponse)
def monthly(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000, le=3000),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    start, end = month_bounds(year, month)
    detections = query_detections(db, device=device, start=start, end=end)
    local_start = start.astimezone(app_tz()).date()
    local_end = (end - timedelta(days=1)).astimezone(app_tz()).date()
    days = (local_end - local_start).days + 1
    return PeriodStatsResponse(
        month=local_start.strftime("%B"),
        year=year,
        total_eggs=len(detections),
        avg_per_day=average_per_day(len(detections), days),
    )


@router.get("/yearly", response_model=PeriodStatsResponse)
def yearly(
    year: int = Query(..., ge=2000, le=3000),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    start, end = year_bounds(year)
    detections = query_detections(db, device=device, start=start, end=end)
    day_count = (date(year + 1, 1, 1) - date(year, 1, 1)).days
    return PeriodStatsResponse(year=year, total_eggs=len(detections), avg_per_day=average_per_day(len(detections), day_count))


@router.get("/daily-chart", response_model=DailyChartResponse)
def daily_chart(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    detections = query_detections(
        db,
        device=device,
        start=datetime.combine(from_date, time.min, tzinfo=app_tz()).astimezone(timezone.utc),
        end=datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=app_tz()).astimezone(timezone.utc),
    )
    return DailyChartResponse(data=daily_chart_points(detections, from_date, to_date))


@router.get("/size-distribution", response_model=SizeDistributionResponse)
def size_distribution(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    detections = query_detections(
        db,
        device=device,
        start=datetime.combine(from_date, time.min, tzinfo=app_tz()).astimezone(timezone.utc),
        end=datetime.combine(to_date + timedelta(days=1), time.min, tzinfo=app_tz()).astimezone(timezone.utc),
    )
    counts = aggregate_sizes(detections)
    items = [
        SizeDistributionItem(size=size, display=size_display(size), count=counts.get(size, 0))
        for size in ["small", "medium", "large", "extra-large", "jumbo"]
    ]
    return SizeDistributionResponse(data=items)


@router.get("/period-dist", response_model=CompatibilityPeriodDistResponse)
def period_dist(
    period: str = Query(default="week", pattern="^(week|month|year)$"),
    device_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    device = _resolve_device(db, device_id)
    today = current_local_date()
    if period == "week":
        start_date = today - timedelta(days=6)
    elif period == "month":
        start_date = today - timedelta(days=29)
    else:
        start_date = today - timedelta(days=364)
    detections = query_detections(
        db,
        device=device,
        start=datetime.combine(start_date, time.min, tzinfo=app_tz()).astimezone(timezone.utc),
        end=datetime.combine(today + timedelta(days=1), time.min, tzinfo=app_tz()).astimezone(timezone.utc),
    )
    return CompatibilityPeriodDistResponse(period=period, daily_data=daily_chart_points(detections, start_date, today))
