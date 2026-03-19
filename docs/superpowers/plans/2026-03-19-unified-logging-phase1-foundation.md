# Unified Logging System — Phase 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `mds_logging` shared contract package and migrate all Python components from fragmented logging to the unified system.

**Architecture:** A top-level `mds_logging/` Python package at `/opt/mavsdk_drone_show/mds_logging/` provides JSONL-formatted file logging with session management, colored console output, and a pub/sub watcher for future SSE streaming. Drone-side and GCS-side thin wrappers call the same core. Each existing component is migrated one file at a time, tested, and committed individually.

**Tech Stack:** Python 3.8+ (uses `from __future__ import annotations` for PEP 604/585 syntax compatibility), standard `logging` module, JSON serialization, `argparse` integration

**Compatibility note:** All `mds_logging/` modules MUST start with `from __future__ import annotations` to support `int | None` and `dict[str, dict]` syntax on Python 3.8/3.9 (per `pyproject.toml` `requires-python = ">=3.8"`).

**Spec:** `docs/superpowers/specs/2026-03-19-unified-logging-system-design.md`

---

## File Structure

### New Files (create)

| File | Responsibility |
|------|---------------|
| `mds_logging/__init__.py` | Public API: `get_logger()`, `init_logging()`, `register_component()` |
| `mds_logging/schema.py` | JSONL field definitions, validation, log entry builder |
| `mds_logging/constants.py` | Environment variable names, defaults, deprecation shims |
| `mds_logging/formatter.py` | `JSONLFormatter` (file) + `ConsoleFormatter` (terminal with colors) |
| `mds_logging/session.py` | Session lifecycle: create, name, rotate, cleanup |
| `mds_logging/handlers.py` | `SessionFileHandler` with flush-on-write |
| `mds_logging/watcher.py` | In-memory pub/sub for real-time SSE (Phase 2 consumer) |
| `mds_logging/registry.py` | Component self-registration dict |
| `mds_logging/cli.py` | `add_log_arguments(parser)` for unified CLI flags |
| `mds_logging/drone.py` | `init_drone_logging()` convenience wrapper |
| `mds_logging/server.py` | `init_server_logging()` convenience wrapper + GCS helpers |
| `tests/test_mds_logging/__init__.py` | Test package |
| `tests/test_mds_logging/test_schema.py` | JSONL format validation |
| `tests/test_mds_logging/test_constants.py` | Env var reading, defaults, deprecation shim |
| `tests/test_mds_logging/test_formatter.py` | Console + JSONL formatter output |
| `tests/test_mds_logging/test_session.py` | Session lifecycle, rotation, cleanup |
| `tests/test_mds_logging/test_handlers.py` | File handler, flush behavior |
| `tests/test_mds_logging/test_watcher.py` | Pub/sub, buffer, filtering |
| `tests/test_mds_logging/test_registry.py` | Component registration |
| `tests/test_mds_logging/test_cli.py` | CLI flag parsing |
| `tests/test_mds_logging/test_integration.py` | End-to-end: init → log → verify JSONL file |

### Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml:32-34` | Add `mds_logging*` to packages.find include list |
| `.gitignore:131-134` | Add `logs/sessions/`, `logs/current` |
| `gcs-server/app_fastapi.py:80-82` | Replace `from gcs_logging import ...` with `from mds_logging.server import ...` |
| `gcs-server/command.py:22-27` | Replace `from gcs_logging import ...` with `from mds_logging import get_logger` |
| `gcs-server/telemetry.py:50` | Replace `get_logger()` from `gcs_logging` |
| `gcs-server/git_status.py` | Replace `gcs_logging` in `__main__` block |
| `gcs-server/heartbeat.py:5` | Replace `logging.getLogger(__name__)` with `from mds_logging import get_logger` |
| `gcs-server/utils.py:50+` | Replace bare `logging.*` with `get_logger()` |
| `gcs-server/config.py:24` | Replace `logging.getLogger(__name__)` |
| `gcs-server/command_tracker.py:61` | Replace `logging.getLogger(__name__)` |
| `gcs-server/origin.py:14-15` | Remove `logging.basicConfig()`, use `mds_logging` |
| `gcs-server/sar/routes.py:34` | Replace `logging.getLogger(__name__)` |
| `gcs-server/sar/coverage_planner.py:37` | Same |
| `gcs-server/sar/mission_manager.py:17` | Same |
| `gcs-server/sar/poi_manager.py:16` | Same |
| `gcs-server/sar/terrain.py:21` | Same |
| `coordinator.py:24,54-78` | Remove inline logging setup, use `init_drone_logging()` |
| `actions.py:53-54,75-94` | Remove inline logging setup, use `init_drone_logging()` |
| `drone_show.py:99,127,2159,2196-2208` | Replace `configure_logging()`, use `init_drone_logging()` + CLI flags |
| `smart_swarm.py:91-92,121,1298` | Same |
| `swarm_trajectory_mission.py:90,114-118,1553,1578-1583` | Same |
| `src/drone_api_server.py:32` | Replace bare `import logging` with `from mds_logging import get_logger` |
| `src/drone_communicator.py:5` | Same |
| `src/heartbeat_sender.py:4` | Same |
| `src/drone_setup.py:6,17` | Same |
| `src/connectivity_checker.py:1` | Same |
| `src/led_controller.py:85-86` | Replace `logging.getLogger` + `print()` with `get_logger()` |
| `src/params.py:3,9` | Replace `import logging` with `from mds_logging import get_logger` |
| `quickscout_mission.py:18,30-34` | Remove `logging.basicConfig()`, use `mds_logging` |
| `process_formation.py:2,11-24` | Remove inline setup, use `mds_logging` |
| `led_indicator.py:40,49,57` | Replace `print()` + `basicConfig` with `get_logger()` |
| `functions/file_management.py:7` | Remove `logging.basicConfig()`, use `mds_logging` |
| `drone_show_src/utils.py:40-91` | Delete `configure_logging()` function only (keep other utils) |

### Files to Delete

| File | After |
|------|-------|
| `gcs-server/logging_config.py` | All GCS migrations verified |
| `gcs-server/gcs_logging.py` | All GCS migrations verified |
| `src/logging_config.py` | All drone migrations verified |

---

## Task 1: Create `mds_logging` Core — Schema, Constants, Formatters

**Files:**
- Create: `mds_logging/__init__.py`
- Create: `mds_logging/schema.py`
- Create: `mds_logging/constants.py`
- Create: `mds_logging/formatter.py`
- Create: `tests/test_mds_logging/__init__.py`
- Create: `tests/test_mds_logging/test_schema.py`
- Create: `tests/test_mds_logging/test_constants.py`
- Create: `tests/test_mds_logging/test_formatter.py`
- Modify: `pyproject.toml:32-34`

- [ ] **Step 1: Write schema tests**

Create `tests/test_mds_logging/__init__.py` (empty) and `tests/test_mds_logging/test_schema.py`:

