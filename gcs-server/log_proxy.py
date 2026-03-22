"""
Async helpers to proxy log requests from GCS to individual drones.

GCS is the single gateway — the UI never connects directly to drones.
Drone IPs are resolved from the fleet config (same as command.py).
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

import httpx

from config import load_config
from mds_logging import get_logger
from mds_logging.schema import build_log_entry

logger = get_logger("log_proxy")

# Drone API port (same as Params.drone_api_port but avoids circular import)
_DRONE_API_PORT = 7070
_TIMEOUT = 5.0  # seconds


def resolve_drone_ip(drone_id: int) -> Optional[str]:
    """Resolve a drone_id (hw_id as int) to its IP address from fleet config."""
    drones = load_config()
    for d in drones:
        hw = d.get("hw_id", "")
        try:
            if int(hw) == drone_id:
                return d.get("ip")
        except (ValueError, TypeError):
            continue
    return None


async def fetch_drone_sessions(drone_ip: str) -> Optional[dict]:
    """Fetch session list from a drone. Returns None if unreachable."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"http://{drone_ip}:{_DRONE_API_PORT}/api/logs/sessions")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Drone at {drone_ip} unreachable: {e}")
        return None


async def fetch_drone_session_content(
    drone_ip: str,
    session_id: str,
    level: str | None = None,
    component: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    since: str | None = None,
) -> Optional[dict]:
    """Fetch session content from a drone. Returns None if unreachable."""
    params: dict = {}
    if level:
        params["level"] = level
    if component:
        params["component"] = component
    if limit is not None:
        params["limit"] = limit
    if offset:
        params["offset"] = offset
    if since:
        params["since"] = since
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"http://{drone_ip}:{_DRONE_API_PORT}/api/logs/sessions/{session_id}",
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning(f"Drone at {drone_ip} unreachable for session {session_id}: {e}")
        return None


async def stream_drone_logs(
    drone_ip: str,
    drone_id: int,
    level: str | None = None,
    component: str | None = None,
    source: str | None = None,
):
    """Async generator that proxies SSE from a drone. Yields SSE data lines."""
    params: dict = {}
    if level:
        params["level"] = level
    if component:
        params["component"] = component
    if source:
        params["source"] = source
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET",
                f"http://{drone_ip}:{_DRONE_API_PORT}/api/logs/stream",
                params=params,
            ) as resp:
                resp.raise_for_status()
                try:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            yield line + "\n\n"
                except (asyncio.CancelledError, GeneratorExit):
                    return
    except (asyncio.CancelledError, GeneratorExit):
        return
    except Exception as e:
        error = build_log_entry(
            level="WARNING",
            component="log_proxy",
            source="gcs",
            msg=f"Drone #{drone_id} log stream unavailable: {e}",
            session_id="",
            drone_id=drone_id,
            extra={
                "kind": "proxy_stream_error",
                "drone_ip": drone_ip,
                "error": str(e),
            },
        )
        yield f"data: {json.dumps(error)}\n\n"
