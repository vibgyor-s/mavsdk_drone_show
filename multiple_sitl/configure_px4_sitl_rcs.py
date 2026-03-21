#!/usr/bin/env python3
"""
Manage the legacy MDS SITL PX4 rcS override block.

The active Docker SITL launch path now prefers PX4's native `PX4_PARAM_*`
environment-variable overrides. This helper is kept for compatibility with
older tooling that still patches the generated `build/.../rcS` file directly.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


DEFAULT_HWID_DIR = Path("~/mavsdk_drone_show").expanduser()
DEFAULT_RCS_PATH = Path(
    "~/PX4-Autopilot/build/px4_sitl_default/etc/init.d-posix/rcS"
).expanduser()
BEGIN_MARKER = "# BEGIN MDS SITL OVERRIDES\n"
END_MARKER = "# END MDS SITL OVERRIDES\n"
MAV_SYS_ID_PATTERN = "param set MAV_SYS_ID $((px4_instance+1))"
PARAM_NAME_PATTERN = re.compile(r"^[A-Z0-9_]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hwid", type=int, default=None)
    parser.add_argument("--hwid-dir", type=Path, default=DEFAULT_HWID_DIR)
    parser.add_argument("--rcs", type=Path, default=DEFAULT_RCS_PATH)
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="PX4 parameter override in NAME=VALUE form",
    )
    return parser.parse_args()


def discover_hwid(hwid_dir: Path) -> int:
    try:
        hwid_file = next(path for path in sorted(hwid_dir.iterdir()) if path.suffix == ".hwID")
    except (FileNotFoundError, StopIteration) as exc:
        raise FileNotFoundError(f".hwID file not found in {hwid_dir}") from exc

    try:
        return int(hwid_file.stem)
    except ValueError as exc:
        raise ValueError(f"Invalid hw_id file name: {hwid_file.name}") from exc


def parse_param_assignment(assignment: str) -> Tuple[str, str]:
    if "=" not in assignment:
        raise ValueError(f"Invalid parameter override '{assignment}': expected NAME=VALUE")

    name, value = assignment.split("=", 1)
    name = name.strip()
    value = value.strip()

    if not PARAM_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid PX4 parameter name '{name}'")
    if value == "":
        raise ValueError(f"Invalid PX4 parameter override '{assignment}': missing value")

    return name, value


def normalize_param_assignments(assignments: Sequence[str]) -> List[Tuple[str, str]]:
    return [parse_param_assignment(assignment) for assignment in assignments]


def strip_managed_block(lines: Sequence[str]) -> List[str]:
    cleaned: List[str] = []
    in_block = False

    for line in lines:
        if line == BEGIN_MARKER:
            in_block = True
            continue
        if line == END_MARKER:
            in_block = False
            continue
        if not in_block:
            cleaned.append(line)

    return cleaned


def find_insert_index(lines: Sequence[str], rcs_path: Path) -> int:
    for index, line in enumerate(lines):
        if MAV_SYS_ID_PATTERN in line:
            return index + 1

    for index in range(len(lines) - 1, -1, -1):
        if "MAV_SYS_ID" in lines[index]:
            return index + 1

    raise ValueError(f"Could not find a MAV_SYS_ID anchor line in {rcs_path}")


def build_override_block(hwid: int, params: Iterable[Tuple[str, str]]) -> List[str]:
    block = [BEGIN_MARKER, f"param set MAV_SYS_ID {hwid}\n"]
    block.extend(f"param set {name} {value}\n" for name, value in params)
    block.append(END_MARKER)
    return block


def configure_rcs(
    rcs_path: Path,
    hwid: int,
    params: Sequence[Tuple[str, str]],
) -> bool:
    lines = rcs_path.read_text(encoding="utf-8").splitlines(keepends=True)
    cleaned_lines = strip_managed_block(lines)
    insert_index = find_insert_index(cleaned_lines, rcs_path)
    new_lines = (
        cleaned_lines[:insert_index]
        + build_override_block(hwid, params)
        + cleaned_lines[insert_index:]
    )

    if new_lines == lines:
        return False

    rcs_path.write_text("".join(new_lines), encoding="utf-8")
    return True


def format_param_summary(params: Sequence[Tuple[str, str]]) -> str:
    if not params:
        return "none"
    return ", ".join(f"{name}={value}" for name, value in params)


def main() -> int:
    args = parse_args()
    hwid = args.hwid if args.hwid is not None else discover_hwid(args.hwid_dir)
    params = normalize_param_assignments(args.param)

    if hwid <= 0:
        raise ValueError(f"hw_id must be a positive integer, got {hwid}")
    if not args.rcs.exists():
        raise FileNotFoundError(f"PX4 rcS file not found: {args.rcs}")

    changed = configure_rcs(args.rcs, hwid, params)
    action = "Updated" if changed else "Verified"
    print(f"{action} PX4 SITL rcS: {args.rcs}")
    print(f"Applied hw_id/MAV_SYS_ID: {hwid}")
    print(f"Applied SITL parameter overrides: {format_param_summary(params)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
