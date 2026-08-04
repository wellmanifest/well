#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
docker compose -f compose.e2e.yml up --build --abort-on-container-exit --exit-code-from e2e
docker compose -f compose.e2e.yml down -v --remove-orphans