```python
"""Tests for mds_logging.schema — JSONL log entry schema."""
import json
import pytest
from mds_logging.schema import build_log_entry, REQUIRED_FIELDS, VALID_LEVELS, VALID_SOURCES


class TestBuildLogEntry:
    def test_minimal_entry_has_all_required_fields(self):
        entry = build_log_entry(
            level="INFO",
            component="test",
            source="gcs",
            msg="hello",
            session_id="s_20260319_140000",
        )
        for field in REQUIRED_FIELDS:
            assert field in entry, f"Missing required field: {field}"

    def test_timestamp_is_iso8601_utc(self):
        entry = build_log_entry(
            level="INFO", component="test", source="gcs",
            msg="hello", session_id="s_20260319_140000",
        )
        ts = entry["ts"]
        assert ts.endswith("Z"), f"Timestamp must end with Z: {ts}"
        assert "T" in ts, f"Timestamp must contain T: {ts}"

    def test_entry_serializes_to_valid_json(self):
        entry = build_log_entry(
            level="DEBUG", component="coord", source="drone",
            msg="test msg", session_id="s_20260319_140000",
            drone_id=5, extra={"key": "value"},
        )
        line = json.dumps(entry)
        parsed = json.loads(line)
        assert parsed["level"] == "DEBUG"
        assert parsed["drone_id"] == 5
        assert parsed["extra"]["key"] == "value"

    def test_drone_id_defaults_to_none(self):
        entry = build_log_entry(
            level="INFO", component="api", source="gcs",
            msg="test", session_id="s_20260319_140000",
        )
        assert entry["drone_id"] is None

    def test_extra_defaults_to_none(self):
        entry = build_log_entry(
            level="INFO", component="api", source="gcs",
            msg="test", session_id="s_20260319_140000",
        )
        assert entry["extra"] is None

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="level"):
            build_log_entry(
                level="TRACE", component="test", source="gcs",
                msg="bad", session_id="s_20260319_140000",
            )

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError, match="source"):
            build_log_entry(
                level="INFO", component="test", source="unknown",
                msg="bad", session_id="s_20260319_140000",
            )

    def test_valid_levels(self):
        assert set(VALID_LEVELS) == {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def test_valid_sources(self):
        assert set(VALID_SOURCES) == {"drone", "gcs", "frontend", "infra"}
```

- [ ] **Step 2: Write constants tests**

Create `tests/test_mds_logging/test_constants.py`:

```python
"""Tests for mds_logging.constants — env var reading and deprecation shims."""
import os
import pytest
from unittest.mock import patch
from mds_logging.constants import (
    get_log_level, get_file_log_level, get_max_sessions,
    get_max_size_mb, get_log_dir, get_console_format, get_flush_enabled,
    DEFAULTS,
)


class TestDefaults:
    def test_default_log_level(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_log_level() == "INFO"

    def test_default_file_log_level(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_file_log_level() == "DEBUG"

    def test_default_max_sessions(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_max_sessions() == 10

    def test_default_max_size_mb(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_max_size_mb() == 100

    def test_default_log_dir(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_log_dir() == "logs/sessions"

    def test_default_console_format(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_console_format() == "text"

    def test_default_flush(self):
        with patch.dict(os.environ, {}, clear=True):
            assert get_flush_enabled() is True


class TestEnvOverrides:
    def test_mds_log_level_override(self):
        with patch.dict(os.environ, {"MDS_LOG_LEVEL": "DEBUG"}):
            assert get_log_level() == "DEBUG"

    def test_mds_log_max_sessions_override(self):
        with patch.dict(os.environ, {"MDS_LOG_MAX_SESSIONS": "20"}):
            assert get_max_sessions() == 20

    def test_mds_log_dir_override(self):
        with patch.dict(os.environ, {"MDS_LOG_DIR": "/tmp/test_logs"}):
            assert get_log_dir() == "/tmp/test_logs"


class TestDeprecationShims:
    def test_drone_log_level_fallback(self):
        """Old DRONE_LOG_LEVEL env var still works via shim."""
        with patch.dict(os.environ, {"DRONE_LOG_LEVEL": "WARNING"}, clear=True):
            assert get_log_level() == "WARNING"

    def test_mds_takes_precedence_over_drone(self):
        """New MDS_LOG_LEVEL takes precedence over old DRONE_LOG_LEVEL."""
        with patch.dict(os.environ, {
            "MDS_LOG_LEVEL": "ERROR",
            "DRONE_LOG_LEVEL": "DEBUG",
        }):
            assert get_log_level() == "ERROR"
```

- [ ] **Step 3: Write formatter tests**

Create `tests/test_mds_logging/test_formatter.py`:

```python
"""Tests for mds_logging.formatter — JSONL and console formatters."""
import json
import logging
import pytest
from mds_logging.formatter import JSONLFormatter, ConsoleFormatter


class TestJSONLFormatter:
    def _make_record(self, msg="test message", level=logging.INFO):
        record = logging.LogRecord(
            name="test.component", level=level, pathname="",
            lineno=0, msg=msg, args=(), exc_info=None,
        )
        record.mds_component = "coordinator"
        record.mds_source = "drone"
        record.mds_drone_id = 3
        record.mds_session_id = "s_20260319_140000"
        record.mds_extra = {"key": "value"}
        return record

    def test_output_is_valid_jsonl(self):
        fmt = JSONLFormatter()
        record = self._make_record()
        line = fmt.format(record)
        parsed = json.loads(line)
        assert parsed["msg"] == "test message"
        assert parsed["component"] == "coordinator"

    def test_output_ends_without_newline(self):
        """Handler adds newline, not formatter."""
        fmt = JSONLFormatter()
        record = self._make_record()
        line = fmt.format(record)
        assert not line.endswith("\n")

    def test_level_name_is_string(self):
        fmt = JSONLFormatter()
        record = self._make_record(level=logging.WARNING)
        parsed = json.loads(fmt.format(record))
        assert parsed["level"] == "WARNING"

    def test_missing_mds_fields_use_defaults(self):
        fmt = JSONLFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="bare log", args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert parsed["component"] == "test"
        assert parsed["source"] == "gcs"
        assert parsed["drone_id"] is None


class TestConsoleFormatter:
    def _make_record(self, msg="hello", level=logging.INFO):
        record = logging.LogRecord(
            name="test", level=level, pathname="",
            lineno=0, msg=msg, args=(), exc_info=None,
        )
        record.mds_component = "coordinator"
        record.mds_extra = None
        return record

    def test_output_contains_component_in_brackets(self):
        fmt = ConsoleFormatter()
        record = self._make_record()
        line = fmt.format(record)
        assert "[coordinator]" in line

    def test_output_contains_level(self):
        fmt = ConsoleFormatter()
        record = self._make_record(level=logging.ERROR)
        line = fmt.format(record)
        assert "ERROR" in line

    def test_output_contains_message(self):
        fmt = ConsoleFormatter()
        record = self._make_record(msg="drone armed")
        line = fmt.format(record)
        assert "drone armed" in line

    def test_extra_fields_appended(self):
        fmt = ConsoleFormatter()
        record = self._make_record()
        record.mds_extra = {"battery": 12.4}
        line = fmt.format(record)
        assert "battery=12.4" in line
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/test_mds_logging/ -v 2>&1 | head -30`
Expected: ModuleNotFoundError — `mds_logging` does not exist yet.

- [ ] **Step 5: Create `mds_logging/schema.py`**

```python
"""
JSONL log entry schema — the single source of truth for log format.

Every log line across every MDS component follows this schema.
Reference: docs/guides/logging-system.md
"""
from datetime import datetime, timezone

REQUIRED_FIELDS = ("ts", "level", "component", "source", "drone_id", "session_id", "msg")
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
VALID_SOURCES = ("drone", "gcs", "frontend", "infra")


def build_log_entry(
    level: str,
    component: str,
    source: str,
    msg: str,
    session_id: str,
    drone_id: int | None = None,
    extra: dict | None = None,
    ts: str | None = None,
) -> dict:
    """Build a validated JSONL log entry dict."""
    if level not in VALID_LEVELS:
        raise ValueError(f"Invalid level '{level}', must be one of {VALID_LEVELS}")
    if source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{source}', must be one of {VALID_SOURCES}")
    if ts is None:
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return {
        "ts": ts,
        "level": level,
        "component": component,
        "source": source,
        "drone_id": drone_id,
        "session_id": session_id,
        "msg": msg,
        "extra": extra,
    }
```

