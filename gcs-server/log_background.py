"""
Optional background task: periodically pull WARNING+ logs from drones.

Disabled by default. Enable via MDS_LOG_BACKGROUND_PULL=true or the
runtime toggle at POST /api/logs/config.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import asyncio
import json
import os

from config import load_config
from log_proxy import fetch_drone_sessions, fetch_drone_session_content
from mds_logging import get_logger
from mds_logging.constants import (
    get_background_pull_enabled, get_pull_interval_sec,
    get_pull_level, get_pull_max_drones, get_log_dir,
)

logger = get_logger("log_bg_pull")


class BackgroundLogPuller:
    """Periodically pulls WARNING+ logs from connected drones."""

    def __init__(self, log_dir: str | None = None):
        self.log_dir = log_dir or get_log_dir()
        self.enabled = get_background_pull_enabled()
        self._task: asyncio.Task | None = None

    def set_enabled(self, enabled: bool) -> None:
        """Toggle background pull at runtime."""
        self.enabled = enabled
        if enabled:
            logger.info("Background log pull enabled")
        else:
            logger.info("Background log pull disabled")

    async def start(self) -> None:
        """Start the background pull loop as an async task."""
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Background log puller started")

    async def stop(self) -> None:
        """Stop the background pull loop."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Background log puller stopped")

    async def _run_loop(self) -> None:
        """Main loop — runs until cancelled."""
        interval = get_pull_interval_sec()
        while True:
            try:
                if self.enabled:
                    await self._pull_once()
            except Exception as e:
                logger.error(f"Background pull error: {e}")
            await asyncio.sleep(interval)

    async def _pull_once(self) -> None:
        """Single pull cycle — fetch WARNING+ from all drones."""
        drones = load_config()
        level = get_pull_level()
        max_concurrent = get_pull_max_drones()

        for drone in drones[:max_concurrent]:
            hw_id = drone.get("hw_id", "")
            ip = drone.get("ip")
            if not ip:
                continue

            try:
                drone_id = int(hw_id)
            except (ValueError, TypeError):
                continue

            # Fetch session list
            sessions_result = await fetch_drone_sessions(ip)
            if sessions_result is None:
                continue  # Drone unreachable

            sessions = sessions_result.get("sessions", [])
            if not sessions:
                continue

            # Pull the most recent session
            latest = sessions[0]
            sid = latest["session_id"]

            # Fetch content at WARNING+ level
            content = await fetch_drone_session_content(ip, sid, level=level)
            if content is None or not content.get("lines"):
                continue

            # Store to local GCS filesystem
            drone_dir = os.path.join(self.log_dir, f"drone_{drone_id}")
            os.makedirs(drone_dir, exist_ok=True)
            outfile = os.path.join(drone_dir, f"{sid}.jsonl")
            with open(outfile, "a", encoding="utf-8") as f:
                for entry in content["lines"]:
                    f.write(json.dumps(entry) + "\n")

            logger.debug(
                f"Pulled {len(content['lines'])} entries from drone {drone_id} session {sid}"
            )
