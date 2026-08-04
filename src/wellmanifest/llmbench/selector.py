from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .adapters import CompletionAdapter
from .cases import format_instruction
from .models import BenchmarkCase, BenchmarkConfig, BenchmarkReport, CompletionMetrics, ModelCandidate
from .runner import BenchmarkRunner, benchmark_fingerprint


class FirstRequestModelSelector:
    """Benchmark fixed synthetic fixtures once, then route real requests once.

    The actual user request is not broadcast to every candidate. Cache entries
    are keyed by the benchmark/config fingerprint and store both the model and
    the selected operational format.
    """

    def __init__(self, adapter: CompletionAdapter, *, cache_path: str | Path | None = None) -> None:
        self.adapter = adapter
        self.cache_path = Path(cache_path) if cache_path else None

    def select(
        self,
        config: BenchmarkConfig,
        cases: list[BenchmarkCase],
    ) -> tuple[ModelCandidate, BenchmarkReport | None]:
        candidate, _selected_format, report = self.select_route(config, cases)
        return candidate, report

    def select_route(
        self,
        config: BenchmarkConfig,
        cases: list[BenchmarkCase],
    ) -> tuple[ModelCandidate, str, BenchmarkReport | None]:
        fingerprint = benchmark_fingerprint(config, cases)
        cached = self._read_cache(fingerprint, config.selection.cache_ttl_seconds)
        if cached:
            candidate = next((item for item in config.models if item.id == cached["model_id"]), None)
            selected_format = str(cached.get("selected_format") or "")
            if candidate is not None and selected_format in config.formats:
                return candidate, selected_format, None

        report = BenchmarkRunner(self.adapter).run(config, cases)
        if not report.selected_model_id or not report.selected_format:
            raise RuntimeError("No model/format route passed the configured capability thresholds")
        candidate = next(item for item in config.models if item.id == report.selected_model_id)
        self._write_cache(fingerprint, candidate.id, report.selected_format)
        return candidate, report.selected_format, report

    def complete_selected(
        self,
        config: BenchmarkConfig,
        cases: list[BenchmarkCase],
        messages: list[dict[str, str]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ModelCandidate, CompletionMetrics, BenchmarkReport | None]:
        candidate, _selected_format, completion, report = self.complete_selected_route(
            config,
            cases,
            messages,
            metadata=metadata,
        )
        return candidate, completion, report

    def complete_selected_route(
        self,
        config: BenchmarkConfig,
        cases: list[BenchmarkCase],
        messages: list[dict[str, str]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ModelCandidate, str, CompletionMetrics, BenchmarkReport | None]:
        candidate, selected_format, report = self.select_route(config, cases)
        completion_metadata = dict(metadata or {})
        completion_metadata["wellmanifest_format"] = selected_format
        routed_messages = [
            {
                "role": "system",
                "content": (
                    f"WellManifest selected operational format: {selected_format}. "
                    f"{format_instruction(selected_format)}"
                ),
            },
            *messages,
        ]
        completion = self.adapter.complete(candidate, routed_messages, metadata=completion_metadata)
        return candidate, selected_format, completion, report

    def _read_cache(self, fingerprint: str, ttl: int) -> dict[str, str] | None:
        if self.cache_path is None or not self.cache_path.exists():
            return None
        try:
            payload = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if payload.get("fingerprint") != fingerprint:
                return None
            if time.time() - float(payload.get("created_at", 0)) > ttl:
                return None
            model_id = str(payload.get("model_id") or "")
            selected_format = str(payload.get("selected_format") or "")
            if not model_id or not selected_format:
                return None
            return {"model_id": model_id, "selected_format": selected_format}
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _write_cache(self, fingerprint: str, model_id: str, selected_format: str) -> None:
        if self.cache_path is None:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "fingerprint": fingerprint,
            "model_id": model_id,
            "selected_format": selected_format,
            "created_at": time.time(),
        }
        self.cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