- [ ] **Step 6: Create `mds_logging/constants.py`**

```python
"""
Environment variable names, defaults, and deprecation shims.

All logging configuration flows through environment variables with the
MDS_LOG_* prefix. Old DRONE_* vars are supported via shim for one release.
Reference: docs/guides/logging-system.md
"""
import os
import warnings

DEFAULTS = {
    "log_level": "INFO",
    "file_log_level": "DEBUG",
    "max_sessions": 10,
    "max_size_mb": 100,
    "log_dir": "logs/sessions",
    "console_format": "text",
    "flush": True,
}


def _get_with_shim(new_key: str, old_key: str | None, default: str) -> str:
    """Read env var with fallback to deprecated name."""
    value = os.environ.get(new_key)
    if value is not None:
        return value
    if old_key:
        old_value = os.environ.get(old_key)
        if old_value is not None:
            warnings.warn(
                f"Environment variable {old_key} is deprecated, use {new_key} instead.",
                DeprecationWarning,
                stacklevel=3,
            )
            return old_value
    return default


def get_log_level() -> str:
    return _get_with_shim("MDS_LOG_LEVEL", "DRONE_LOG_LEVEL", DEFAULTS["log_level"])


def get_file_log_level() -> str:
    return os.environ.get("MDS_LOG_FILE_LEVEL", DEFAULTS["file_log_level"])


def get_max_sessions() -> int:
    return int(os.environ.get("MDS_LOG_MAX_SESSIONS", DEFAULTS["max_sessions"]))


def get_max_size_mb() -> int:
    return int(os.environ.get("MDS_LOG_MAX_SIZE_MB", DEFAULTS["max_size_mb"]))


def get_log_dir() -> str:
    return _get_with_shim("MDS_LOG_DIR", "DRONE_LOG_FILE", DEFAULTS["log_dir"])


def get_console_format() -> str:
    return os.environ.get("MDS_LOG_CONSOLE_FORMAT", DEFAULTS["console_format"])


def get_flush_enabled() -> bool:
    return os.environ.get("MDS_LOG_FLUSH", str(DEFAULTS["flush"])).lower() in ("true", "1", "yes")
```

- [ ] **Step 7: Create `mds_logging/formatter.py`**

```python
"""
Log formatters — JSONL for files, colored text for console.

JSONLFormatter produces one JSON object per line for machine parsing.
ConsoleFormatter produces colored human-readable output for terminals.
Reference: docs/guides/logging-system.md
"""
import json
import logging
from datetime import datetime, timezone


class JSONLFormatter(logging.Formatter):
    """Formats log records as single-line JSON (JSONL)."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ts.microsecond // 1000:03d}Z"
        entry = {
            "ts": ts_str,
            "level": record.levelname,
            "component": getattr(record, "mds_component", record.name),
            "source": getattr(record, "mds_source", "gcs"),
            "drone_id": getattr(record, "mds_drone_id", None),
            "session_id": getattr(record, "mds_session_id", ""),
            "msg": record.getMessage(),
            "extra": getattr(record, "mds_extra", None),
        }
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            entry["traceback"] = record.exc_text
        return json.dumps(entry, default=str)


# ANSI color codes
_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[1;31m",  # bold red
}
_RESET = "\033[0m"


class ConsoleFormatter(logging.Formatter):
    """Formats log records as colored human-readable text for terminals."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
        ts_str = ts.strftime("%H:%M:%S.") + f"{ts.microsecond // 1000:03d}"
        level = record.levelname
        color = _COLORS.get(level, "")
        component = getattr(record, "mds_component", record.name)
        msg = record.getMessage()
        extra = getattr(record, "mds_extra", None)

        parts = [f"{ts_str} {color}{level:<5}{_RESET} [{component}] {msg}"]
        if extra:
            kv = " ".join(f"{k}={v}" for k, v in extra.items())
            parts[0] += f" ({kv})"
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            parts.append(record.exc_text)
        return "\n".join(parts)
```

- [ ] **Step 8: Create `mds_logging/__init__.py`** (minimal — just re-exports)

```python
"""
MDS Unified Logging — shared contract for all components.

Usage:
    from mds_logging import get_logger, init_logging, register_component

Reference: docs/guides/logging-system.md
"""
# Public API re-exports — populated by submodules
# Full init_logging is in drone.py / server.py wrappers
# get_logger and register_component are always available

from mds_logging.registry import register_component, get_registry  # noqa: F401

# Lazy logger cache
_loggers: dict[str, "logging.Logger"] = {}
_session_id: str = ""
_source: str = "gcs"  # default, overridden by init_drone_logging / init_server_logging


def get_logger(component: str) -> "logging.Logger":
    """Get a logger configured with MDS metadata.

    Must be called after init_logging() (from drone.py or server.py).
    """
    import logging

    if component in _loggers:
        return _loggers[component]

    logger = logging.getLogger(f"mds.{component}")

    # Inject MDS fields into every record via a filter
    class _MDSFilter(logging.Filter):
        def filter(self, record):
            record.mds_component = component
            record.mds_source = _source
            record.mds_session_id = _session_id
            record.mds_drone_id = getattr(record, "mds_drone_id", None)
            if not hasattr(record, "mds_extra"):
                record.mds_extra = None
            return True

    logger.addFilter(_MDSFilter())
    _loggers[component] = logger
    return logger


def set_session(session_id: str) -> None:
    """Set the current session ID (called by init functions)."""
    global _session_id
    _session_id = session_id


def set_source(source: str) -> None:
    """Set the source type (called by init functions)."""
    global _source
    _source = source
```

- [ ] **Step 9: Update `pyproject.toml`**

At `pyproject.toml:34`, change the include list:

```toml
include = ["src*", "functions*", "gcs-server*", "mds_logging*"]
```

- [ ] **Step 10: Run tests — schema, constants, formatter should pass**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/test_mds_logging/test_schema.py tests/test_mds_logging/test_constants.py tests/test_mds_logging/test_formatter.py -v`
Expected: All tests PASS.

- [ ] **Step 11: Commit**

```bash
git add mds_logging/ tests/test_mds_logging/ pyproject.toml
git commit -m "feat(logging): add mds_logging core — schema, constants, formatters

Create the shared logging contract package with:
- JSONL schema definition and builder (schema.py)
- Environment variable config with deprecation shims (constants.py)
- JSONLFormatter for files and ConsoleFormatter for terminals (formatter.py)
- Public API with get_logger and component registry (__init__.py)
- Full test coverage for all modules"
```

---

## Task 2: Session Management and File Handlers

**Files:**
- Create: `mds_logging/session.py`
- Create: `mds_logging/handlers.py`
- Create: `tests/test_mds_logging/test_session.py`
- Create: `tests/test_mds_logging/test_handlers.py`

- [ ] **Step 1: Write session tests**

Create `tests/test_mds_logging/test_session.py`:

```python
"""Tests for mds_logging.session — session lifecycle management."""
import os
import time
import pytest
from mds_logging.session import (
    create_session, get_session_id, get_session_filepath,
    list_sessions, cleanup_sessions,
)


@pytest.fixture
def tmp_log_dir(tmp_path):
    log_dir = tmp_path / "sessions"
    log_dir.mkdir()
    return str(log_dir)


