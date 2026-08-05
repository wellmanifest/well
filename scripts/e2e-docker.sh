#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHONPATH=src python3 scripts/docker_network_preflight.py --scope e2e --repair
cleanup() {
  docker compose --env-file .env -f compose.e2e.yml down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM
status=0
docker compose --env-file .env -f compose.e2e.yml up -d --build || status=$?
if [ "$status" -eq 0 ]; then
  docker compose --env-file .env -f compose.e2e.yml wait e2e || status=$?
fi
docker compose --env-file .env -f compose.e2e.yml logs --no-color
exit "$status"
