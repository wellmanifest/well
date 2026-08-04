from __future__ import annotations

from wellmanifest.runtime import WellManifestRuntime

runtime = WellManifestRuntime()
response = runtime.execute_uri(
    {
        "uri": "llm://planner/manifest/query/propose",
        "payload": {
            "goal": "Zweryfikuj profil sytuacji, wybierz digital twin i przygotuj bezpieczny plan URI Process.",
            "environment": "digital-twin",
        },
        "contract_ref": "contract:dev",
        "run_id": "llm:proposal:001",
    }
)
print(response.model_dump_json(indent=2))
