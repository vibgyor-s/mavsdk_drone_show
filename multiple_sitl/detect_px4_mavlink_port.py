#!/usr/bin/env python3
"""
Detect the PX4 SITL UDP port that carries the GCS MAVLink stream.

The Docker image and the checked-out repo do not always agree on the PX4
runtime defaults. Modern images use remote port 14550, while older/legacy
setups may still emit the GCS stream on a different UDP port. This utility
inspects the live PX4 process sockets (and falls back to SITL log parsing)
so startup_sitl.sh can route MAVLink without hardcoding a single port.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence


PROCESS_PATTERN = re.compile(r'users:\(\("([^"]+)"')
PORT_PATTERN = re.compile(r":(\d+)$")
REMOTE_PORT_PATTERN = re.compile(r"\bremote port (?P<port>\d+)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-port", type=int, default=14550)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--sitl-log", type=Path, default=None)
    parser.add_argument(
        "--exclude-port",
        type=int,
        action="append",
        default=[],
        help="Ports that are known not to be the PX4 GCS stream",
    )
    return parser.parse_args()


def _port_from_endpoint(endpoint: str) -> int | None:
    match = PORT_PATTERN.search(endpoint)
    if not match:
        return None
    return int(match.group(1))


def _candidate_port(port: int | None, excluded_ports: Sequence[int]) -> bool:
    if port is None:
        return False
    if port in excluded_ports:
        return False
    return 14550 <= port <= 14999


def extract_ports_from_ss_output(
    output: str,
    excluded_ports: Sequence[int],
) -> List[int]:
    """
    Extract candidate PX4 remote UDP ports from `ss -uapn` output.
    """
    candidates: List[int] = []
    for line in output.splitlines():
        if "users:((" not in line:
            continue
        process_match = PROCESS_PATTERN.search(line)
        if not process_match:
            continue
        process_name = process_match.group(1)
        if process_name != "px4":
            continue

        parts = line.split()
        if len(parts) < 6:
            continue

        peer_endpoint = parts[-2]
        port = _port_from_endpoint(peer_endpoint)
        if _candidate_port(port, excluded_ports):
            candidates.append(port)

    return sorted(set(candidates))


def extract_ports_from_log(
    log_text: str,
    excluded_ports: Sequence[int],
) -> List[int]:
    """
    Extract candidate PX4 remote UDP ports from SITL log lines.
    """
    candidates = []
    for match in REMOTE_PORT_PATTERN.finditer(log_text):
        port = int(match.group("port"))
        if _candidate_port(port, excluded_ports):
            candidates.append(port)
    return sorted(set(candidates))


def choose_port(candidates: Iterable[int], default_port: int) -> int:
    candidates = sorted(set(candidates))
    if not candidates:
        return default_port
    if 14550 in candidates:
        return 14550
    return candidates[0]


def _read_sitl_log(sitl_log: Path | None) -> str:
    if not sitl_log or not sitl_log.exists():
        return ""
    try:
        return sitl_log.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def detect_from_runtime(
    default_port: int,
    timeout: float,
    poll_interval: float,
    sitl_log: Path | None,
    excluded_ports: Sequence[int],
) -> int:
    deadline = time.time() + timeout
    last_error = None

    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["ss", "-H", "-uapn"],
                capture_output=True,
                check=True,
                text=True,
            )
            ss_candidates = extract_ports_from_ss_output(result.stdout, excluded_ports)
            if ss_candidates:
                return choose_port(ss_candidates, default_port)

            log_candidates = extract_ports_from_log(_read_sitl_log(sitl_log), excluded_ports)
            if log_candidates:
                return choose_port(log_candidates, default_port)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            last_error = exc
            log_candidates = extract_ports_from_log(_read_sitl_log(sitl_log), excluded_ports)
            if log_candidates:
                return choose_port(log_candidates, default_port)

        time.sleep(poll_interval)

    if last_error:
        print(
            f"Warning: falling back to default MAVLink port {default_port} "
            f"after detection error: {last_error}",
            file=sys.stderr,
        )
    else:
        print(
            f"Warning: falling back to default MAVLink port {default_port} "
            "after detection timeout",
            file=sys.stderr,
        )
    return default_port


def main() -> int:
    args = parse_args()
    excluded_ports = [*args.exclude_port]
    port = detect_from_runtime(
        default_port=args.default_port,
        timeout=args.timeout,
        poll_interval=args.poll_interval,
        sitl_log=args.sitl_log,
        excluded_ports=excluded_ports,
    )
    print(port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
