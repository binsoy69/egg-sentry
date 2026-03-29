from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.models import CountSnapshot
from tests.helpers import create_event_payload


def test_event_ingestion_and_events_alias(client: TestClient, auth_headers: dict, device_headers: dict):
    ingest_response = client.post(
        "/api/events",
        json=create_event_payload(timestamp=datetime.now(timezone.utc), sizes=["medium", "large"]),
        headers=device_headers,
    )

    assert ingest_response.status_code == 201
    assert ingest_response.json()["events_created"] == 2

    events_response = client.get("/api/events", headers=auth_headers)

    assert events_response.status_code == 200
    assert len(events_response.json()) == 2
    assert events_response.json()[0]["device_id"] == "cam-001"


def test_event_ingestion_backfills_missing_history_records(client: TestClient, auth_headers: dict, device_headers: dict):
    timestamp = datetime.now(timezone.utc)
    payload = create_event_payload(timestamp=timestamp, sizes=["jumbo"], total_count=3)
    payload["size_breakdown"] = {"jumbo": 3}

    ingest_response = client.post("/api/events", json=payload, headers=device_headers)

    assert ingest_response.status_code == 201
    assert ingest_response.json()["events_created"] == 3

    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert summary_response.status_code == 200
    assert summary_response.json()["current_eggs"] == 3
    assert summary_response.json()["all_time_eggs"] == 3

    assert history_response.status_code == 200
    body = history_response.json()
    assert body["total_records"] == 3
    assert len(body["records"]) == 3
    assert all(record["size"] == "jumbo" for record in body["records"])


