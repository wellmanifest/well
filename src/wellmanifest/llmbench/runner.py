from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from statistics import fmean
from typing import Any

from wellmanifest.models import ValidationRequest
from wellmanifest.runtime import WellManifestRuntime

from .adapters import CompletionAdapter
from .cases import emit_expected
from .models import (
    BenchmarkAttempt,
    BenchmarkCase,
    BenchmarkConfig,
    BenchmarkReport,
    ModelCandidate,
    ModelSummary,
)


_DIALECTS = {
    "json": "json",
    "yaml": "yaml",
    "typed": "typed",
    "hcl": "hcl",
    "typescript": "typescript",
}


class BenchmarkRunner:
    def __init__(self, adapter: CompletionAdapter, *, runtime: WellManifestRuntime | None = None) -> None:
        self.adapter = adapter
        self.runtime = runtime or WellManifestRuntime()

    def run(self, config: BenchmarkConfig, cases: list[BenchmarkCase]) -> BenchmarkReport:
        attempts: list[BenchmarkAttempt] = []
        for candidate in config.models:
            for case in cases:
                expected_output = emit_expected(self.runtime, case.expected_data, case.target_format)
                wrong_output = emit_expected(self.runtime, {}, case.target_format)
                for repetition in range(1, config.repetitions + 1):
                    attempts.append(
                        self._run_attempt(
                            candidate,
                            case,
                            repetition,
                            expected_output=expected_output,
                            wrong_output=wrong_output,
                        )
                    )

        summaries = self._summaries(config, attempts, cases)
        selected = next((summary for summary in summaries if summary.rank == 1 and summary.capable), None)
        selected_format = self._select_operational_format(config, selected) if selected else None
        notes = [
            "Selection is based on deterministic parsing, JSON Schema validation and exact semantic comparison; no judge LLM is used.",
            "A model with unknown price remains measurable but is ranked after equally capable models with measured cost when cost is preferred.",
        ]
        return BenchmarkReport(
            benchmark_id=config.id,
            fingerprint=benchmark_fingerprint(config, cases),
            selected_model_id=selected.model_id if selected else None,
            selected_model=selected.model if selected else None,
            selected_format=selected_format,
            summaries=summaries,
            attempts=attempts,
            notes=notes,
        )

    def _run_attempt(
        self,
        candidate: ModelCandidate,
        case: BenchmarkCase,
        repetition: int,
        *,
        expected_output: str,
        wrong_output: str,
    ) -> BenchmarkAttempt:
        metrics = self.adapter.complete(
            candidate,
            [
                {
                    "role": "system",
                    "content": "Return deterministic structured data only. Never invent permissions or bypass a failed gate.",
                },
                {"role": "user", "content": case.prompt},
            ],
            metadata={
                "case_id": case.id,
                "target_format": case.target_format,
                "expected_output": expected_output,
                "wrong_output": wrong_output,
            },
        )
        output = strip_code_fence(metrics.text)
        errors: list[str] = []
        syntax_valid = False
        schema_valid = False
        semantic_valid = False
        normalized: Any = None
        try:
            document = self.runtime.parse(
                output,
                dialect=_DIALECTS[case.target_format],
                source_name=f"llm-output.{case.target_format}",
            )
            syntax_valid = document.ok
            normalized = document.data
            if document.diagnostics:
                errors.extend(f"{item.code}: {item.message}" for item in document.diagnostics if item.severity.value == "ERROR")
        except Exception as exc:
            errors.append(f"parse: {exc}")

        if syntax_valid:
            validation = self.runtime.validate(
                ValidationRequest(
                    source=normalized,
                    dialect="json",
                    schema=case.output_schema,
                    source_name=f"llm-output.{case.target_format}",
                )
            )
            schema_valid = validation.valid
            if not schema_valid:
                errors.extend(f"{item.code}: {item.message}" for item in validation.diagnostics)
            semantic_valid = normalized == case.expected_data
            if not semantic_valid:
                errors.append("semantic: normalized output differs from the deterministic expected result")

        score = round((0.25 if syntax_valid else 0.0) + (0.25 if schema_valid else 0.0) + (0.50 if semantic_valid else 0.0), 6)
        return BenchmarkAttempt(
            model_id=candidate.id,
            model=candidate.model,
            case_id=case.id,
            target_format=case.target_format,
            repetition=repetition,
            syntax_valid=syntax_valid,
            schema_valid=schema_valid,
            semantic_valid=semantic_valid,
            score=score,
            cost_usd=metrics.cost_usd,
            latency_ms=metrics.latency_ms,
            prompt_tokens=metrics.prompt_tokens,
            completion_tokens=metrics.completion_tokens,
            output=metrics.text,
            normalized=normalized,
            provider_metadata=metrics.provider_metadata,
            errors=errors,
        )

    @staticmethod
    def _summaries(
        config: BenchmarkConfig,
        attempts: list[BenchmarkAttempt],
        cases: list[BenchmarkCase],
    ) -> list[ModelSummary]:
        by_model: dict[str, list[BenchmarkAttempt]] = defaultdict(list)
        candidates = {candidate.id: candidate for candidate in config.models}
        for attempt in attempts:
            by_model[attempt.model_id].append(attempt)

        case_weights = {case.id: case.weight for case in cases}
        summaries: list[ModelSummary] = []
        for model_id, items in by_model.items():
            by_format: dict[str, list[BenchmarkAttempt]] = defaultdict(list)
            for item in items:
                by_format[item.target_format].append(item)
            format_scores: dict[str, float] = {}
            format_costs: dict[str, float | None] = {}
            format_latencies: dict[str, float] = {}
            for name, format_items in sorted(by_format.items()):
                weights = [case_weights.get(item.case_id, 1.0) for item in format_items]
                denominator = sum(weights) or 1.0
                format_scores[name] = round(
                    sum(item.score * weight for item, weight in zip(format_items, weights, strict=True)) / denominator,
                    6,
                )
                known_format_costs = [item.cost_usd for item in format_items if item.cost_usd is not None]
                format_costs[name] = (
                    round(sum(known_format_costs), 12)
                    if len(known_format_costs) == len(format_items)
                    else None
                )
                format_latencies[name] = round(fmean(item.latency_ms for item in format_items), 3)

            item_weights = [case_weights.get(item.case_id, 1.0) for item in items]
            total_denominator = sum(item_weights) or 1.0
            total_score = round(
                sum(item.score * weight for item, weight in zip(items, item_weights, strict=True)) / total_denominator,
                6,
            )
            known_costs = [item.cost_usd for item in items if item.cost_usd is not None]
            total_cost = round(sum(known_costs), 12) if len(known_costs) == len(items) else None
            latency = round(fmean(item.latency_ms for item in items), 3)
            capable = (
                total_score >= config.selection.minimum_total_score
                and all(score >= config.selection.minimum_format_score for score in format_scores.values())
            )
            candidate = candidates[model_id]
            summaries.append(
                ModelSummary(
                    model_id=model_id,
                    model=candidate.model,
                    total_score=total_score,
                    format_scores=format_scores,
                    format_costs_usd=format_costs,
                    format_latencies_ms=format_latencies,
                    total_cost_usd=total_cost,
                    average_latency_ms=latency,
                    attempts=len(items),
                    failures=sum(1 for item in items if not item.semantic_valid),
                    capable=capable,
                )
            )

        prefer = config.selection.prefer
        if prefer == "highest_score":
            key = lambda item: (not item.capable, -item.total_score, item.total_cost_usd is None, item.total_cost_usd or 0.0, item.average_latency_ms)
        elif prefer == "lowest_latency":
            key = lambda item: (not item.capable, item.average_latency_ms, -item.total_score, item.total_cost_usd is None, item.total_cost_usd or 0.0)
        else:
            key = lambda item: (not item.capable, item.total_cost_usd is None, item.total_cost_usd or 0.0, -item.total_score, item.average_latency_ms)
        summaries.sort(key=key)
        for rank, summary in enumerate(summaries, start=1):
            summary.rank = rank
        return summaries

    @staticmethod
    def _select_operational_format(config: BenchmarkConfig, summary: ModelSummary) -> str | None:
        available = [
            name
            for name in config.selection.preferred_operational_formats
            if name in summary.format_scores
            and summary.format_scores[name] >= config.selection.minimum_format_score
        ]
        if not available:
            available = [
                name
                for name in config.formats
                if summary.format_scores.get(name, 0.0) >= config.selection.minimum_format_score
            ]
        if not available:
            return None
        preference = {name: index for index, name in enumerate(config.selection.preferred_operational_formats)}
        return min(
            available,
            key=lambda name: (
                summary.format_costs_usd.get(name) is None,
                summary.format_costs_usd.get(name) or 0.0,
                -summary.format_scores.get(name, 0.0),
                summary.format_latencies_ms.get(name, float("inf")),
                preference.get(name, len(preference)),
            ),
        )


def benchmark_fingerprint(config: BenchmarkConfig, cases: list[BenchmarkCase]) -> str:
    payload = {
        "config": config.model_dump(mode="json", by_alias=True, exclude={"metadata"}),
        "cases": [case.model_dump(mode="json", exclude={"prompt"}) for case in cases],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()
