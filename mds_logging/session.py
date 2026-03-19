"""
Session lifecycle management — create, list, rotate, cleanup.

Sessions are named s_{YYYYMMDD}_{HHMMSS} and stored as .jsonl files.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

import os
from datetime import datetime, timezone


def create_session(log_dir: str) -> str:
    """Create a new session, return its ID. Creates dir if needed."""
    os.makedirs(log_dir, exist_ok=True)
    now = datetime.now(timezone.utc)
    session_id = now.strftime("s_%Y%m%d_%H%M%S")
    filepath = os.path.join(log_dir, f"{session_id}.jsonl")
    if os.path.exists(filepath):
        session_id = session_id + "_2"
        filepath = os.path.join(log_dir, f"{session_id}.jsonl")
    # Create empty file
    open(filepath, "a").close()
    return session_id


def get_session_id() -> str:
    """Generate a session ID for the current moment."""
    return datetime.now(timezone.utc).strftime("s_%Y%m%d_%H%M%S")


def get_session_filepath(log_dir: str, session_id: str) -> str:
    """Get the full file path for a session."""
    return os.path.join(log_dir, f"{session_id}.jsonl")


def list_sessions(log_dir: str) -> list[dict]:
    """List sessions in log_dir, newest first. Returns list of dicts."""
    if not os.path.isdir(log_dir):
        return []
    files = []
    for fname in os.listdir(log_dir):
        if fname.endswith(".jsonl") and fname.startswith("s_"):
            fpath = os.path.join(log_dir, fname)
            stat = os.stat(fpath)
            files.append({
                "session_id": fname[:-6],  # strip .jsonl (3.8-compatible)
                "size_bytes": stat.st_size,
                "modified": stat.st_mtime,
            })
    files.sort(key=lambda f: f["modified"], reverse=True)
    return files


def cleanup_sessions(log_dir: str, max_sessions: int, max_size_mb: int) -> None:
    """Remove oldest sessions exceeding count or size limits."""
    sessions = list_sessions(log_dir)
    if not sessions:
        return
    # Remove by count
    while len(sessions) > max_sessions:
        oldest = sessions.pop()
        fpath = os.path.join(log_dir, f"{oldest['session_id']}.jsonl")
        if os.path.exists(fpath):
            os.remove(fpath)
    # Remove by size
    max_bytes = max_size_mb * 1024 * 1024
    total = sum(s["size_bytes"] for s in sessions)
    while total > max_bytes and len(sessions) > 1:
        oldest = sessions.pop()
        fpath = os.path.join(log_dir, f"{oldest['session_id']}.jsonl")
        if os.path.exists(fpath):
            os.remove(fpath)
            total -= oldest["size_bytes"]