class TestCreateSession:
    def test_returns_session_id_with_correct_format(self, tmp_log_dir):
        sid = create_session(tmp_log_dir)
        assert sid.startswith("s_")
        assert len(sid) == 18  # s_YYYYMMDD_HHMMSS

    def test_creates_jsonl_file(self, tmp_log_dir):
        sid = create_session(tmp_log_dir)
        filepath = os.path.join(tmp_log_dir, f"{sid}.jsonl")
        assert os.path.exists(filepath)

    def test_duplicate_second_gets_suffix(self, tmp_log_dir):
        sid1 = create_session(tmp_log_dir)
        # Create a file with the same name to force collision
        sid2_expected = sid1 + "_2"
        sid2 = create_session(tmp_log_dir)
        assert sid2 == sid2_expected


class TestListSessions:
    def test_lists_sessions_newest_first(self, tmp_log_dir):
        # Create two session files with different timestamps
        open(os.path.join(tmp_log_dir, "s_20260318_100000.jsonl"), "w").close()
        time.sleep(0.01)
        open(os.path.join(tmp_log_dir, "s_20260319_100000.jsonl"), "w").close()
        sessions = list_sessions(tmp_log_dir)
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "s_20260319_100000"

    def test_empty_dir_returns_empty_list(self, tmp_log_dir):
        assert list_sessions(tmp_log_dir) == []


class TestCleanupSessions:
    def test_cleanup_by_count(self, tmp_log_dir):
        # Create 12 session files
        for i in range(12):
            fname = f"s_20260301_{i:06d}.jsonl"
            with open(os.path.join(tmp_log_dir, fname), "w") as f:
                f.write('{"test": true}\n')
        cleanup_sessions(tmp_log_dir, max_sessions=10, max_size_mb=1000)
        remaining = os.listdir(tmp_log_dir)
        assert len(remaining) == 10

    def test_cleanup_by_size(self, tmp_log_dir):
        # Create files that exceed size limit
        for i in range(5):
            fname = f"s_20260301_{i:06d}.jsonl"
            with open(os.path.join(tmp_log_dir, fname), "w") as f:
                f.write("x" * (1024 * 1024))  # 1MB each = 5MB total
        # Limit to 3MB — should remove oldest 2
        cleanup_sessions(tmp_log_dir, max_sessions=100, max_size_mb=3)
        remaining = os.listdir(tmp_log_dir)
        assert len(remaining) == 3

    def test_keeps_newest_files(self, tmp_log_dir):
        for i in range(5):
            fname = f"s_20260301_{i:06d}.jsonl"
            with open(os.path.join(tmp_log_dir, fname), "w") as f:
                f.write("data\n")
        cleanup_sessions(tmp_log_dir, max_sessions=3, max_size_mb=1000)
        remaining = sorted(os.listdir(tmp_log_dir))
        assert remaining[0] == "s_20260301_000002.jsonl"  # oldest surviving
```

- [ ] **Step 2: Write handler tests**

Create `tests/test_mds_logging/test_handlers.py`:

```python
"""Tests for mds_logging.handlers — session-aware file handler."""
import json
import logging
import os
import pytest
from mds_logging.handlers import SessionFileHandler
from mds_logging.formatter import JSONLFormatter


@pytest.fixture
def tmp_log_file(tmp_path):
    return str(tmp_path / "test_session.jsonl")


class TestSessionFileHandler:
    def test_writes_jsonl_lines(self, tmp_log_file):
        handler = SessionFileHandler(tmp_log_file, flush_every_line=True)
        handler.setFormatter(JSONLFormatter())
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="hello world", args=(), exc_info=None,
        )
        record.mds_component = "test"
        record.mds_source = "gcs"
        record.mds_drone_id = None
        record.mds_session_id = "s_test"
        record.mds_extra = None
        handler.emit(record)
        handler.close()

        with open(tmp_log_file) as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed["msg"] == "hello world"

    def test_flush_on_every_line(self, tmp_log_file):
        handler = SessionFileHandler(tmp_log_file, flush_every_line=True)
        handler.setFormatter(JSONLFormatter())
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="flush test", args=(), exc_info=None,
        )
        record.mds_component = "test"
        record.mds_source = "gcs"
        record.mds_drone_id = None
        record.mds_session_id = "s_test"
        record.mds_extra = None
        handler.emit(record)
        # File should be readable immediately (flushed)
        with open(tmp_log_file) as f:
            assert "flush test" in f.read()

    def test_handler_creates_parent_dirs(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "test.jsonl")
        handler = SessionFileHandler(deep_path)
        handler.close()
        assert os.path.exists(deep_path)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/test_mds_logging/test_session.py tests/test_mds_logging/test_handlers.py -v 2>&1 | head -20`
Expected: FAIL — modules don't exist yet.

- [ ] **Step 4: Implement `mds_logging/session.py`**

```python
"""
Session lifecycle management — create, list, rotate, cleanup.

Sessions are named s_{YYYYMMDD}_{HHMMSS} and stored as .jsonl files.
Reference: docs/guides/logging-system.md
"""
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
                "session_id": fname.removesuffix(".jsonl"),
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
```

- [ ] **Step 5: Implement `mds_logging/handlers.py`**

```python
"""
Session-aware file handler with flush-on-write for crash safety.

Reference: docs/guides/logging-system.md
"""
import logging
import os


class SessionFileHandler(logging.FileHandler):
    """File handler that creates parent dirs and optionally flushes every line."""

    def __init__(self, filename: str, flush_every_line: bool = True, **kwargs):
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        self._flush_every_line = flush_every_line
        super().__init__(filename, mode="a", encoding="utf-8", **kwargs)

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        if self._flush_every_line:
            self.flush()


class WatcherHandler(logging.Handler):
    """Handler that publishes log entries to a LogWatcher for SSE streaming.

    Shared by both drone.py and server.py init functions.
    """

    def __init__(self, watcher, formatter):
        super().__init__()
        self._watcher = watcher
        self._formatter = formatter

    def emit(self, record):
        import json
        try:
            line = self._formatter.format(record)
            entry = json.loads(line)
            self._watcher.publish(entry)
        except Exception:
            pass  # Never crash the app for watcher failures
```

- [ ] **Step 6: Run tests — session and handler should pass**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/test_mds_logging/test_session.py tests/test_mds_logging/test_handlers.py -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add mds_logging/session.py mds_logging/handlers.py tests/test_mds_logging/test_session.py tests/test_mds_logging/test_handlers.py
git commit -m "feat(logging): add session management and file handler

Session lifecycle: create with s_YYYYMMDD_HHMMSS naming, list newest
first, cleanup by count (max 10) and size (max 100MB).
SessionFileHandler: flush-on-write for crash safety, auto-creates dirs."
```

---

## Task 3: Watcher, Registry, CLI, and Init Wrappers

**Files:**
- Create: `mds_logging/watcher.py`
- Create: `mds_logging/registry.py`
- Create: `mds_logging/cli.py`
- Create: `mds_logging/drone.py`
- Create: `mds_logging/server.py`
- Create: `tests/test_mds_logging/test_watcher.py`
- Create: `tests/test_mds_logging/test_registry.py`
- Create: `tests/test_mds_logging/test_cli.py`
- Create: `tests/test_mds_logging/test_integration.py`

- [ ] **Step 1: Write watcher tests**

Create `tests/test_mds_logging/test_watcher.py`:

