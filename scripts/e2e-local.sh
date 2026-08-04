#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PORT=${WELLMANIFEST_E2E_PORT:-18080}
EVENTS=$(mktemp "${TMPDIR:-/tmp}/wellmanifest-events.XXXXXX")
LOG=$(mktemp "${TMPDIR:-/tmp}/wellmanifest-server.XXXXXX")
export PYTHONPATH="$ROOT/src"
export WELLMANIFEST_EVENT_STORE="$EVENTS"
export WELLMANIFEST_URL="http://127.0.0.1:$PORT"
python -m wellmanifest.cli serve --host 127.0.0.1 --port "$PORT" >"$LOG" 2>&1 &
PID=$!
cleanup() {
  kill "$PID" 2>/dev/null || true
  wait "$PID" 2>/dev/null || true
  rm -f "$EVENTS" "$LOG"
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
WELLMANIFEST_URL="$WELLMANIFEST_URL" python "$ROOT/examples/firmware/rpi_client.py"
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
print('http/events e2e: PASS')
PY
printf '%s\n' 'local multi-client e2e: PASS'
