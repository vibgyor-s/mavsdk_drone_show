from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_with_log_policy.py"


def run_helper(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )


def test_bounded_mode_rotates_logs(tmp_path: Path) -> None:
    log_file = tmp_path / "bounded.log"
    payload = "x" * 64

    run_helper(
        tmp_path,
        "--mode",
        "bounded",
        "--log-file",
        str(log_file),
        "--max-bytes",
        "32",
        "--backup-count",
        "1",
        "--",
        "bash",
        "-lc",
        f"printf '%s' '{payload}'",
    )

    assert log_file.exists()
    assert log_file.stat().st_size <= 32
    rotated = log_file.with_name("bounded.log.1")
    assert rotated.exists()


def test_discard_mode_keeps_no_log_file(tmp_path: Path) -> None:
    log_file = tmp_path / "discard.log"

    run_helper(
        tmp_path,
        "--mode",
        "discard",
        "--log-file",
        str(log_file),
        "--",
        "bash",
        "-lc",
        "printf 'discarded output'",
    )

    assert not log_file.exists()