```python
"""Tests for mds_logging.watcher — in-memory pub/sub for SSE."""
import asyncio
import pytest
from mds_logging.watcher import LogWatcher


class TestLogWatcher:
    def test_publish_to_empty_watcher(self):
        """Publishing with no subscribers should not error."""
        watcher = LogWatcher()
        watcher.publish({"msg": "test"})  # no error

    def test_buffer_stores_recent_entries(self):
        watcher = LogWatcher(max_buffer=5)
        for i in range(10):
            watcher.publish({"msg": f"entry_{i}"})
        assert len(watcher._buffer) == 5
        assert watcher._buffer[0]["msg"] == "entry_5"

    @pytest.mark.asyncio
    async def test_subscribe_receives_published(self):
        watcher = LogWatcher()
        received = []

        async def consumer():
            async for entry in watcher.subscribe():
                received.append(entry)
                if len(received) >= 3:
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        for i in range(3):
            watcher.publish({"msg": f"live_{i}"})
        await asyncio.wait_for(task, timeout=2.0)
        assert len(received) == 3

    @pytest.mark.asyncio
    async def test_subscribe_with_level_filter(self):
        watcher = LogWatcher()
        received = []

        async def consumer():
            async for entry in watcher.subscribe(level="ERROR"):
                received.append(entry)
                if len(received) >= 1:
                    break

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.05)
        watcher.publish({"level": "INFO", "msg": "skip"})
        watcher.publish({"level": "ERROR", "msg": "catch"})
        await asyncio.wait_for(task, timeout=2.0)
        assert received[0]["msg"] == "catch"
```

- [ ] **Step 2: Write registry tests**

Create `tests/test_mds_logging/test_registry.py`:

```python
"""Tests for mds_logging.registry — component self-registration."""
from mds_logging.registry import register_component, get_registry, clear_registry


class TestRegistry:
    def setup_method(self):
        clear_registry()

    def test_register_and_retrieve(self):
        register_component("coordinator", "drone", "System init")
        reg = get_registry()
        assert "coordinator" in reg
        assert reg["coordinator"]["category"] == "drone"

    def test_register_multiple(self):
        register_component("api", "gcs", "FastAPI server")
        register_component("coordinator", "drone", "Init")
        assert len(get_registry()) == 2

    def test_overwrite_existing(self):
        register_component("api", "gcs", "Old desc")
        register_component("api", "gcs", "New desc")
        assert get_registry()["api"]["description"] == "New desc"
```

- [ ] **Step 3: Write CLI tests**

Create `tests/test_mds_logging/test_cli.py`:

```python
"""Tests for mds_logging.cli — shared CLI argument parser."""
import argparse
from mds_logging.cli import add_log_arguments


class TestCLIArgs:
    def test_adds_verbose_flag(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_adds_quiet_flag(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--quiet"])
        assert args.quiet is True

    def test_default_no_flags(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args([])
        assert args.verbose is False
        assert args.quiet is False

    def test_debug_is_alias_for_verbose(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--debug"])
        assert args.verbose is True

    def test_log_json_flag(self):
        parser = argparse.ArgumentParser()
        add_log_arguments(parser)
        args = parser.parse_args(["--log-json"])
        assert args.log_json is True
```

- [ ] **Step 4: Write integration test**

Create `tests/test_mds_logging/test_integration.py`:

```python
"""Integration test: full init → log → verify JSONL file."""
import json
import os
import pytest
from mds_logging.drone import init_drone_logging
from mds_logging import get_logger, set_session, set_source


@pytest.fixture
def tmp_log_env(tmp_path, monkeypatch):
    log_dir = str(tmp_path / "sessions")
    monkeypatch.setenv("MDS_LOG_DIR", log_dir)
    return log_dir


class TestEndToEnd:
    def test_drone_init_creates_session_and_logs(self, tmp_log_env):
        session_id = init_drone_logging(drone_id=5, log_dir=tmp_log_env)
        logger = get_logger("coordinator")
        logger.info("Armed successfully", extra={"mds_drone_id": 5, "mds_extra": {"mode": "OFFBOARD"}})

        # Verify JSONL file exists and contains valid entry
        session_file = os.path.join(tmp_log_env, f"{session_id}.jsonl")
        assert os.path.exists(session_file)

        with open(session_file) as f:
            lines = f.readlines()
            assert len(lines) >= 1
            entry = json.loads(lines[-1])
            assert entry["component"] == "coordinator"
            assert entry["source"] == "drone"
            assert entry["drone_id"] == 5
            assert entry["msg"] == "Armed successfully"
            assert entry["extra"]["mode"] == "OFFBOARD"
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/test_mds_logging/test_watcher.py tests/test_mds_logging/test_registry.py tests/test_mds_logging/test_cli.py tests/test_mds_logging/test_integration.py -v 2>&1 | head -30`
Expected: FAIL — modules don't exist yet.

- [ ] **Step 6: Implement `mds_logging/registry.py`**

```python
"""
Component self-registration — no hardcoded list.

Components call register_component() at startup. GCS exposes the registry
via GET /api/logs/sources for the frontend to auto-discover.
Reference: docs/guides/logging-system.md
"""
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
```

- [ ] **Step 7: Implement `mds_logging/watcher.py`**

```python
"""
In-memory pub/sub for real-time log streaming via SSE.

LogWatcher.publish() is called by the log handler on every write.
LogWatcher.subscribe() is an async generator consumed by SSE endpoints.
Zero subscribers = zero overhead.
Reference: docs/guides/logging-system.md
"""
import asyncio
from collections import deque

# Level ordering for filtering
_LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}


def _matches_filter(entry: dict, level: str | None = None, component: str | None = None,
                    source: str | None = None, drone_id: int | None = None) -> bool:
    """Check if a log entry matches the given filters."""
    if level and _LEVEL_ORDER.get(entry.get("level", ""), 0) < _LEVEL_ORDER.get(level, 0):
        return False
    if component and entry.get("component") != component:
        return False
    if source and entry.get("source") != source:
        return False
    if drone_id is not None and entry.get("drone_id") != drone_id:
        return False
    return True


class LogWatcher:
    """In-memory pub/sub for real-time log streaming."""

    def __init__(self, max_buffer: int = 100):
        self._subscribers: list[asyncio.Queue] = []
        self._buffer: deque = deque(maxlen=max_buffer)

    def publish(self, log_entry: dict) -> None:
        """Called by log handler on every write. Non-blocking."""
        self._buffer.append(log_entry)
        for queue in self._subscribers:
            try:
                queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                pass  # Drop entry if subscriber is slow

    async def subscribe(self, level: str | None = None, component: str | None = None,
                        source: str | None = None, drone_id: int | None = None):
        """Async generator yielding filtered log entries."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.append(queue)
        try:
            # Send buffered recent lines first
            for entry in self._buffer:
                if _matches_filter(entry, level, component, source, drone_id):
                    yield entry
            # Stream live
            while True:
                entry = await queue.get()
                if _matches_filter(entry, level, component, source, drone_id):
                    yield entry
        finally:
            self._subscribers.remove(queue)


# Global watcher instance — shared across the process
_watcher = LogWatcher()


def get_watcher() -> LogWatcher:
    """Get the global LogWatcher instance."""
    return _watcher
```

- [ ] **Step 8: Implement `mds_logging/cli.py`**

```python
"""
Shared CLI argument parser for unified logging flags.

Call add_log_arguments(parser) in any script's argparse setup.
Reference: docs/guides/logging-system.md
"""
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
```

- [ ] **Step 9: Implement `mds_logging/drone.py`**

