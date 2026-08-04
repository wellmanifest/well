from __future__ import annotations

import json
from pathlib import Path

from wellm.plesk import PleskPublicationPlanner, WorkspaceResolver, load_project_registry

root = Path(__file__).resolve().parents[2]
registry = load_project_registry(root / "examples/plesk/projects.json")
resolver = WorkspaceResolver(
    mappings={"workspace:obslugabiurowa-pl": root / "examples/plesk/site/www"},
    workspace_root=root,
)
plan = PleskPublicationPlanner(registry, resolver).build("obslugabiurowa-pl")
print(json.dumps(plan.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2))
