"""
Component self-registration — no hardcoded list.

Components call register_component() at startup. GCS exposes the registry
via GET /api/logs/sources for the frontend to auto-discover.
Reference: docs/guides/logging-system.md
"""
from __future__ import annotations

from datetime import datetime, timezone

_REGISTRY: dict[str, dict] = {}


def register_component(name: str, category: str, description: str) -> None:
    """Register a log source component."""
    _REGISTRY[name] = {
        "name": name,
        "category": category,
        "description": description,
        "registered_at": datetime.now(timezone.utc).isoformat() + "Z",
    }


def get_registry() -> dict[str, dict]:
    """Return a copy of the current registry."""
    return dict(_REGISTRY)


def clear_registry() -> None:
    """Clear registry (for testing)."""
    _REGISTRY.clear()
