import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from mds_logging import get_logger


logger = get_logger("swarm_runtime_state")

_ENV_PATH = "MDS_SWARM_RUNTIME_ASSIGNMENT_PATH"
_DEFAULT_FILENAME = "smart_swarm_assignment.json"


def get_runtime_assignment_path() -> Path:
    override = os.getenv(_ENV_PATH)
    if override:
        return Path(override)

    project_root = Path(__file__).resolve().parent.parent
    return project_root / "logs" / "runtime" / _DEFAULT_FILENAME


def write_runtime_swarm_assignment(assignment: Optional[Dict[str, Any]]) -> None:
    """Persist the latest live Smart Swarm assignment for local cross-process readers."""
    path = get_runtime_assignment_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"assignment": assignment or {}}

    with NamedTemporaryFile("w", dir=path.parent, prefix=path.name, suffix=".tmp", delete=False) as handle:
        json.dump(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())
        temp_path = Path(handle.name)

    temp_path.replace(path)


def read_runtime_swarm_assignment() -> Optional[Dict[str, Any]]:
    """Read the latest persisted live Smart Swarm assignment, if present."""
    path = get_runtime_assignment_path()
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text())
    except Exception as exc:
        logger.debug("Failed to read runtime swarm assignment from %s: %s", path, exc)
        return None

    assignment = payload.get("assignment") if isinstance(payload, dict) else None
    if not isinstance(assignment, dict) or not assignment:
        return None
    return assignment