```python
"""
Drone-side logging initialization.

Call init_drone_logging() once at startup in coordinator, drone_show, etc.
Reference: docs/guides/logging-system.md
"""
import logging
import sys

import mds_logging
from mds_logging.constants import get_log_level, get_file_log_level, get_log_dir, get_console_format, get_flush_enabled
from mds_logging.formatter import JSONLFormatter, ConsoleFormatter
from mds_logging.session import create_session, cleanup_sessions, get_session_filepath
from mds_logging.handlers import SessionFileHandler, WatcherHandler
from mds_logging.watcher import get_watcher
from mds_logging.constants import get_max_sessions, get_max_size_mb


def init_drone_logging(drone_id: int | None = None, log_dir: str | None = None) -> str:
    """Initialize logging for a drone-side component.

    Returns the session_id.
    """
    log_dir = log_dir or get_log_dir()

    # Cleanup old sessions
    cleanup_sessions(log_dir, get_max_sessions(), get_max_size_mb())

    # Create new session
    session_id = create_session(log_dir)
    session_file = get_session_filepath(log_dir, session_id)

    # Set global state
    mds_logging.set_session(session_id)
    mds_logging.set_source("drone")

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    # Remove existing handlers to avoid duplicates
    root.handlers.clear()

    # File handler — JSONL, DEBUG level
    file_handler = SessionFileHandler(session_file, flush_every_line=get_flush_enabled())
    file_handler.setLevel(getattr(logging, get_file_log_level()))
    file_handler.setFormatter(JSONLFormatter())
    root.addHandler(file_handler)

    # Console handler — colored text, configurable level
    console_handler = logging.StreamHandler(sys.stdout)
    console_level = get_log_level()
    console_handler.setLevel(getattr(logging, console_level))
    if get_console_format() == "json":
        console_handler.setFormatter(JSONLFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root.addHandler(console_handler)

    # Watcher handler — for SSE streaming (Phase 2)
    watcher_handler = WatcherHandler(get_watcher(), JSONLFormatter())
    watcher_handler.setLevel(logging.DEBUG)
    root.addHandler(watcher_handler)

    return session_id
```

- [ ] **Step 10: Implement `mds_logging/server.py`**

```python
"""
GCS server-side logging initialization.

Call init_server_logging() once at FastAPI startup.
Provides convenience wrappers that match the old gcs_logging.py API
to minimize migration churn in app_fastapi.py.
Reference: docs/guides/logging-system.md
"""
import logging
import sys

import mds_logging
from mds_logging.constants import get_log_level, get_file_log_level, get_log_dir, get_console_format, get_flush_enabled
from mds_logging.formatter import JSONLFormatter, ConsoleFormatter
from mds_logging.session import create_session, cleanup_sessions, get_session_filepath
from mds_logging.handlers import SessionFileHandler, WatcherHandler
from mds_logging.watcher import get_watcher
from mds_logging.constants import get_max_sessions, get_max_size_mb

# Module-level logger for server convenience functions
_server_logger: logging.Logger | None = None


def init_server_logging(log_dir: str | None = None) -> str:
    """Initialize logging for GCS server. Returns session_id."""
    global _server_logger
    log_dir = log_dir or get_log_dir()

    cleanup_sessions(log_dir, get_max_sessions(), get_max_size_mb())
    session_id = create_session(log_dir)
    session_file = get_session_filepath(log_dir, session_id)

    mds_logging.set_session(session_id)
    mds_logging.set_source("gcs")

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    file_handler = SessionFileHandler(session_file, flush_every_line=get_flush_enabled())
    file_handler.setLevel(getattr(logging, get_file_log_level()))
    file_handler.setFormatter(JSONLFormatter())
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_level = get_log_level()
    console_handler.setLevel(getattr(logging, console_level))
    if get_console_format() == "json":
        console_handler.setFormatter(JSONLFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root.addHandler(console_handler)

    watcher_handler = _WatcherHandler(get_watcher(), JSONLFormatter())
    watcher_handler.setLevel(logging.DEBUG)
    root.addHandler(watcher_handler)

    _server_logger = mds_logging.get_logger("gcs")
    return session_id


# --- Convenience wrappers matching old gcs_logging.py API ---
# These allow minimal changes in app_fastapi.py during migration.

def get_logger(component: str = "gcs") -> logging.Logger:
    """Get a logger (delegates to mds_logging.get_logger)."""
    return mds_logging.get_logger(component)


def log_system_event(message: str, level: str = "INFO", component: str = "system") -> None:
    """Log a system event (replaces old gcs_logging.log_system_event)."""
    logger = mds_logging.get_logger(component)
    log_level = getattr(logging, level, logging.INFO)
    logger.log(log_level, message)


def log_system_error(message: str, component: str = "system") -> None:
    """Log a system error (replaces old gcs_logging.log_system_error)."""
    logger = mds_logging.get_logger(component)
    logger.error(message)


def log_system_warning(message: str, component: str = "system") -> None:
    """Log a system warning (replaces old gcs_logging.log_system_warning)."""
    logger = mds_logging.get_logger(component)
    logger.warning(message)


def log_system_startup(message: str, component: str = "system") -> None:
    """Log a startup event."""
    logger = mds_logging.get_logger(component)
    logger.info(message)


def log_drone_command(message: str, drone_id: int | None = None, component: str = "command") -> None:
    """Log a drone command event."""
    logger = mds_logging.get_logger(component)
    logger.info(message, extra={"mds_drone_id": drone_id})


def log_drone_telemetry(message: str, drone_id: int | None = None, component: str = "telemetry") -> None:
    """Log a telemetry event."""
    logger = mds_logging.get_logger(component)
    logger.debug(message, extra={"mds_drone_id": drone_id})


def initialize_logging(**kwargs) -> str:
    """Alias for init_server_logging (backward compat)."""
    return init_server_logging(**kwargs)
```

- [ ] **Step 11: Run all tests**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/test_mds_logging/ -v`
Expected: All tests PASS.

- [ ] **Step 12: Commit**

```bash
git add mds_logging/watcher.py mds_logging/registry.py mds_logging/cli.py mds_logging/drone.py mds_logging/server.py tests/test_mds_logging/test_watcher.py tests/test_mds_logging/test_registry.py tests/test_mds_logging/test_cli.py tests/test_mds_logging/test_integration.py
git commit -m "feat(logging): add watcher, registry, CLI, and init wrappers

LogWatcher: in-memory pub/sub for future SSE streaming
Registry: component self-registration pattern
CLI: unified --verbose/--debug/--quiet/--log-json flags
drone.py: init_drone_logging() for drone-side components
server.py: init_server_logging() + compat wrappers for gcs_logging API"
```

---

## Task 4: Migrate GCS Server Components

**Files:**
- Modify: `gcs-server/app_fastapi.py:80-82`
- Modify: `gcs-server/command.py`
- Modify: `gcs-server/telemetry.py`
- Modify: `gcs-server/git_status.py`
- Modify: `gcs-server/heartbeat.py`
- Modify: `gcs-server/utils.py`
- Modify: `gcs-server/config.py`
- Modify: `gcs-server/command_tracker.py`
- Modify: `gcs-server/origin.py`
- Modify: `gcs-server/sar/routes.py`
- Modify: `gcs-server/sar/coverage_planner.py`
- Modify: `gcs-server/sar/mission_manager.py`
- Modify: `gcs-server/sar/poi_manager.py`
- Modify: `gcs-server/sar/terrain.py`

**NOTE:** Each file migration is a separate commit for safe rollback.

- [ ] **Step 1: Migrate `gcs-server/app_fastapi.py` (Group A)**

Replace lines 80-82:
```python
# OLD:
from gcs_logging import (
    get_logger, log_system_error, log_system_warning, log_system_event
)
# NEW:
from mds_logging.server import (  # Unified logging: docs/guides/logging-system.md
    get_logger, log_system_error, log_system_warning, log_system_event,
    init_server_logging, log_system_startup,
)
```

Find the startup/lifespan section and add `init_server_logging()` call before other initialization.

Also find and replace any `initialize_logging()` call with `init_server_logging()`.

Register GCS components:
```python
from mds_logging import register_component
register_component("api", "gcs", "FastAPI HTTP/WebSocket server")
register_component("telemetry", "gcs", "Telemetry aggregation")
register_component("command", "gcs", "Command dispatch and tracking")
register_component("config", "gcs", "Configuration management")
```

- [ ] **Step 2: Run existing GCS API tests**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/ -k "gcs" -v --timeout=30 2>&1 | tail -20`
Expected: Tests pass (or at least no new failures from logging changes).

