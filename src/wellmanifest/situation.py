from __future__ import annotations

from typing import Any

from .expressions import ExpressionError, evaluate_expression


class SituationProfileError(ValueError):
    pass


def evaluate_situation_profile(profile: dict[str, Any], snapshots: dict[str, Any]) -> dict[str, Any]:
    if profile.get("schema") != "subactor.doql-situation-profile/v1":
        raise SituationProfileError("Unsupported situation profile schema")

    source_values: dict[str, list[dict[str, Any]]] = {}
    total_objects = 0
    max_total = int(profile.get("policy", {}).get("max_total_objects", 1000))
    for source in profile.get("sources", []):
        source_id = source["id"]
        path = source.get("snapshot_path", source_id)
        value = snapshots.get(path)
        if value is None:
            if source.get("required", False):
                raise SituationProfileError(f"Missing required snapshot: {path}")
            value = []
        if not isinstance(value, list):
            raise SituationProfileError(f"Snapshot {path} must be a list")
        per_source_max = int(source.get("max_objects", max_total))
        source_values[source_id] = value[:per_source_max]
        total_objects += len(source_values[source_id])
    if total_objects > max_total:
        raise SituationProfileError("Situation profile object budget exceeded")

    metrics: dict[str, Any] = {}
    for metric in profile.get("metrics", []):
        operation = metric.get("operation")
        metric_id = metric["id"]
        if operation == "count":
            metrics[metric_id] = len(source_values.get(metric["source"], []))
        elif operation == "count_where":
            items = source_values.get(metric["source"], [])
            count = 0
            for item in items:
                try:
                    if bool(evaluate_expression(metric["where"], {"item": item, "metrics": metrics})):
                        count += 1
                except ExpressionError as exc:
                    raise SituationProfileError(f"Metric {metric_id}: {exc}") from exc
            metrics[metric_id] = count
        elif operation == "ratio":
            numerator = float(metrics.get(metric["numerator"], 0))
            denominator = float(metrics.get(metric["denominator"], 0))
            precision = int(metric.get("precision", 4))
            metrics[metric_id] = round(numerator / denominator, precision) if denominator else 0.0
        else:
            raise SituationProfileError(f"Unsupported metric operation: {operation}")

    assessments: dict[str, Any] = {}
    for assessment in profile.get("assessments", []):
        candidates = sorted(assessment.get("rules", []), key=lambda item: int(item.get("priority", 0)), reverse=True)
        selected: Any = None
        for rule in candidates:
            try:
                if bool(evaluate_expression(rule["when"], {"metrics": metrics, "situation": {"assessments": assessments}})):
                    selected = rule.get("value")
                    break
            except ExpressionError as exc:
                raise SituationProfileError(f"Assessment {assessment['id']}: {exc}") from exc
        assessments[assessment["id"]] = selected

    candidates: list[dict[str, Any]] = []
    max_candidates = int(profile.get("policy", {}).get("max_decision_candidates", 50))
    situation = {"metrics": metrics, "assessments": assessments}
    for candidate in profile.get("decision_candidates", []):
        try:
            if bool(evaluate_expression(candidate["when"], {"metrics": metrics, "situation": situation})):
                candidates.append(candidate)
        except ExpressionError as exc:
            raise SituationProfileError(f"Decision {candidate['id']}: {exc}") from exc
        if len(candidates) >= max_candidates:
            break

    result: dict[str, Any] = {
        "schema": "wellmanifest.situation-result/v1",
        "profile": {"id": profile.get("id"), "version": profile.get("version")},
        "metrics": metrics,
        "assessments": assessments,
        "decision_candidates": candidates,
        "policy": profile.get("policy", {}),
        "provenance": profile.get("provenance", {}),
    }
    if profile.get("policy", {}).get("include_raw_objects", False):
        result["objects"] = source_values
    return result
