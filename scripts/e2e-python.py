from __future__ import annotations

import json
import os

from wellmanifest.client import WellManifestClient

base_url = os.getenv("WELLMANIFEST_URL", "http://runtime:8080")
client = WellManifestClient(base_url, timeout=10)

capabilities = client.capabilities()
assert capabilities["protocol"] == "wellmanifest.protocol/v1"

converted = client.convert(
    "status:\n  operation: 002-cv-pdf2md\n  value: SUCCEEDED\n  errors: []\n",
    source_dialect="yaml",
    target_dialect="json",
)
assert json.loads(converted["output"])["status"]["value"] == "SUCCEEDED"

executed = client.execute(
    "youtube://channel/video/query/list",
    {"channel": "ours"},
    contract_ref="contract:dev",
    run_id="docker-python:youtube:1",
)
assert executed["ok"] is True
print("python e2e: PASS")
