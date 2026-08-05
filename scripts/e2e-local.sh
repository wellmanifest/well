#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PORT=${WELLMANIFEST_E2E_PORT:-18080}
EVENTS=$(mktemp "${TMPDIR:-/tmp}/wellmanifest-events.XXXXXX")
LOG=$(mktemp "${TMPDIR:-/tmp}/wellmanifest-server.XXXXXX")
EXTRA=$(mktemp -d "${TMPDIR:-/tmp}/wellm-e2e.XXXXXX")
export PYTHONPATH="$ROOT/src"
export WELLMANIFEST_EVENT_STORE="$EVENTS"
export WELLMANIFEST_URL="http://127.0.0.1:$PORT"
python -m wellmanifest.cli serve --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
PID=$!
cleanup() {
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  rm -f "$EVENTS" "$LOG"
  rm -rf "$EXTRA"
}
trap cleanup EXIT INT TERM

count=0
until python -c "import urllib.request; urllib.request.urlopen('$WELLMANIFEST_URL/healthz', timeout=1)" >/dev/null 2>&1; do
  count=$((count+1))
  if [ "$count" -ge 50 ]; then
    cat "$LOG" >&2
    exit 1
  fi
  sleep 0.2
done

python "$ROOT/scripts/e2e-python.py"
(
  cd "$ROOT"
  node scripts/e2e-node.mjs
)
PYTHONPATH="$ROOT/src" python "$ROOT/scripts/e2e-plesk-plan-parity.py"
WELLMANIFEST_URL="$WELLMANIFEST_URL" python "$ROOT/examples/firmware/rpi_client.py"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli plesk-plan "$ROOT/examples/plesk/projects.json" \
  --project obslugabiurowa-pl \
  --source-ref "workspace:obslugabiurowa-pl=$ROOT/examples/plesk/site/www" \
  --workspace-root "$ROOT" --to json --output "$EXTRA/plan.json"
test -s "$EXTRA/plan.json"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli benchmark-llm "$ROOT/examples/benchmark/config.yaml" \
  --mock --output-dir "$EXTRA/benchmark" >/dev/null
test -s "$EXTRA/benchmark/benchmark-report.json"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli governance build "$ROOT/examples/governance/wellm.project.yaml" --check >"$EXTRA/governance-check.json"
test -s "$EXTRA/governance-check.json"
PYTHONPATH="$ROOT/src" python "$ROOT/scripts/env_contract.py" check >"$EXTRA/env-check.json"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli versions --check >"$EXTRA/versions.json"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli intent analyze "$ROOT/examples/todo2code/intent-formats.wellm.yaml" \
  -o "$EXTRA/intent-report.json" --todo2code-evidence "$EXTRA/todo2code-evidence.json"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli schema import "$ROOT/schemas/status.schema.json" -o "$EXTRA/status.schema.wm"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli schema export "$EXTRA/status.schema.wm" -o "$EXTRA/status.schema.json"
PYTHONPATH="$ROOT/src" python -m wellmanifest.cli convert "$ROOT/examples/toon/map.toon.yaml" --from toon --to json -o "$EXTRA/map.json"
python - "$EXTRA/intent-report.json" "$EXTRA/status.schema.json" "$EXTRA/map.json" "$ROOT/schemas/status.schema.json" <<'PY2'
import json, sys
report=json.load(open(sys.argv[1], encoding='utf-8'))
roundtrip=json.load(open(sys.argv[2], encoding='utf-8'))
toon=json.load(open(sys.argv[3], encoding='utf-8'))
original=json.load(open(sys.argv[4], encoding='utf-8'))
assert report['equivalent'] is True
assert roundtrip == original
assert toon['moduleCount'] == 235
print('versions/env/types/intent/TOON local e2e: PASS')
PY2
printf '%s\n' 'plesk/benchmark/governance local e2e: PASS'
python - <<'PY'
import json, os, urllib.request
base=os.environ['WELLMANIFEST_URL']
body=json.dumps({
  'source':'status:\n  value: SUCCEEDED\n  errors: []\n',
  'source_dialect':'yaml','target_dialect':'json','projection':'data'
}).encode()
req=urllib.request.Request(base+'/v1/convert',data=body,headers={'content-type':'application/json'})
with urllib.request.urlopen(req,timeout=5) as r:
  data=json.load(r)
assert json.loads(data['output'])['status']['value']=='SUCCEEDED'
with urllib.request.urlopen(base+'/v1/events?limit=20',timeout=5) as r:
  events=json.load(r)['events']
assert any(e['type']=='ProcessCompleted' for e in events)
with urllib.request.urlopen(base+'/v1/versions',timeout=5) as r:
  versions=json.load(r)
assert versions['package']['version'] == '0.2.0rc4'
with urllib.request.urlopen(base+'/v1/env-contract',timeout=5) as r:
  env_contract=json.load(r)
assert env_contract['schema'] == 'wellm.env-contract/v1'
print('http/events/version/env e2e: PASS')
PY
printf '%s\n' 'local multi-client e2e: PASS'
