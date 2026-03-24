from app.database import SessionLocal
from app.services import clear_runtime_data


def main() -> int:
    with SessionLocal() as db:
        result = clear_runtime_data(db)
        db.commit()

    print("Cleared runtime data while preserving users and devices:")
    for key, value in result.items():
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
