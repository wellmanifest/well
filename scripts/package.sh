#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION=$(cat "$ROOT/VERSION")
DIST="$ROOT/dist"
NAME="wellm-project-$VERSION"
PYTHON_RESULT=${WELLMANIFEST_PYTHON_TEST_RESULT:-"not recorded by package command"}
NODE_RESULT=${WELLMANIFEST_NODE_TEST_RESULT:-"not recorded by package command"}
E2E_RESULT=${WELLMANIFEST_E2E_RESULT:-"not recorded by package command"}
DOCKER_RESULT=${WELLMANIFEST_DOCKER_RESULT:-"not run by package command"}
RUST_RESULT=${WELLMANIFEST_RUST_RESULT:-"not run by package command"}
RUFF_RESULT=${WELLMANIFEST_RUFF_RESULT:-"not run by package command"}
WHEEL_RESULT=${WELLMANIFEST_WHEEL_RESULT:-"not run by package command"}
NPM_PACKAGE_RESULT=${WELLMANIFEST_NPM_PACKAGE_RESULT:-"not run by package command"}
SOURCE_ARCHIVE_RESULT=${WELLMANIFEST_SOURCE_ARCHIVE_RESULT:-"not run by package command"}
GOVERNANCE_RESULT=${WELLMANIFEST_GOVERNANCE_RESULT:-"not recorded by package command"}
rm -rf "$DIST"
mkdir -p "$DIST/$NAME" "$DIST/python"

# Copy release sources while excluding local caches/build outputs.
tar -C "$ROOT" \
  --exclude='./dist' \
  --exclude='./.git' \
  --exclude='./.pytest_cache' \
  --exclude='./.wellm' \
  --exclude='./build' \
  --exclude='*.egg-info' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='./target' \
  --exclude='*/node_modules' \
  -cf - . | tar -C "$DIST/$NAME" -xf -

cat > "$DIST/TEST-REPORT.md" <<EOF
# wellm / WellManifest $VERSION test report

Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)

| Suite | Result |
|---|---|
| Python reference tests | $PYTHON_RESULT |
| JavaScript SDK tests | $NODE_RESULT |
| Local HTTP/Node/RPi E2E | $E2E_RESULT |
| Governance build/check | $GOVERNANCE_RESULT |
| Python wheel smoke | $WHEEL_RESULT |
| npm package smoke | $NPM_PACKAGE_RESULT |
| Source ZIP smoke | $SOURCE_ARCHIVE_RESULT |
| Ruff lint | $RUFF_RESULT |
| Docker Compose E2E | $DOCKER_RESULT |
| Rust/WASM/PyO3/N-API | $RUST_RESULT |

Verification commands:

\`./scripts/verify.sh\`
\`./scripts/e2e-local.sh\`
\`./scripts/e2e-docker.sh\`

A source scaffold or Docker recipe is not marked as executed unless the
corresponding toolchain was available in the packaging environment.
EOF
cp "$DIST/TEST-REPORT.md" "$DIST/$NAME/TEST-REPORT.md"

(cd "$DIST" && tar -czf "$NAME.tar.gz" "$NAME")
python - "$DIST" "$NAME" <<'PY'
from pathlib import Path
import sys, zipfile
out=Path(sys.argv[1]); name=sys.argv[2]
with zipfile.ZipFile(out/f'{name}.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for path in sorted((out/name).rglob('*')):
        if path.is_file():
            z.write(path,path.relative_to(out))
PY

# Build the pure-Python wheel without network/build isolation when setuptools is
# already present. The project source archives remain available if this fails.
if python -m pip wheel --no-build-isolation --no-deps "$ROOT" -w "$DIST/python" >/dev/null 2>&1; then
  cp "$DIST"/python/wellm-*.whl "$DIST/"
else
  printf '%s\n' 'WARNING: Python wheel was not built; use the source archive.' >&2
fi

# Build the dependency-free JavaScript/TypeScript SDK package when npm is
# available. npm pack does not contact the registry.
if command -v npm >/dev/null 2>&1; then
  mkdir -p "$DIST/npm"
  if (cd "$ROOT/packages/js" && npm pack --pack-destination "$DIST/npm" >/dev/null); then
    cp "$DIST"/npm/*.tgz "$DIST/"
  else
    printf '%s\n' 'WARNING: npm SDK package was not built.' >&2
  fi
fi

(
  cd "$DIST"
  files="$NAME.tar.gz $NAME.zip"
  for candidate in wellm-*.whl wellmanifest-*.tgz; do
    [ -f "$candidate" ] && files="$files $candidate"
  done
  # shellcheck disable=SC2086
  sha256sum $files > SHA256SUMS
)
printf 'Created %s\n' "$DIST/$NAME.zip"
printf 'Created %s\n' "$DIST/$NAME.tar.gz"
ls "$DIST"/wellm-*.whl 2>/dev/null || true