- [ ] **Step 3: Commit app_fastapi.py migration**

```bash
git add gcs-server/app_fastapi.py
git commit -m "refactor(gcs): migrate app_fastapi.py to mds_logging"
```

- [ ] **Step 4: Migrate `gcs-server/command.py` (Group A)**

Replace gcs_logging imports with mds_logging. Keep function signatures identical.

- [ ] **Step 5: Migrate `gcs-server/telemetry.py` and `gcs-server/git_status.py` (Group A)**

Replace gcs_logging imports with mds_logging.

- [ ] **Step 6: Commit Group A migrations**

```bash
git add gcs-server/command.py gcs-server/telemetry.py gcs-server/git_status.py
git commit -m "refactor(gcs): migrate command, telemetry, git_status to mds_logging"
```

- [ ] **Step 7: Migrate Group B files (bare `import logging`)**

For each file: replace `import logging` / `logging.getLogger(__name__)` with `from mds_logging import get_logger`:

Files: heartbeat.py, utils.py, config.py, command_tracker.py, origin.py (also remove `logging.basicConfig()`), and all sar/*.py files.

Pattern for each file:
```python
# OLD:
import logging
logger = logging.getLogger(__name__)
# NEW:
from mds_logging import get_logger  # Unified logging: docs/guides/logging-system.md
logger = get_logger("heartbeat")  # use descriptive component name
```

For `origin.py` specifically, also remove line 14: `logging.basicConfig(level=logging.INFO)`.

- [ ] **Step 8: Run GCS tests again**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/ -k "gcs or api or command or telemetry" -v --timeout=30 2>&1 | tail -20`
Expected: No new failures.

- [ ] **Step 9: Commit Group B migrations**

```bash
git add gcs-server/heartbeat.py gcs-server/utils.py gcs-server/config.py gcs-server/command_tracker.py gcs-server/origin.py gcs-server/sar/
git commit -m "refactor(gcs): migrate remaining GCS modules to mds_logging

Migrate heartbeat, utils, config, command_tracker, origin, and all SAR
modules from bare logging.getLogger() to mds_logging.get_logger().
Remove logging.basicConfig() from origin.py."
```

- [ ] **Step 10: Verify no gcs_logging references remain**

Run: `grep -r "from gcs_logging" --include="*.py" /opt/mavsdk_drone_show/gcs-server/`
Expected: 0 results (only the old gcs_logging.py file itself).

Run: `grep -r "import gcs_logging" --include="*.py" /opt/mavsdk_drone_show/gcs-server/`
Expected: 0 results.

---

## Task 5: Migrate Drone-Side Components

**Files:**
- Modify: `coordinator.py:24,54-78`
- Modify: `actions.py:53-54,75-94`
- Modify: `drone_show.py:99,127,2159,2196-2208`
- Modify: `smart_swarm.py:91-92,121,1298`
- Modify: `swarm_trajectory_mission.py:90,114-118,1553,1578-1583`
- Modify: `src/drone_api_server.py:32`
- Modify: `src/drone_communicator.py:5`
- Modify: `src/heartbeat_sender.py:4`
- Modify: `src/drone_setup.py:6,17`
- Modify: `src/connectivity_checker.py:1`
- Modify: `src/led_controller.py:85-86`
- Modify: `src/params.py:3,9`

- [ ] **Step 1: Migrate `coordinator.py` (Group A — own logging setup)**

Replace lines 24, 54-78:
```python
# OLD (line 24):
import logging
# OLD (lines 54-78): entire logging setup block with RotatingFileHandler

# NEW:
from mds_logging.drone import init_drone_logging  # Unified logging: docs/guides/logging-system.md
from mds_logging import get_logger, register_component
from mds_logging.cli import add_log_arguments, apply_log_args
```

In the main startup section, replace the logging setup with:
```python
register_component("coordinator", "drone", "System initialization and heartbeat")
init_drone_logging()
logger = get_logger("coordinator")
```

Remove the entire inline RotatingFileHandler setup block (lines 54-78).

- [ ] **Step 2: Test coordinator**

Run: `cd /opt/mavsdk_drone_show && python -c "from coordinator import *" 2>&1 | head -5`
Expected: No import errors.

- [ ] **Step 3: Commit coordinator migration**

```bash
git add coordinator.py
git commit -m "refactor(drone): migrate coordinator.py to mds_logging"
```

- [ ] **Step 4: Migrate `actions.py` (Group A)**

Replace lines 53-54, 75-94 with mds_logging init. Same pattern as coordinator.

- [ ] **Step 5: Commit actions migration**

```bash
git add actions.py
git commit -m "refactor(drone): migrate actions.py to mds_logging"
```

- [ ] **Step 6: Migrate `drone_show.py` (Group B — uses configure_logging)**

Replace:
- Line 127: Remove `configure_logging` from imports
- Line 2159: Replace `configure_logging("drone_show")` with `init_drone_logging()`
- Lines 2196-2208: Replace `--debug` flag handling with `add_log_arguments(parser)` and `apply_log_args(args)`

```python
# At imports:
from mds_logging.drone import init_drone_logging  # Unified logging: docs/guides/logging-system.md
from mds_logging import get_logger, register_component
from mds_logging.cli import add_log_arguments, apply_log_args

# In main():
register_component("drone_show", "drone", "Offline trajectory execution")
# Replace configure_logging("drone_show"):
init_drone_logging()
logger = get_logger("drone_show")

# In argparse section, replace --debug with:
add_log_arguments(parser)
# After parse_args:
apply_log_args(args)
```

- [ ] **Step 7: Migrate `smart_swarm.py` and `swarm_trajectory_mission.py` (Group B)**

Same pattern as drone_show.py. Replace `configure_logging()` calls with `init_drone_logging()`.

- [ ] **Step 8: Commit mission script migrations**

```bash
git add drone_show.py smart_swarm.py swarm_trajectory_mission.py
git commit -m "refactor(drone): migrate mission scripts to mds_logging

Replace configure_logging() from drone_show_src/utils.py with
init_drone_logging(). Add unified CLI flags (--verbose/--debug/--quiet)."
```

- [ ] **Step 9: Migrate Group C — bare logging modules**

For each src/ file: replace `import logging` with `from mds_logging import get_logger`:

- `src/drone_api_server.py` → `logger = get_logger("drone_api")`
- `src/drone_communicator.py` → `logger = get_logger("drone_comm")`
- `src/heartbeat_sender.py` → `logger = get_logger("heartbeat")`
- `src/drone_setup.py` → `logger = get_logger("drone_setup")`
- `src/connectivity_checker.py` → `logger = get_logger("connectivity")`
- `src/led_controller.py` → replace `print()` AND `logging.getLogger` with `logger = get_logger("led")`
- `src/params.py` → `logger = get_logger("params")`

- [ ] **Step 10: Commit Group C**

```bash
git add src/drone_api_server.py src/drone_communicator.py src/heartbeat_sender.py src/drone_setup.py src/connectivity_checker.py src/led_controller.py src/params.py
git commit -m "refactor(drone): migrate all src/ modules to mds_logging

Replace bare import logging with mds_logging.get_logger().
Replace print() statements in led_controller with proper logging."
```

- [ ] **Step 11: Run all tests**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/ -v --timeout=60 2>&1 | tail -30`
Expected: All tests pass.

---

## Task 6: Cleanup — Remove Old Code, Fix Remaining Files

**Files:**
- Modify: `quickscout_mission.py`
- Modify: `process_formation.py`
- Modify: `led_indicator.py`
- Modify: `functions/file_management.py`
- Modify: `drone_show_src/utils.py` (remove `configure_logging()` function only)
- Modify: `.gitignore`
- Delete: `gcs-server/logging_config.py`
- Delete: `gcs-server/gcs_logging.py`
- Delete: `src/logging_config.py`
- Delete: `logs/gcs.log` (from git tracking)
- Delete: `logs/drone_swarm.log` (from git tracking)

- [ ] **Step 1: Fix remaining `logging.basicConfig()` files**

For each file, remove `logging.basicConfig()` and replace with `from mds_logging import get_logger`:

- `quickscout_mission.py:30-34`
- `process_formation.py:11-24`
- `led_indicator.py:40,49,57` (also replace `print()` statements)
- `functions/file_management.py:7`
- `src/origin_cache.py:197` (`__main__` block) — remove `basicConfig`, use `get_logger`
- `tests/test_led_controller.py:6` — replace with isolated `mds_logging` test fixture

- [ ] **Step 1b: Fix `__main__` blocks in GCS files**

These files have `gcs_logging` imports inside `if __name__ == "__main__":` blocks that were not covered in Task 4:

- `gcs-server/telemetry.py:473` — replace `from gcs_logging import initialize_logging, LogLevel, DisplayMode` with `from mds_logging.server import init_server_logging`; replace `initialize_logging(LogLevel.VERBOSE, ...)` with `init_server_logging()`
- `gcs-server/command.py:480` — same pattern
- `gcs-server/git_status.py:100` — same pattern (this is the only gcs_logging reference in this file)

- [ ] **Step 2: Remove `configure_logging()` from `drone_show_src/utils.py`**

Delete lines 40-91 (the `configure_logging` function). Keep all other functions in the file (`read_hw_id`, `clamp_led_value`, `get_expected_position_from_trajectory`, etc.).

Also remove the `import sys` and `import logging` if no longer used by remaining functions. Check before removing.

- [ ] **Step 3: Update `.gitignore`**

Add to the logs section:
```
# Logs — session files and symlinks (never committed)
logs/
logs/sessions/
logs/current
*.log
*.jsonl
gcs-server/logs/
```

- [ ] **Step 4: Remove old log stubs from git tracking**

```bash
git rm --cached logs/gcs.log logs/drone_swarm.log 2>/dev/null || true
```

- [ ] **Step 5: Delete old logging files**

```bash
# Only after verifying zero references
grep -r "from gcs_logging" --include="*.py" /opt/mavsdk_drone_show/ | grep -v "gcs_logging.py"
grep -r "from logging_config import" --include="*.py" /opt/mavsdk_drone_show/ | grep -v "logging_config.py"
grep -r "from drone_show_src.utils import.*configure_logging" --include="*.py" /opt/mavsdk_drone_show/

# If all return 0 results:
git rm gcs-server/logging_config.py
git rm gcs-server/gcs_logging.py
git rm src/logging_config.py
```

- [ ] **Step 6: Run full verification checklist**

```bash
# Zero old imports (search Python files only, exclude docs/)
grep -r "from gcs_logging" --include="*.py" --exclude-dir=docs . && echo "FAIL" || echo "PASS"
grep -r "from logging_config import" --include="*.py" --exclude-dir=docs . && echo "FAIL" || echo "PASS"
grep -r "from drone_show_src.utils import.*configure_logging" --include="*.py" --exclude-dir=docs . && echo "FAIL" || echo "PASS"
grep -r "logging\.basicConfig" --include="*.py" --exclude-dir=docs . && echo "FAIL" || echo "PASS"
grep -r "DRONE_ULTRA_QUIET" --include="*.py" --exclude-dir=docs . && echo "FAIL" || echo "PASS"
grep -r "DRONE_DISPLAY_MODE" --include="*.py" --exclude-dir=docs . && echo "FAIL" || echo "PASS"

# Old files removed
test ! -f gcs-server/logging_config.py && echo "PASS" || echo "FAIL"
test ! -f gcs-server/gcs_logging.py && echo "PASS" || echo "FAIL"
test ! -f src/logging_config.py && echo "PASS" || echo "FAIL"

# New system works
python -c "from mds_logging import get_logger; l = get_logger('test'); l.info('works')" && echo "PASS" || echo "FAIL"
```

- [ ] **Step 7: Run full test suite**

Run: `cd /opt/mavsdk_drone_show && python -m pytest tests/ -v --timeout=60`
Expected: All tests PASS.

- [ ] **Step 8: Commit cleanup**

```bash
git add quickscout_mission.py process_formation.py led_indicator.py functions/file_management.py src/origin_cache.py tests/test_led_controller.py gcs-server/telemetry.py gcs-server/command.py gcs-server/git_status.py drone_show_src/utils.py .gitignore
git commit -m "refactor(logging): complete Phase 1 cleanup — remove all deprecated logging

Remove old logging systems:
- gcs-server/logging_config.py (857 lines, DroneSwarmLogger)
- gcs-server/gcs_logging.py (PYTHONPATH workaround)
- src/logging_config.py (drone-side config)
- configure_logging() from drone_show_src/utils.py
- Committed log stub files (gcs.log, drone_swarm.log)

Fix remaining logging.basicConfig() calls in quickscout_mission,
process_formation, led_indicator, file_management.
Replace print() logging in led_indicator.py.
Update .gitignore for new session directory."
```

---

## Task 7: Documentation

**Files:**
- Create: `docs/guides/logging-system.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Create `docs/guides/logging-system.md`**

Write comprehensive guide covering:
1. Architecture overview (shared contract, JSONL format)
2. Quick start (how to add logging to a new component)
3. Environment variables reference table
4. CLI flags reference
5. Session management (naming, retention, cleanup)
6. JSONL schema reference with examples
7. Console output format
8. Component registry (how to register)
9. Troubleshooting (common issues)

- [ ] **Step 2: Update `CHANGELOG.md`**

Add entry under current version describing the unified logging system.

- [ ] **Step 3: Commit docs**

```bash
git add docs/guides/logging-system.md CHANGELOG.md
git commit -m "docs: add unified logging system guide

Complete guide for the mds_logging package: architecture, quick start,
env vars, CLI flags, session management, JSONL schema, registry,
and troubleshooting."
```

---

## Final Verification

After all tasks complete, run the full verification:

```bash
# 1. All mds_logging tests pass
python -m pytest tests/test_mds_logging/ -v

# 2. All existing tests pass (no regressions)
python -m pytest tests/ -v --timeout=60

# 3. Zero old references (exclude docs/)
grep -rn "from gcs_logging\|from logging_config import\|logging\.basicConfig\|DRONE_ULTRA_QUIET\|DRONE_DISPLAY_MODE" --include="*.py" --exclude-dir=docs .

# 4. New system works end-to-end
python -c "
from mds_logging.drone import init_drone_logging
from mds_logging import get_logger, register_component
register_component('test', 'drone', 'Verification test')
sid = init_drone_logging()
logger = get_logger('test')
logger.info('Phase 1 complete')
logger.warning('This should be visible')
logger.debug('This should be in file only')
print(f'Session: {sid}')
"
```
