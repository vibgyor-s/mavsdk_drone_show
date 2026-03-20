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

    return router
