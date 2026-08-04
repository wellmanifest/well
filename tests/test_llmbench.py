from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

from wellmanifest.llmbench import (
    BenchmarkConfig,
    BenchmarkRunner,
    FirstRequestModelSelector,
    LiteLLMAdapter,
    MockAdapter,
    build_cases,
)
from wellmanifest.runtime import WellManifestRuntime


def fixture() -> dict:
    return json.loads(Path("examples/plesk/projects.json").read_text(encoding="utf-8"))


def config() -> BenchmarkConfig:
    return BenchmarkConfig.model_validate(
        {
            "schema": "wellmanifest.llm-benchmark/v1",
            "id": "test",
            "formats": ["json", "yaml", "typed", "typescript"],
            "models": [
                {"id": "weak", "model": "mock/weak"},
                {"id": "efficient", "model": "mock/efficient"},
                {"id": "premium", "model": "mock/premium"},
            ],
            "selection": {
                "minimum_total_score": 0.9,
                "minimum_format_score": 0.75,
                "prefer": "lowest_cost",
            },
        }
    )


def behaviors() -> dict:
    return {
        "weak": {"fail_formats": ["typed", "typescript"], "cost_per_call": 0.000001},
        "efficient": {"fail_formats": [], "cost_per_call": 0.000004},
        "premium": {"fail_formats": [], "cost_per_call": 0.00002},
    }


def test_generated_expected_outputs_roundtrip_for_every_format() -> None:
    runtime = WellManifestRuntime()
    cases = build_cases(fixture(), ["json", "yaml", "typed", "typescript"], runtime=runtime)
    assert len(cases) == 12
    for case in cases:
        assert case.output_schema["type"] == "object"


def test_benchmark_selects_cheapest_model_that_passes_every_format() -> None:
    cfg = config()
    cases = build_cases(fixture(), list(cfg.formats))
    report = BenchmarkRunner(MockAdapter(behaviors())).run(cfg, cases)
    assert report.selected_model_id == "efficient"
    assert report.selected_format == "typed"
    weak = next(item for item in report.summaries if item.model_id == "weak")
    efficient = next(item for item in report.summaries if item.model_id == "efficient")
    assert weak.capable is False
    assert efficient.capable is True
    assert all(attempt.semantic_valid for attempt in report.attempts if attempt.model_id == "efficient")


def test_first_request_selector_uses_fingerprint_cache(tmp_path: Path) -> None:
    cfg = config()
    cases = build_cases(fixture(), list(cfg.formats))
    selector = FirstRequestModelSelector(MockAdapter(behaviors()), cache_path=tmp_path / "selection.json")
    selected, selected_format, report = selector.select_route(cfg, cases)
    assert selected.id == "efficient"
    assert selected_format == "typed"
    assert report is not None
    selected_again, selected_format_again, report_again = selector.select_route(cfg, cases)
    assert selected_again.id == "efficient"
    assert selected_format_again == "typed"
    assert report_again is None


def test_report_contains_cost_and_latency_per_format() -> None:
    cfg = config()
    cases = build_cases(fixture(), list(cfg.formats))
    report = BenchmarkRunner(MockAdapter(behaviors())).run(cfg, cases)
    efficient = next(item for item in report.summaries if item.model_id == "efficient")
    assert set(efficient.format_costs_usd) == set(cfg.formats)
    assert set(efficient.format_latencies_ms) == set(cfg.formats)
    assert all(value is not None for value in efficient.format_costs_usd.values())


class CapturingAdapter:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.metadata: dict | None = None

    def complete(self, candidate, messages, *, metadata=None):
        from wellmanifest.llmbench.models import CompletionMetrics

        self.messages = messages
        self.metadata = metadata
        return CompletionMetrics(text="{}", cost_usd=0.0, latency_ms=1.0)


def test_selected_operational_format_is_added_to_the_real_request_prompt(tmp_path: Path) -> None:
    cfg = config()
    cases = build_cases(fixture(), list(cfg.formats))
    # Prime the route cache with the deterministic benchmark adapter.
    cache = tmp_path / "selection.json"
    FirstRequestModelSelector(MockAdapter(behaviors()), cache_path=cache).select_route(cfg, cases)

    adapter = CapturingAdapter()
    selector = FirstRequestModelSelector(adapter, cache_path=cache)
    candidate, selected_format, _completion, report = selector.complete_selected_route(
        cfg,
        cases,
        [{"role": "user", "content": "Prepare the next manifest."}],
    )
    assert candidate.id == "efficient"
    assert selected_format == "typed"
    assert report is None
    assert adapter.metadata == {"wellmanifest_format": "typed"}
    assert "selected operational format: typed" in adapter.messages[0]["content"]
    assert "WellManifest typed@1" in adapter.messages[0]["content"]


def test_litellm_adapter_reads_usage_reported_cost_and_model_metadata(monkeypatch) -> None:
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok":true}'))],
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=7),
        model="provider/resolved-model",
        _hidden_params={
            "response_cost": 0.00125,
            "custom_llm_provider": "test-provider",
            "model_id": "resolved-123",
        },
    )
    calls: list[dict] = []

    def completion(**kwargs):
        calls.append(kwargs)
        return response

    fake = SimpleNamespace(completion=completion, completion_cost=lambda **_kwargs: 999.0)
    monkeypatch.setitem(sys.modules, "litellm", fake)
    candidate = config().models[1]
    metrics = LiteLLMAdapter().complete(candidate, [{"role": "user", "content": "x"}])
    assert calls[0]["model"] == candidate.model
    assert metrics.text == '{"ok":true}'
    assert metrics.prompt_tokens == 12
    assert metrics.completion_tokens == 7
    assert metrics.cost_usd == 0.00125
    assert metrics.provider_metadata["response_model"] == "provider/resolved-model"
    assert metrics.provider_metadata["custom_llm_provider"] == "test-provider"
