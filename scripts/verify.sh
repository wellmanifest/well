#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
export PYTHONPATH=src

python scripts/env_contract.py check >/tmp/wellm-env-check.json
python -m wellmanifest versions --check >/tmp/wellm-version-check.json
python -m compileall -q src tests examples
python -m pytest -q
(cd packages/js && npm test && npm run check)
python -m wellmanifest governance build examples/governance/wellm.project.yaml --check >/tmp/wellm-governance-check.json

TMP=$(mktemp -d "${TMPDIR:-/tmp}/wellm-verify.XXXXXX")
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT INT TERM
python -m wellmanifest intent analyze examples/todo2code/intent-formats.wellm.yaml \
  -o "$TMP/intent-report.json" --todo2code-evidence "$TMP/todo2code-evidence.json" >/tmp/wellm-intent-diagnostics.txt
python - <<'PY' "$TMP/intent-report.json" "$TMP/todo2code-evidence.json"
import json, sys
report=json.load(open(sys.argv[1], encoding='utf-8'))
evidence=json.load(open(sys.argv[2], encoding='utf-8'))
assert report['equivalent'] is True
assert len(report['representations']) == 6
assert evidence['schema'] == 'wellm.todo2code-format-evidence/v1'
print('multi-format intent evidence: PASS')
PY
python -m wellmanifest schema import schemas/status.schema.json -o "$TMP/status.schema.wm"
python -m wellmanifest schema export "$TMP/status.schema.wm" -o "$TMP/status.schema.json"
python - <<'PY' schemas/status.schema.json "$TMP/status.schema.json"
import json, sys
assert json.load(open(sys.argv[1], encoding='utf-8')) == json.load(open(sys.argv[2], encoding='utf-8'))
print('JSON Schema <-> typed module: PASS')
PY
python -m wellmanifest convert examples/toon/map.toon.yaml --from toon --to json -o "$TMP/map.json"
python - <<'PY' "$TMP/map.json"
import json, sys
value=json.load(open(sys.argv[1], encoding='utf-8'))
assert value['moduleCount'] == len(value['modules']) == 235
assert len(value['details']) == 235
print('code2llm TOON import: PASS')
PY
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
        if any(part in excluded for part in path.parts) or path.name.endswith('.toon.yaml'):
            continue
        list(yaml.safe_load_all(path.read_text(encoding='utf-8')))
print('JSON/YAML fixtures: PASS')
PY
for file in scripts/*.sh examples/**/*.sh; do
  [ -f "$file" ] && sh -n "$file"
done
printf '%s\n' 'verification: PASS'
