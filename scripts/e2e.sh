#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
./scripts/e2e-local.sh
if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  if [ "${WELLMANIFEST_E2E_ALLOW_LOCAL_FALLBACK:-0}" = "1" ]; then
    printf '%s\n' 'WARNING: Docker unavailable; explicit local fallback accepted.' >&2
    exit 0
  fi
  printf '%s\n' 'ERROR WM-DOCKER-001: Docker is required for make e2e. Use make e2e-local for the local-only suite.' >&2
  exit 2
fi
./scripts/e2e-docker.sh
./scripts/e2e-iot.sh
