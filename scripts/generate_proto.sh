#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
OUT="$ROOT/src/wellmanifest/generated"
mkdir -p "$OUT/wellmanifest/v1"
: > "$OUT/__init__.py"
: > "$OUT/wellmanifest/__init__.py"
: > "$OUT/wellmanifest/v1/__init__.py"
python -m grpc_tools.protoc \
  -I"$ROOT/proto" \
  --python_out="$OUT" \
  --grpc_python_out="$OUT" \
  "$ROOT/proto/wellmanifest/v1/wellmanifest.proto"
# grpc_tools preserves the proto directory hierarchy. Re-export the generated
# modules under stable package names used by the reference server.
cp "$OUT/wellmanifest/v1/wellmanifest_pb2.py" \
   "$OUT/wellmanifest_pb2.py"
sed 's/from wellmanifest.v1 import wellmanifest_pb2/from wellmanifest.generated import wellmanifest_pb2/' \
  "$OUT/wellmanifest/v1/wellmanifest_pb2_grpc.py" \
  > "$OUT/wellmanifest_pb2_grpc.py"