def test_event_ingestion_corrects_repeated_sizes_for_ui_and_snapshot(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
    db_session,
):
    timestamp = datetime.now(timezone.utc)
    payload = {
        "device_id": "cam-001",
        "timestamp": timestamp.isoformat(),
        "total_count": 3,
        "new_eggs": [
            {
                "size": "jumbo",
                "confidence": 0.91,
                "bbox_area_normalized": 0.0042,
                "detected_at": timestamp.isoformat(),
            },
            {
                "size": "jumbo",
                "confidence": 0.92,
                "bbox_area_normalized": 0.0052,
                "detected_at": (timestamp + timedelta(microseconds=1)).isoformat(),
            },
            {
                "size": "jumbo",
                "confidence": 0.93,
                "bbox_area_normalized": 0.0064,
                "detected_at": (timestamp + timedelta(microseconds=2)).isoformat(),
            },
        ],
        "size_breakdown": {"jumbo": 3},
    }

    ingest_response = client.post("/api/events", json=payload, headers=device_headers)
    history_response = client.get("/api/history", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert ingest_response.status_code == 201
    assert history_response.status_code == 200
    assert summary_response.status_code == 200

    history_sizes = Counter(record["size"] for record in history_response.json()["records"])
    assert history_sizes == {"large": 1, "extra-large": 1, "jumbo": 1}

    summary_body = summary_response.json()
    assert summary_body["size_distribution"] == {"L": 1, "XL": 1, "Jumbo": 1}

    snapshot = db_session.query(CountSnapshot).order_by(CountSnapshot.id.desc()).first()
    assert snapshot is not None
    assert snapshot.size_breakdown == {"large": 1, "extra-large": 1, "jumbo": 1}


def test_event_ingestion_forces_repeated_jumbo_bias_downward_even_without_area_spread(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
):
    timestamp = datetime.now(timezone.utc)
    payload = {
        "device_id": "cam-001",
        "timestamp": timestamp.isoformat(),
        "total_count": 5,
        "new_eggs": [
            {
                "size": "large",
                "confidence": 0.88,
                "bbox_area_normalized": 0.004,
                "detected_at": timestamp.isoformat(),
            },
            {
                "size": "jumbo",
                "confidence": 0.9,
                "bbox_area_normalized": 0.005,
                "detected_at": (timestamp + timedelta(microseconds=1)).isoformat(),
            },
            {
                "size": "jumbo",
                "confidence": 0.9,
                "bbox_area_normalized": 0.005,
                "detected_at": (timestamp + timedelta(microseconds=2)).isoformat(),
            },
            {
                "size": "jumbo",
                "confidence": 0.9,
                "bbox_area_normalized": 0.005,
                "detected_at": (timestamp + timedelta(microseconds=3)).isoformat(),
            },
            {
                "size": "jumbo",
                "confidence": 0.9,
                "bbox_area_normalized": 0.005,
                "detected_at": (timestamp + timedelta(microseconds=4)).isoformat(),
            },
        ],
        "size_breakdown": {"large": 1, "jumbo": 4},
    }

    ingest_response = client.post("/api/events", json=payload, headers=device_headers)
    history_response = client.get("/api/history", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert ingest_response.status_code == 201
    assert history_response.status_code == 200
    assert summary_response.status_code == 200

    history_sizes = Counter(record["size"] for record in history_response.json()["records"])
    assert history_sizes == {"medium": 1, "large": 2, "extra-large": 1, "jumbo": 1}

    summary_body = summary_response.json()
    assert summary_body["size_distribution"] == {"M": 1, "L": 2, "XL": 1, "Jumbo": 1}


def test_event_ingestion_forces_repeated_small_bias_upward_even_without_area_spread(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
):
    timestamp = datetime.now(timezone.utc)
    payload = {
        "device_id": "cam-001",
        "timestamp": timestamp.isoformat(),
        "total_count": 5,
        "new_eggs": [
            {
                "size": "small",
                "confidence": 0.9,
                "bbox_area_normalized": 0.002,
                "detected_at": timestamp.isoformat(),
            },
            {
                "size": "small",
                "confidence": 0.9,
                "bbox_area_normalized": 0.002,
                "detected_at": (timestamp + timedelta(microseconds=1)).isoformat(),
            },
            {
                "size": "small",
                "confidence": 0.9,
                "bbox_area_normalized": 0.002,
                "detected_at": (timestamp + timedelta(microseconds=2)).isoformat(),
            },
            {
                "size": "small",
                "confidence": 0.9,
                "bbox_area_normalized": 0.002,
                "detected_at": (timestamp + timedelta(microseconds=3)).isoformat(),
            },
            {
                "size": "medium",
                "confidence": 0.88,
                "bbox_area_normalized": 0.003,
                "detected_at": (timestamp + timedelta(microseconds=4)).isoformat(),
            },
        ],
        "size_breakdown": {"small": 4, "medium": 1},
    }

    ingest_response = client.post("/api/events", json=payload, headers=device_headers)
    history_response = client.get("/api/history", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert ingest_response.status_code == 201
    assert history_response.status_code == 200
    assert summary_response.status_code == 200

    history_sizes = Counter(record["size"] for record in history_response.json()["records"])
    assert history_sizes == {"small": 1, "medium": 2, "large": 1, "extra-large": 1}

    summary_body = summary_response.json()
    assert summary_body["size_distribution"] == {"S": 1, "M": 2, "L": 1, "XL": 1}


def test_event_ingestion_forces_repeated_unknown_bias_into_balanced_real_sizes(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
):
    timestamp = datetime.now(timezone.utc)
    payload = {
        "device_id": "cam-001",
        "timestamp": timestamp.isoformat(),
        "total_count": 5,
        "new_eggs": [
            {
                "size": "unknown",
                "confidence": 0.5,
                "bbox_area_normalized": 0.0025,
                "detected_at": timestamp.isoformat(),
            },
            {
                "size": "unknown",
                "confidence": 0.5,
                "bbox_area_normalized": 0.0025,
                "detected_at": (timestamp + timedelta(microseconds=1)).isoformat(),
            },
            {
                "size": "unknown",
                "confidence": 0.5,
                "bbox_area_normalized": 0.0025,
                "detected_at": (timestamp + timedelta(microseconds=2)).isoformat(),
            },
            {
                "size": "unknown",
                "confidence": 0.5,
                "bbox_area_normalized": 0.0025,
                "detected_at": (timestamp + timedelta(microseconds=3)).isoformat(),
            },
            {
                "size": "large",
                "confidence": 0.88,
                "bbox_area_normalized": 0.003,
                "detected_at": (timestamp + timedelta(microseconds=4)).isoformat(),
            },
        ],
        "size_breakdown": {"unknown": 4, "large": 1},
    }

    ingest_response = client.post("/api/events", json=payload, headers=device_headers)
    history_response = client.get("/api/history", headers=auth_headers)
    summary_response = client.get("/api/dashboard/summary", headers=auth_headers)

    assert ingest_response.status_code == 201
    assert history_response.status_code == 200
    assert summary_response.status_code == 200

    history_sizes = Counter(record["size"] for record in history_response.json()["records"])
    assert history_sizes == {"small": 1, "medium": 1, "large": 2, "extra-large": 1}

    summary_body = summary_response.json()
    assert summary_body["size_distribution"] == {"S": 1, "M": 1, "L": 2, "XL": 1}


def test_single_new_egg_redistributes_when_previous_snapshot_is_biased(
    client: TestClient,
    auth_headers: dict,
    device_headers: dict,
    db_session,
):
    first_timestamp = datetime.now(timezone.utc)
    first_payload = {
        "device_id": "cam-001",
        "timestamp": first_timestamp.isoformat(),
        "total_count": 1,
        "new_eggs": [
            {
                "size": "jumbo",
                "confidence": 0.9,
                "bbox_area_normalized": 0.0051,
                "detected_at": first_timestamp.isoformat(),
            }
        ],
        "size_breakdown": {"jumbo": 1},
    }
    second_timestamp = first_timestamp + timedelta(minutes=1)
    second_payload = {
        "device_id": "cam-001",
        "timestamp": second_timestamp.isoformat(),
        "total_count": 2,
        "new_eggs": [
            {
                "size": "jumbo",
                "confidence": 0.9,
                "bbox_area_normalized": 0.0051,
                "detected_at": second_timestamp.isoformat(),
            }
        ],
        "size_breakdown": {"jumbo": 2},
    }

    first_response = client.post("/api/events", json=first_payload, headers=device_headers)
    second_response = client.post("/api/events", json=second_payload, headers=device_headers)
    history_response = client.get("/api/history", headers=auth_headers)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert history_response.status_code == 200

    history_sizes = Counter(record["size"] for record in history_response.json()["records"])
    assert history_sizes == {"jumbo": 1, "extra-large": 1}

    latest_snapshot = db_session.query(CountSnapshot).order_by(CountSnapshot.id.desc()).first()
    assert latest_snapshot is not None
    assert latest_snapshot.size_breakdown == {"jumbo": 1, "extra-large": 1}
