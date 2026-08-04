from __future__ import annotations

import json
from pathlib import Path

from .models import BenchmarkReport


def write_report(report: BenchmarkReport, output_dir: str | Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark-report.json"
    markdown_path = output_dir / "benchmark-report.md"
    json_path.write_text(
        json.dumps(report.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, markdown_path


def render_markdown(report: BenchmarkReport) -> str:
    lines = [
        f"# WellManifest LLM benchmark — {report.benchmark_id}",
        "",
        f"Fingerprint: `{report.fingerprint}`",
        "",
        f"Selected model: `{report.selected_model or 'none'}`",
        f"Selected operational format: `{report.selected_format or 'none'}`",
        "",
        "| Rank | Candidate | Score | Cost USD | Avg latency ms | Capable | Format score / cost / latency |",
        "|---:|---|---:|---:|---:|:---:|---|",
    ]
    for item in report.summaries:
        costs = "unknown" if item.total_cost_usd is None else f"{item.total_cost_usd:.8f}"
        format_parts: list[str] = []
        for key, value in item.format_scores.items():
            format_cost = item.format_costs_usd.get(key)
            cost_text = "?" if format_cost is None else f"${format_cost:.8f}"
            latency = item.format_latencies_ms.get(key, 0.0)
            format_parts.append(f"{key}={value:.2f}/{cost_text}/{latency:.1f}ms")
        formats = ", ".join(format_parts)
        lines.append(
            f"| {item.rank} | `{item.model_id}` / `{item.model}` | {item.total_score:.3f} | {costs} | "
            f"{item.average_latency_ms:.1f} | {'yes' if item.capable else 'no'} | {formats} |"
        )
    lines.extend(["", "## Method", ""])
    lines.extend(f"- {note}" for note in report.notes)
    lines.extend(
        [
            "",
            "Scores: syntax 25%, JSON Schema 25%, deterministic semantic result 50%.",
            "The benchmark records provider-reported token usage and cost when available.",
        ]
    )
    return "\n".join(lines) + "\n"
