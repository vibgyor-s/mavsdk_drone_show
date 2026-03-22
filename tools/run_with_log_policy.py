#!/usr/bin/env python3
"""
Run a subprocess while applying a simple log retention policy to its combined
stdout/stderr stream.

Modes:
  - bounded: rotate the active log file when it reaches max_bytes
  - full: keep a full per-run log file
  - discard: do not persist the child output
"""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import TextIO


PXH_PROMPT_PATTERN = re.compile(rb"(?:\x1b\[[0-9;?]*[A-Za-z])*(?:\r|\n)*pxh>\s*")


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("bounded", "full", "discard"),
        default="bounded",
        help="How to persist child output",
    )
    parser.add_argument(
        "--log-file",
        required=True,
        help="Path of the primary log file to write",
    )
    parser.add_argument(
        "--max-bytes",
        type=positive_int,
        default=5 * 1024 * 1024,
        help="Maximum size of the active log file in bounded mode",
    )
    parser.add_argument(
        "--backup-count",
        type=positive_int,
        default=1,
        help="How many rotated backups to keep in bounded mode",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to the primary log file instead of truncating it",
    )
    parser.add_argument(
        "--strip-pxh-prompts",
        action="store_true",
        help="Drop repeated PX4 shell prompt control sequences from the log stream",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to execute after '--'",
    )
    return parser


class LogWriter:
    def __init__(
        self,
        path: Path,
        mode: str,
        max_bytes: int,
        backup_count: int,
        append: bool,
    ) -> None:
        self.path = path
        self.mode = mode
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.append = append
        self.handle: TextIO | None = None

        if self.mode != "discard":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            file_mode = "ab" if self.append and self.path.exists() else "wb"
            self.handle = self.path.open(file_mode)

    def close(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None

    def _rotate(self) -> None:
        if self.handle is not None:
            self.handle.close()
            self.handle = None

        if self.backup_count > 0:
            oldest = self.path.with_name(f"{self.path.name}.{self.backup_count}")
            if oldest.exists():
                oldest.unlink()

            for index in range(self.backup_count - 1, 0, -1):
                src = self.path.with_name(f"{self.path.name}.{index}")
                dst = self.path.with_name(f"{self.path.name}.{index + 1}")
                if src.exists():
                    src.replace(dst)

            if self.path.exists():
                self.path.replace(self.path.with_name(f"{self.path.name}.1"))
        elif self.path.exists():
            self.path.unlink()

        self.handle = self.path.open("wb")

    def write(self, data: bytes) -> None:
        if not data or self.mode == "discard":
            return

        if self.handle is None:
            self.handle = self.path.open("ab")

        if self.mode == "bounded" and self.max_bytes > 0:
            current_size = self.handle.tell()
            if current_size + len(data) > self.max_bytes:
                self._rotate()
                if len(data) > self.max_bytes:
                    data = data[-self.max_bytes :]

        self.handle.write(data)
        self.handle.flush()


def run_child(args: argparse.Namespace) -> int:
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("No command provided. Use: run_with_log_policy.py ... -- <command>")

    log_writer = LogWriter(
        path=Path(args.log_file),
        mode=args.mode,
        max_bytes=args.max_bytes,
        backup_count=args.backup_count,
        append=args.append,
    )

    child: subprocess.Popen[bytes] | None = None

    def forward_signal(signum: int, _frame: object) -> None:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass

    signal.signal(signal.SIGTERM, forward_signal)
    signal.signal(signal.SIGINT, forward_signal)

    stdout = subprocess.DEVNULL if args.mode == "discard" else subprocess.PIPE
    child = subprocess.Popen(
        command,
        stdout=stdout,
        stderr=subprocess.STDOUT,
        bufsize=0,
        start_new_session=True,
    )

    try:
        if child.stdout is not None:
            while True:
                chunk = child.stdout.read(65536)
                if not chunk:
                    break
                if args.strip_pxh_prompts:
                    chunk = PXH_PROMPT_PATTERN.sub(b"", chunk)
                log_writer.write(chunk)
        return child.wait()
    finally:
        log_writer.close()
        if child.stdout is not None:
            child.stdout.close()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_child(args)


if __name__ == "__main__":
    raise SystemExit(main())
