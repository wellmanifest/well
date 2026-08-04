#!/usr/bin/env sh
set -eu
RUNTIME=${WELLMANIFEST_URL:-http://localhost:8080}

curl -fsS "$RUNTIME/v1/convert" \
  -H 'content-type: application/json' \
  -d '{
    "source":"status:\n  operation: 002-cv-pdf2md\n  value: SUCCEEDED\n  errors: []\n",
    "source_dialect":"yaml",
    "target_dialect":"json",
    "projection":"data"
  }'
