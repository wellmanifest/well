from __future__ import annotations

import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_todo2code_bridge_extracts_the_explicit_evidence_directory(tmp_path: Path) -> None:
    fake = tmp_path / "t2c"
    args_file = tmp_path / "args.txt"
    fake.write_text(
        """#!/bin/sh
set -eu
printf '%s\\n' \"$@\" > \"$FAKE_ARGS_FILE\"
while [ \"$#\" -gt 0 ]; do
  if [ \"$1\" = \"--out\" ]; then
    shift
    mkdir -p \"$(dirname \"$1\")\"
    printf '%s\\n' '{\"schema\":\"t2c.intent/v1\"}' > \"$1\"
    exit 0
  fi
  shift
done
exit 3
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    out = tmp_path / "out"
    env = {
        **os.environ,
        "TODO2CODE_BIN": str(fake),
        "TODO2CODE_OUTPUT_DIR": str(out),
        "FAKE_ARGS_FILE": str(args_file),
        "PYTHONPATH": str(ROOT / "src"),
    }
    result = subprocess.run(
        [str(ROOT / "scripts" / "todo2code-intent.sh")],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    args = args_file.read_text(encoding="utf-8").splitlines()
    assert args[:3] == ["extract", "config", str(out / "input")]
    assert args[3:] == ["--out", str(out / "configuration.intent.jsonl")]
    assert (out / "input" / "wellm-format-evidence.json").is_file()
    assert (out / "wellm-format-analysis.json").is_file()
    assert (out / "configuration.intent.jsonl").is_file()
