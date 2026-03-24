from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


@dataclass(frozen=True)
class DeliveryResult:
    delivered: bool
    queued: bool
    status_code: int | None = None
    response_body: dict[str, Any] | None = None
    queue_depth: int = 0


@dataclass(frozen=True)
class QueueFlushResult:
    flushed: int = 0
    dropped: int = 0
    remaining: int = 0


class ReporterError(RuntimeError):
    pass


class RetryableReporterError(ReporterError):
    pass


class PermanentReporterError(ReporterError):
    pass


class EventReporter:
    def __init__(
        self,
        *,
        backend_api_base_url: str,
        device_id: str,
        device_api_key: str,
        timeout_seconds: float = 10.0,
        retry_max_attempts: int = 3,
        retry_backoff_seconds: float = 1.0,
        retry_backoff_max_seconds: float = 8.0,
        offline_queue_path: str | Path,
        client: Any | None = None,
        sleep_func: Any = time.sleep,
    ) -> None:
        self.backend_api_base_url = backend_api_base_url.rstrip("/")
        self.device_id = device_id
        self.headers = {"X-Device-Key": device_api_key}
        self.timeout_seconds = timeout_seconds
        self.retry_max_attempts = max(1, retry_max_attempts)
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)
        self.retry_backoff_max_seconds = max(self.retry_backoff_seconds, retry_backoff_max_seconds)
        self.offline_queue_path = Path(offline_queue_path)
        self._sleep = sleep_func
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url=self.backend_api_base_url,
            timeout=self.timeout_seconds,
        )

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    def send_heartbeat(
        self,
        *,
        timestamp: datetime,
        current_count: int,
        status: str = "ok",
    ) -> DeliveryResult:
        payload = {
            "device_id": self.device_id,
            "timestamp": timestamp.isoformat(),
            "current_count": current_count,
            "status": status,
        }
        response = self._post_json("/devices/heartbeat", payload)
        return self._delivery_from_response(response)

    def send_event(
        self,
        *,
        timestamp: datetime,
        total_count: int,
        new_eggs: list[dict[str, Any]],
        size_breakdown: dict[str, int],
    ) -> DeliveryResult:
        payload = self._build_event_payload(
            timestamp=timestamp,
            total_count=total_count,
            new_eggs=new_eggs,
            size_breakdown=size_breakdown,
        )
        try:
            response = self._post_json("/events", payload)
        except RetryableReporterError:
            queue_depth = self.queue_event(payload)
            return DeliveryResult(delivered=False, queued=True, queue_depth=queue_depth)

        return self._delivery_from_response(response)

    def send_snapshot(
        self,
        *,
        timestamp: datetime,
        total_count: int,
        size_breakdown: dict[str, int],
    ) -> DeliveryResult:
        payload = self._build_event_payload(
            timestamp=timestamp,
            total_count=total_count,
            new_eggs=[],
            size_breakdown=size_breakdown,
        )
        try:
            response = self._post_json("/events", payload)
        except RetryableReporterError:
            return DeliveryResult(delivered=False, queued=False, queue_depth=self.queue_depth())

        return self._delivery_from_response(response)

    def _build_event_payload(
        self,
        *,
        timestamp: datetime,
        total_count: int,
        new_eggs: list[dict[str, Any]],
        size_breakdown: dict[str, int],
    ) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": timestamp.isoformat(),
            "total_count": total_count,
            "new_eggs": new_eggs,
            "size_breakdown": size_breakdown,
        }

    def _delivery_from_response(self, response: Any) -> DeliveryResult:
        return DeliveryResult(
            delivered=True,
            queued=False,
            status_code=response.status_code,
            response_body=self._coerce_json(response),
            queue_depth=self.queue_depth(),
        )

    def flush_event_queue(self) -> QueueFlushResult:
        queued = self._load_queue()
        if not queued:
            return QueueFlushResult()

        flushed = 0
        dropped = 0
        remaining: list[dict[str, Any]] = []

        for index, payload in enumerate(queued):
            try:
                self._post_json("/events", payload)
            except RetryableReporterError:
                remaining = queued[index:]
                break
            except PermanentReporterError:
                dropped += 1
            else:
                flushed += 1

        self._save_queue(remaining)
        return QueueFlushResult(flushed=flushed, dropped=dropped, remaining=len(remaining))

    def queue_event(self, payload: dict[str, Any]) -> int:
        queued = self._load_queue()
        queued.append(payload)
        self._save_queue(queued)
        return len(queued)

    def queue_depth(self) -> int:
        return len(self._load_queue())

    def _post_json(self, endpoint: str, payload: dict[str, Any]):
        last_error: Exception | None = None
        for attempt in range(1, self.retry_max_attempts + 1):
            try:
                response = self.client.post(endpoint, json=payload, headers=self.headers)
            except httpx.RequestError as exc:
                last_error = exc
                if attempt >= self.retry_max_attempts:
                    raise RetryableReporterError(
                        f"Request to {endpoint} failed after {attempt} attempts"
                    ) from exc
                self._sleep(self._backoff_for_attempt(attempt))
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                last_error = RetryableReporterError(self._error_message(endpoint, response))
                if attempt >= self.retry_max_attempts:
                    raise last_error
                self._sleep(self._backoff_for_attempt(attempt))
                continue

            if response.status_code >= 400:
                raise PermanentReporterError(self._error_message(endpoint, response))

            return response

        raise RetryableReporterError(f"Request to {endpoint} failed: {last_error}")

    def _backoff_for_attempt(self, attempt: int) -> float:
        delay = self.retry_backoff_seconds * (2 ** (attempt - 1))
        return min(delay, self.retry_backoff_max_seconds)

    def _error_message(self, endpoint: str, response: Any) -> str:
        body = getattr(response, "text", "")
        return f"{endpoint} returned HTTP {response.status_code}: {body}".strip()

    def _coerce_json(self, response: Any) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {"data": body}

    def _load_queue(self) -> list[dict[str, Any]]:
        if not self.offline_queue_path.exists():
            return []
        try:
            with self.offline_queue_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _save_queue(self, queued: list[dict[str, Any]]) -> None:
        if not queued:
            if self.offline_queue_path.exists():
                self.offline_queue_path.unlink()
            return

        self.offline_queue_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.offline_queue_path.with_suffix(self.offline_queue_path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(queued, handle, indent=2, sort_keys=True)
        temp_path.replace(self.offline_queue_path)
