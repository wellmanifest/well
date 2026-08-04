from __future__ import annotations

import json
import os
from pathlib import Path

from wellm.plesk import PleskPublicationExecutor, PleskPublicationPlanner, WorkspaceResolver, load_project_registry
from wellm.urirun import UrirunProcessClient

root = Path(__file__).resolve().parents[2]
registry = load_project_registry(root / "examples/plesk/projects.extended.yaml")
plan = PleskPublicationPlanner(
    registry,
    WorkspaceResolver(
        mappings={"workspace:obslugabiurowa-pl": root / "examples/plesk/site/www"},
        workspace_root=root,
    ),
).build("obslugabiurowa-pl")
client = UrirunProcessClient(
    node_url=os.environ["URIRUN_NODE_URL"],
    token=os.getenv("URIRUN_TOKEN", ""),
    contract_ref=registry.connector.contract_ref,
)
receipt = PleskPublicationExecutor(client).dry_run(plan)
print(json.dumps(receipt.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2))
