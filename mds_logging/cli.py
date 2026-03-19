"""
Shared CLI argument parser for unified logging flags.

Call add_log_arguments(parser) in any script's argparse setup.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import argparse
import os


def add_log_arguments(parser: argparse.ArgumentParser) -> None:
    """Add --verbose, --debug, --quiet, --log-dir, --log-json to an argparse parser."""
    log_group = parser.add_argument_group("logging")
    log_group.add_argument(
        "--verbose", "--debug",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG) console logging.",
    )
    log_group.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Quiet mode — only show WARNING and above.",
    )
    log_group.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Override log directory (default: logs/sessions).",
    )
    log_group.add_argument(
        "--log-json",
        action="store_true",
        default=False,
        help="Output JSON to console instead of colored text.",
    )


def apply_log_args(args: argparse.Namespace) -> None:
    """Apply parsed CLI args to environment (before init_logging)."""
    if args.verbose:
        os.environ["MDS_LOG_LEVEL"] = "DEBUG"
    elif args.quiet:
        os.environ["MDS_LOG_LEVEL"] = "WARNING"
    if args.log_dir:
        os.environ["MDS_LOG_DIR"] = args.log_dir
    if args.log_json:
        os.environ["MDS_LOG_CONSOLE_FORMAT"] = "json"
