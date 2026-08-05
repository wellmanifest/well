from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


class JsonlEventStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self._events: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        if self.path and self.path.exists():
            self._refresh_from_disk_unlocked()

    def _refresh_from_disk_unlocked(self) -> None:
        if not self.path or not self.path.exists():
            return
        parsed: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                # A different process may be appending the final line. The next
                # read retries without exposing a partial event.
                continue
        if len(parsed) >= len(self._events):
            self._events = parsed

    def append(
        self,
        event_type: str,
        data: Any,
        *,
        stream: str = "wellmanifest",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self._refresh_from_disk_unlocked()
            event = {
                "spec": "wellmanifest.event/v1",
                "id": str(uuid4()),
                "stream": stream,
                "sequence": 1 + sum(1 for item in self._events if item.get("stream") == stream),
                "type": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "correlationId": correlation_id,
                "causationId": causation_id,
                "data": data,
                "metadata": metadata or {},
            }
            self._events.append(event)
            if self.path:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")
            return event

    def read(self, *, stream: str | None = None, after: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            self._refresh_from_disk_unlocked()
            events = [item for item in self._events if stream is None or item.get("stream") == stream]
            return [item.copy() for item in events[after : after + min(max(limit, 0), 1000)]]

    def count(self) -> int:
        with self._lock:
            self._refresh_from_disk_unlocked()
            return len(self._events)
