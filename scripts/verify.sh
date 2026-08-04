#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHONPATH=src python -m compileall -q src tests examples
PYTHONPATH=src python -m pytest -q
(cd packages/js && npm test && npm run check)
python - <<'PY'
import json
from pathlib import Path

import yaml

excluded = {'.pytest_cache', 'dist', 'target', 'node_modules', '.venv'}
for path in Path('.').rglob('*.json'):
    if any(part in excluded for part in path.parts):
        continue
    json.loads(path.read_text(encoding='utf-8'))
for pattern in ('*.yaml', '*.yml'):
    for path in Path('.').rglob(pattern):
        if any(part in excluded for part in path.parts):
            continue
        list(yaml.safe_load_all(path.read_text(encoding='utf-8')))
print('JSON/YAML fixtures: PASS')
PY
for file in scripts/*.sh examples/**/*.sh; do
  [ -f "$file" ] && sh -n "$file"
done
printf '%s\n' 'verification: PASS'
