#!/usr/bin/env python3
"""
Compatibility wrapper for legacy tooling.

The active Docker SITL launch path now applies PX4 parameter overrides via
`PX4_PARAM_*` environment variables in `startup_sitl.sh`. This wrapper remains
only for older workflows that still call the rcS mutation helper directly.
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
