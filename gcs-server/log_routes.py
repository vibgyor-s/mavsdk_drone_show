"""
GCS Log API Router — REST + SSE endpoints for log access.

Endpoints:
  GET  /api/logs/sources                  — registered components
  GET  /api/logs/sessions                 — list GCS sessions
  GET  /api/logs/sessions/{session_id}    — retrieve session content
  GET  /api/logs/stream                   — real-time SSE stream
  POST /api/logs/frontend                 — receive frontend error reports

Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from mds_logging.registry import get_registry
from mds_logging.session import list_sessions, read_session_lines
from mds_logging.watcher import get_watcher, LogWatcher
from mds_logging.constants import get_log_dir
from mds_logging import get_logger

logger = get_logger("log_api")


def create_log_router(
    log_dir: str | None = None,
    watcher: LogWatcher | None = None,
) -> APIRouter:
    """Create the log API router. Accepts overrides for testing."""

    _log_dir = log_dir or get_log_dir()
    _watcher = watcher or get_watcher()

    router = APIRouter(prefix="/api/logs", tags=["Logs"])

    @router.get("/sources")
    async def get_sources():
        """List all registered log source components."""
        return {"components": get_registry()}

    @router.get("/sessions")
    async def get_sessions():
        """List GCS log sessions, newest first."""
        sessions = list_sessions(_log_dir)
        return {"sessions": sessions}

    @router.get("/sessions/{session_id}")
    async def get_session(
        session_id: str,
        level: Optional[str] = None,
        component: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ):
        """Retrieve filtered JSONL content from a GCS log session."""
        lines = read_session_lines(
            _log_dir, session_id,
            level=level, component=component, limit=limit, offset=offset,
        )
        if lines is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return {"session_id": session_id, "count": len(lines), "lines": lines}

    @router.get("/stream")
    async def stream_logs(
        level: Optional[str] = None,
        component: Optional[str] = None,
        source: Optional[str] = None,
        drone_id: Optional[int] = None,
    ):
        """Stream GCS logs in real-time via SSE."""
        async def event_generator():
            async for entry in _watcher.subscribe(
                level=level, component=component, source=source, drone_id=drone_id,
            ):
                yield f"data: {json.dumps(entry)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.post("/frontend")
    async def receive_frontend_report(report: dict):
        """Receive error/log reports from the React frontend."""
        level = report.get("level", "ERROR")
        component = report.get("component", "frontend")
        msg = report.get("msg", "")
        extra = report.get("extra")
        fe_logger = get_logger(component)
        log_level = getattr(logging, level, logging.ERROR)
        fe_logger.log(log_level, msg, extra={"mds_extra": extra})
        return {"status": "received"}

    # --- Drone proxy endpoints ---

    @router.get("/drone/{drone_id}/sessions")
    async def get_drone_sessions(drone_id: int):
        """List log sessions on a specific drone (proxied)."""
        from log_proxy import resolve_drone_ip, fetch_drone_sessions
        ip = resolve_drone_ip(drone_id)
        if ip is None:
            raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found in config")
        result = await fetch_drone_sessions(ip)
        if result is None:
            raise HTTPException(status_code=502, detail=f"Drone {drone_id} unreachable")
        return result

    @router.get("/drone/{drone_id}/sessions/{session_id}")
    async def get_drone_session(
        drone_id: int,
        session_id: str,
        level: Optional[str] = None,
        component: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ):
        """Retrieve session content from a specific drone (proxied)."""
        from log_proxy import resolve_drone_ip, fetch_drone_session_content
        ip = resolve_drone_ip(drone_id)
        if ip is None:
            raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found in config")
        result = await fetch_drone_session_content(
            ip, session_id, level=level, component=component, limit=limit, offset=offset,
        )
        if result is None:
            raise HTTPException(status_code=502, detail=f"Drone {drone_id} unreachable")
        return result

    @router.get("/drone/{drone_id}/stream")
    async def stream_drone(
        drone_id: int,
        level: Optional[str] = None,
        component: Optional[str] = None,
    ):
        """Proxy real-time log stream from a specific drone via SSE."""
        from log_proxy import resolve_drone_ip, stream_drone_logs
        ip = resolve_drone_ip(drone_id)
        if ip is None:
            raise HTTPException(status_code=404, detail=f"Drone {drone_id} not found in config")
        return StreamingResponse(
            stream_drone_logs(ip, level=level, component=component),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router
