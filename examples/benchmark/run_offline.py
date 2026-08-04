from __future__ import annotations

import json
from pathlib import Path

import yaml

from wellm.llmbench import BenchmarkConfig, BenchmarkRunner, MockAdapter, build_cases, write_report

root = Path(__file__).resolve().parents[2]
config = BenchmarkConfig.model_validate(yaml.safe_load((root / "examples/benchmark/config.yaml").read_text()))
fixture = json.loads((root / "examples/plesk/projects.json").read_text())
behaviors = config.metadata["mock_behaviors"]
report = BenchmarkRunner(MockAdapter(behaviors)).run(config, build_cases(fixture, list(config.formats)))
json_path, markdown_path = write_report(report, root / ".wellm/benchmark")
print(f"selected={report.selected_model} json={json_path} markdown={markdown_path}")
