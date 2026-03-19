# Unified Logging System Guide

> **Package:** `mds_logging/` at repo root
> **Python:** 3.8+ (uses `from __future__ import annotations`)
> **Format:** JSONL (file) + colored text (console)

## Architecture

All MDS components share a single logging contract via the `mds_logging` package:

```
mds_logging/
  __init__.py     # Public API: get_logger(), set_session(), set_source()
  schema.py       # JSONL field definitions and validation
  constants.py    # Environment variable config (MDS_LOG_* prefix)
  formatter.py    # JSONLFormatter (file) + ConsoleFormatter (terminal)
  session.py      # Session lifecycle: create, list, cleanup
  handlers.py     # SessionFileHandler + WatcherHandler
  watcher.py      # In-memory pub/sub for SSE streaming
  registry.py     # Component self-registration
  cli.py          # Shared CLI flags (--verbose, --debug, --quiet, etc.)
  drone.py        # init_drone_logging() — drone-side init
  server.py       # init_server_logging() — GCS server init
```

## Quick Start

### Drone-side component

```python
from mds_logging.drone import init_drone_logging
from mds_logging import get_logger, register_component

register_component("my_component", "drone", "What this component does")
init_drone_logging(drone_id=5)
logger = get_logger("my_component")

logger.info("System ready")
logger.warning("Low battery", extra={"mds_extra": {"voltage": 11.2}})
```

### GCS server component

```python
from mds_logging.server import init_server_logging
from mds_logging import get_logger, register_component

register_component("my_api", "gcs", "REST API endpoints")
init_server_logging()
logger = get_logger("my_api")

logger.info("Server started on port 5000")
```

### Module that doesn't own initialization

```python
from mds_logging import get_logger

logger = get_logger("my_module")
logger.debug("Processing data")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MDS_LOG_LEVEL` | `INFO` | Console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `MDS_LOG_FILE_LEVEL` | `DEBUG` | File log level |
| `MDS_LOG_MAX_SESSIONS` | `10` | Max session files to keep per device |
| `MDS_LOG_MAX_SIZE_MB` | `100` | Max total log size in MB per device |
| `MDS_LOG_DIR` | `logs/sessions` | Session log directory |
| `MDS_LOG_CONSOLE_FORMAT` | `text` | Console format: `text` (colored) or `json` |
| `MDS_LOG_FLUSH` | `true` | Flush file handler after every line |

### Deprecated (still supported via shim)

| Old Variable | Maps To |
|-------------|---------|
| `DRONE_LOG_LEVEL` | `MDS_LOG_LEVEL` |
| `DRONE_LOG_FILE` | `MDS_LOG_DIR` |

## CLI Flags

Add to any argparse-based script:

```python
from mds_logging.cli import add_log_arguments, apply_log_args

parser = argparse.ArgumentParser()
add_log_arguments(parser)
args = parser.parse_args()
apply_log_args(args)
```

Available flags:
- `--verbose` / `--debug` — Set console level to DEBUG
- `--quiet` — Set console level to WARNING
- `--log-dir PATH` — Override log directory
- `--log-json` — Output JSON to console instead of colored text

## Session Management

Sessions are named `s_YYYYMMDD_HHMMSS` and stored as `.jsonl` files.

```python
from mds_logging.session import create_session, list_sessions, cleanup_sessions

# Create a new session
session_id = create_session("logs/sessions")  # Returns "s_20260319_140000"

# List sessions (newest first)
sessions = list_sessions("logs/sessions")
# [{"session_id": "s_20260319_140000", "size_bytes": 1024, "modified": 1742...}, ...]

# Cleanup old sessions (hybrid: count + size)
cleanup_sessions("logs/sessions", max_sessions=10, max_size_mb=100)
```

## JSONL Schema

Every log line follows this schema:

```json
{
  "ts": "2026-03-19T14:00:00.123Z",
  "level": "INFO",
  "component": "coordinator",
  "source": "drone",
  "drone_id": 5,
  "session_id": "s_20260319_140000",
  "msg": "Armed successfully",
  "extra": {"mode": "OFFBOARD", "battery": 12.4}
}
```

| Field | Type | Description |
|-------|------|-------------|
| `ts` | string | ISO 8601 UTC timestamp with milliseconds |
| `level` | string | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `component` | string | Logical component name |
| `source` | string | drone, gcs, frontend, infra |
| `drone_id` | int/null | Drone identifier (null for GCS) |
| `session_id` | string | Current session ID |
| `msg` | string | Human-readable message |
| `extra` | object/null | Structured metadata |

## Console Output

Colored text format for terminals:

```
14:00:00.123 INFO  [coordinator] Armed successfully (mode=OFFBOARD)
14:00:00.456 ERROR [telemetry] Connection lost (drone_id=5)
```

## Component Registry

Components self-register at startup for auto-discovery:

```python
from mds_logging import register_component, get_registry

register_component("coordinator", "drone", "System initialization")
register_component("api", "gcs", "FastAPI server")

# GCS exposes this via GET /api/logs/sources (Phase 2)
registry = get_registry()
```

## Troubleshooting

**No log output?**
Call `init_drone_logging()` or `init_server_logging()` before `get_logger()`. The init functions set up handlers on the root logger.

**Duplicate log lines?**
Ensure init is called only once per process. The init functions call `root.handlers.clear()` to prevent duplicates.

**Old env vars not working?**
`DRONE_LOG_LEVEL` and `DRONE_LOG_FILE` are supported via deprecation shim with a warning. Migrate to `MDS_LOG_*` prefix.

**Where are log files?**
Default: `logs/sessions/s_YYYYMMDD_HHMMSS.jsonl`. Override with `MDS_LOG_DIR` env var or `--log-dir` CLI flag.
