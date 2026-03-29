import argparse
from datetime import date

from app.database import SessionLocal
from app.services import (
    collected_count_for_day,
    count_for_day,
    current_count_for_device,
    current_local_date,
    get_device_by_identifier,
    get_primary_device,
    reconcile_day_detections_to_target,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile live egg detections for a device/day without clearing runtime data.",
    )
    parser.add_argument(
        "--device-id",
        default=None,
        help="Device identifier such as cam-001. Defaults to the primary device.",
    )
    parser.add_argument(
        "--date",
        dest="target_date",
        default=None,
        help="Local app date in YYYY-MM-DD format. Defaults to today.",
    )
    parser.add_argument(
        "--target-total",
        type=int,
        default=None,
        help="Explicit target detection total for the selected day. Required for past dates.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the reconciliation. Without this flag the command runs in dry-run mode.",
    )
    return parser.parse_args()


def resolve_target_date(raw_value: str | None) -> date:
    if raw_value is None:
        return current_local_date()
    return date.fromisoformat(raw_value)


def main() -> int:
    args = parse_args()
    target_date = resolve_target_date(args.target_date)

    with SessionLocal() as db:
        device = get_device_by_identifier(db, args.device_id) if args.device_id else get_primary_device(db)
        if device is None:
            print("No device found.")
            return 1

        current_count = current_count_for_device(db, device)
        collected_today = collected_count_for_day(db, device, target_date)
        actual_total = count_for_day(db, device, target_date)

        if args.target_total is not None:
            target_total = max(0, args.target_total)
        elif target_date == current_local_date():
            target_total = current_count + collected_today
        else:
            print("A past date requires --target-total because the current snapshot only applies to today.")
            return 1

        result = reconcile_day_detections_to_target(
            db,
            device=device,
            target_date=target_date,
            target_total=target_total,
            dry_run=not args.apply,
        )

        print(f"Device: {device.device_id} ({device.name})")
        print(f"Date: {target_date.isoformat()}")
        print(f"Current eggs: {current_count}")
        print(f"Collected that day: {collected_today}")
        print(f"Actual detections: {result['actual_total']}")
        print(f"Target detections: {result['target_total']}")
        print(f"Would remove: {result['removed']}" if not args.apply else f"Removed: {result['removed']}")

        if not args.apply:
            print("Dry run only. Re-run with --apply to persist the reconciliation.")
            return 0

        db.commit()
        print("Reconciliation applied.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
