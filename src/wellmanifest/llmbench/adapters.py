from __future__ import annotations

import os
import time
from typing import Any, Protocol

from .models import CompletionMetrics, ModelCandidate


class CompletionAdapter(Protocol):
    def complete(
        self,
        candidate: ModelCandidate,
        messages: list[dict[str, str]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> CompletionMetrics: ...


class LiteLLMAdapter:
    """Thin, lazy adapter around LiteLLM.

    The optional dependency is imported only when a live benchmark is run.
    API keys are read from the configured environment variable and are never
    copied into benchmark reports.
    """

    def complete(
        self,
        candidate: ModelCandidate,
        messages: list[dict[str, str]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> CompletionMetrics:
        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError("LiteLLM is not installed; install wellm[benchmark]") from exc

        kwargs: dict[str, Any] = {
            "model": candidate.model,
            "messages": messages,
            "temperature": candidate.temperature,
            "max_tokens": candidate.max_tokens,
            "timeout": candidate.timeout_seconds,
        }
        if candidate.api_base:
            kwargs["api_base"] = candidate.api_base
        if candidate.api_key_env:
            api_key = os.getenv(candidate.api_key_env)
            if not api_key:
                raise RuntimeError(f"Missing API key environment variable: {candidate.api_key_env}")
            kwargs["api_key"] = api_key

        started = time.perf_counter()
        response = litellm.completion(**kwargs)
        latency_ms = (time.perf_counter() - started) * 1000
        text = self._response_text(response)
        usage = getattr(response, "usage", None)
        prompt_tokens = self._usage_value(usage, "prompt_tokens")
        completion_tokens = self._usage_value(usage, "completion_tokens")

        cost: float | None = None
        hidden = getattr(response, "_hidden_params", None)
        if isinstance(hidden, dict) and hidden.get("response_cost") is not None:
            try:
                cost = float(hidden["response_cost"])
            except (TypeError, ValueError):
                cost = None
        if cost is None:
            try:
                cost = float(litellm.completion_cost(completion_response=response))
            except Exception:
                # Some self-hosted or newly registered models do not have pricing.
                cost = None

        hidden_metadata = hidden if isinstance(hidden, dict) else {}
        response_model = getattr(response, "model", None)
        provider_metadata = {
            "requested_model": candidate.model,
            "response_model": str(response_model or candidate.model),
        }
        for key in ("custom_llm_provider", "model_id", "region_name"):
            value = hidden_metadata.get(key)
            if value is not None:
                provider_metadata[key] = value
        return CompletionMetrics(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            provider_metadata=provider_metadata,
        )

    @staticmethod
    def _response_text(response: Any) -> str:
        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError):
            if isinstance(response, dict):
                content = response.get("choices", [{}])[0].get("message", {}).get("content")
            else:
                content = None
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            content = "".join(parts)
        if not isinstance(content, str):
            raise RuntimeError("LiteLLM completion did not contain textual output")
        return content

    @staticmethod
    def _usage_value(usage: Any, key: str) -> int:
        if isinstance(usage, dict):
            value = usage.get(key, 0)
        else:
            value = getattr(usage, key, 0) if usage is not None else 0
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


class MockAdapter:
    """Deterministic offline adapter used by tests and Docker E2E.

    Behavior is configured per model id.  It never contacts a network service.
    """

    def __init__(self, behaviors: dict[str, dict[str, Any]] | None = None) -> None:
        self.behaviors = behaviors or {}

    def complete(
        self,
        candidate: ModelCandidate,
        messages: list[dict[str, str]],
        *,
        metadata: dict[str, Any] | None = None,
    ) -> CompletionMetrics:
        metadata = metadata or {}
        behavior = self.behaviors.get(candidate.id, {})
        target_format = str(metadata.get("target_format", "json"))
        fail_formats = set(behavior.get("fail_formats", []))
        semantic_failures = set(behavior.get("semantic_failures", []))
        case_id = str(metadata.get("case_id", ""))

        if target_format in fail_formats:
            text = "not valid output"
        elif case_id in semantic_failures:
            text = str(metadata.get("wrong_output") or "{}")
        else:
            text = str(metadata.get("expected_output") or "{}")

        prompt_size = sum(len(message.get("content", "")) for message in messages)
        prompt_tokens = max(1, prompt_size // 4)
        completion_tokens = max(1, len(text) // 4)
        cost = float(behavior.get("cost_per_call", 0.00001))
        latency = float(behavior.get("latency_ms", 5.0))
        return CompletionMetrics(
            text=text,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency,
            provider_metadata={"mock": True},
        )
