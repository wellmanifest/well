from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    model: str
    api_base: str | None = None
    api_key_env: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout_seconds: float = 60.0
    tags: list[str] = Field(default_factory=list)


class SelectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_total_score: float = 0.90
    minimum_format_score: float = 0.75
    prefer: Literal["lowest_cost", "highest_score", "lowest_latency"] = "lowest_cost"
    preferred_operational_formats: list[Literal["json", "yaml", "typed", "hcl", "typescript"]] = Field(
        default_factory=lambda: ["typed", "typescript", "json", "yaml", "hcl"]
    )
    cache_ttl_seconds: int = 3600


class BenchmarkConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    schema_id: Literal["wellmanifest.llm-benchmark/v1"] = Field(
        default="wellmanifest.llm-benchmark/v1",
        alias="schema",
        serialization_alias="schema",
    )
    id: str = "default-format-capability"
    models: list[ModelCandidate]
    formats: list[Literal["json", "yaml", "typed", "hcl", "typescript"]] = Field(
        default_factory=lambda: ["json", "yaml", "typed", "typescript"]
    )
    repetitions: int = 1
    selection: SelectionPolicy = Field(default_factory=SelectionPolicy)
    fixture_file: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_config(self) -> "BenchmarkConfig":
        if not self.models:
            raise ValueError("at least one model candidate is required")
        if len({item.id for item in self.models}) != len(self.models):
            raise ValueError("model candidate ids must be unique")
        if not self.formats:
            raise ValueError("at least one target format is required")
        if self.repetitions < 1 or self.repetitions > 20:
            raise ValueError("repetitions must be between 1 and 20")
        return self


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    target_format: Literal["json", "yaml", "typed", "hcl", "typescript"]
    input_data: Any
    expected_data: Any
    output_schema: dict[str, Any]
    prompt: str
    weight: float = 1.0
    category: Literal["roundtrip", "logic", "policy"] = "roundtrip"


class CompletionMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float | None = None
    latency_ms: float = 0.0
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    model: str
    case_id: str
    target_format: str
    repetition: int
    syntax_valid: bool
    schema_valid: bool
    semantic_valid: bool
    score: float
    cost_usd: float | None = None
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    output: str
    normalized: Any = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class ModelSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str
    model: str
    total_score: float
    format_scores: dict[str, float]
    format_costs_usd: dict[str, float | None] = Field(default_factory=dict)
    format_latencies_ms: dict[str, float] = Field(default_factory=dict)
    total_cost_usd: float | None
    average_latency_ms: float
    attempts: int
    failures: int
    capable: bool
    rank: int | None = None


class BenchmarkReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    schema_id: Literal["wellmanifest.llm-benchmark-report/v1"] = Field(
        default="wellmanifest.llm-benchmark-report/v1",
        alias="schema",
        serialization_alias="schema",
    )
    benchmark_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fingerprint: str
    selected_model_id: str | None = None
    selected_model: str | None = None
    selected_format: str | None = None
    summaries: list[ModelSummary]
    attempts: list[BenchmarkAttempt]
    notes: list[str] = Field(default_factory=list)
