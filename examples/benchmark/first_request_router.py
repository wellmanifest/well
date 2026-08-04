from __future__ import annotations

import json
from pathlib import Path

import yaml

from wellm.llmbench import BenchmarkConfig, FirstRequestModelSelector, MockAdapter, build_cases

root = Path(__file__).resolve().parents[2]
config = BenchmarkConfig.model_validate(yaml.safe_load((root / "examples/benchmark/config.yaml").read_text()))
fixture = json.loads((root / "examples/plesk/projects.json").read_text())
cases = build_cases(fixture, list(config.formats))
selector = FirstRequestModelSelector(
    MockAdapter(config.metadata["mock_behaviors"]),
    cache_path=root / ".wellm/benchmark/selection-cache.json",
)
model, selected_format, report = selector.select_route(config, cases)
print(
    json.dumps(
        {
            "selected": model.model,
            "selected_format": selected_format,
            "benchmark_ran": report is not None,
        },
        indent=2,
    )
)
