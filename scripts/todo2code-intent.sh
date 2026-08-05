#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
T2C_BIN=${TODO2CODE_BIN:-t2c}
OUT=${TODO2CODE_OUTPUT_DIR:-$ROOT/.intent/wellm-formats}
PROJECT=${1:-$ROOT/examples/todo2code/intent-formats.wellm.yaml}
PYTHON=${PYTHON:-python3}

case "$OUT" in
  /*) ;;
  *) OUT=$ROOT/$OUT ;;
esac
case "$PROJECT" in
  /*) ;;
  *) PROJECT=$ROOT/$PROJECT ;;
esac

mkdir -p "$OUT/input"
PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m wellmanifest intent analyze "$PROJECT" \
  -o "$OUT/wellm-format-analysis.json" \
  --todo2code-evidence "$OUT/input/wellm-format-evidence.config.json"
if ! command -v "$T2C_BIN" >/dev/null 2>&1; then
  printf '%s\n' "ERROR WM-T2C-001: todo2code command '$T2C_BIN' is unavailable." >&2
  printf '%s\n' "Wellm evidence is ready at $OUT/input/wellm-format-evidence.config.json" >&2
  exit 2
fi
INTENT_OUTPUT=$OUT/configuration.intent.jsonl
rm -f "$INTENT_OUTPUT"
"$T2C_BIN" extract config "$OUT/input" --out "$INTENT_OUTPUT"
if [ ! -s "$INTENT_OUTPUT" ]; then
  printf '%s\n' "ERROR WM-T2C-002: todo2code produced no intent records: $INTENT_OUTPUT" >&2
  exit 3
fi
printf '%s\n' "Wellm format evidence: $OUT/input/wellm-format-evidence.config.json"
printf '%s\n' "todo2code configuration records: $INTENT_OUTPUT"
