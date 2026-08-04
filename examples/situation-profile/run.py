from __future__ import annotations

import json
from pathlib import Path

from wellmanifest.situation import evaluate_situation_profile

root = Path(__file__).parent
profile = json.loads((root / "public-site.capability-inventory.json").read_text())
snapshots = json.loads((root / "inventory.json").read_text())
print(json.dumps(evaluate_situation_profile(profile, snapshots), indent=2, ensure_ascii=False))
