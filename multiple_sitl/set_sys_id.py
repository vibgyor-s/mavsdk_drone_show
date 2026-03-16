#!/usr/bin/env python3
"""
Compatibility wrapper for legacy tooling.

The active implementation lives in `configure_px4_sitl_rcs.py`, which manages
MAV_SYS_ID plus any other SITL-only PX4 parameter overrides in one idempotent
block inside the generated rcS file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    helper = Path(__file__).with_name("configure_px4_sitl_rcs.py")
    result = subprocess.run([sys.executable, str(helper)], check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
