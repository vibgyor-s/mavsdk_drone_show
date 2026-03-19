# Unified Logging System — Design Specification

**Date:** 2026-03-19
**Status:** Approved
**Branch:** main-candidate
**Approach:** Federated Logging with Shared Contract (B+)

---

## 1. Problem Statement

The MAVSDK Drone Show (MDS) project has fragmented logging across its components:

- **Two separate logging systems**: `src/logging_config.py` (drone-side) and `gcs-server/logging_config.py` (GCS) with different env var prefixes (`MDS_*` vs `DRONE_*`)
- **No log aggregation**: drone logs stay on each drone, no forwarding to GCS
- **Inconsistent rotation**: some rotate, some overwrite, some don't rotate at all
- **Mixed patterns**: coordinator, actions each roll their own `RotatingFileHandler` setup
- **No structured logging**: all text-based, no JSON for machine parsing
- **No frontend log viewer**: no monitoring UI, no real-time log streaming
- **No WebSocket/SSE for logs**: backend has WebSocket for telemetry but not for logs
- **Print statements**: LED code, startup banners bypass logging entirely
- **No error boundaries** in React for catching frontend crashes
- **Inconsistent CLI flags**: some scripts support `--verbose`/`--debug`, others don't
- **Environment variable naming**: `DRONE_*` vs `MDS_LOG_*` prefix inconsistency

## 2. Goals

1. **Unified format**: JSONL across all components (drone, GCS, infra, frontend)
2. **Session-based retention**: logs organized by mission/session, configurable limits
3. **Real-time streaming**: SSE-based live log viewing for development and operations
4. **Historical review**: post-mission briefing with search, filter, export
5. **Pull-based aggregation**: GCS fetches drone logs on-demand (bandwidth-safe)
6. **Modular & extensible**: registry pattern, adding a log source = one line of code
7. **Two-mode UI**: Operations mode (field operators) + Developer mode (debugging)
8. **Zero deprecated leftovers**: no old code, docs, or references survive migration
9. **Scalable**: 1 to 200+ drones, any network (WiFi, 4G, VPN, SITL)
10. **Self-contained**: no external infrastructure (no Grafana, Loki, ELK)

## 3. Non-Goals

- Centralized log aggregation database (overkill for current scale)
- Constant push-based log streaming from drones (bandwidth risk — but see Section 11.7 for optional periodic pull)
- Custom log shipping agents/sidecars (operational complexity)
- Integration with external monitoring platforms (can be added later via JSONL export)
- PX4 onboard ULG flight log management (binary flight data, large files, requires MAVSDK `log_files` plugin — separate feature, planned for a dedicated future phase)

## 4. Architecture

### 4.1 Approach: Federated Logging with Shared Contract (B+)

A shared **contract module** (`mds_logging/schema.py`) defines the JSONL schema, session naming, environment variables, and rotation rules as actual Python code. Drone-side and GCS each have thin wrappers that import from the contract.

**Filesystem location:** `/opt/mavsdk_drone_show/mds_logging/` (top-level package in the repo root).

**Import path:** `from mds_logging import get_logger`. Both drone-side scripts (which run from the repo root) and GCS scripts (which add `BASE_DIR` to `sys.path` at `gcs-server/app_fastapi.py:51`) can import this package. `pyproject.toml` must be updated to include `mds_logging*` in `setuptools.packages.find`.

```
mds_logging/             ← shared contract + wrappers
├── __init__.py          ← public API: get_logger(), init_logging()
├── schema.py            ← JSONL schema, constants, enums (source of truth)
├── formatter.py         ← JSONLFormatter + ConsoleFormatter
├── session.py           ← Session lifecycle (create, rotate, cleanup)
├── handlers.py          ← SessionRotatingFileHandler, flush-on-write
├── watcher.py           ← In-memory pub/sub for real-time SSE
├── registry.py          ← Component self-registration
├── cli.py               ← Shared CLI argument parser (--verbose, --debug, etc.)
├── constants.py         ← Env var names, defaults, limits
├── drone.py             ← Drone-side convenience wrapper
└── server.py            ← GCS-side convenience wrapper
```

### 4.2 Data Flow

```
┌─────────┐         ┌─────────┐         ┌─────────┐
│ Drone 1 │         │ Drone 2 │         │ Drone N │
│ /api/logs│         │ /api/logs│         │ /api/logs│
└────▲────┘         └────▲────┘         └────▲────┘
     │ pull on-demand    │                   │
     └───────────────────┼───────────────────┘
                         │
                    ┌────┴────┐
                    │   GCS   │
                    │ FastAPI │──── SSE ──── React Dashboard
                    │/api/logs│
                    └─────────┘
```

- Drones never push logs unless GCS requests them
- GCS is the single gateway (UI never connects directly to drones)
- SSE for real-time streaming (unidirectional, auto-reconnect, proxy-friendly)

## 5. JSONL Schema

Every log line across every component follows this schema:

```json
{
  "ts": "2026-03-19T14:32:01.123Z",
  "level": "INFO",
  "component": "coordinator",
  "source": "drone",
  "drone_id": 3,
  "session_id": "s_20260319_143000",
  "msg": "Armed successfully",
  "extra": {"flight_mode": "OFFBOARD", "battery": 12.4}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ts` | ISO 8601 UTC string | Yes | Timestamp with milliseconds |
| `level` | string | Yes | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `component` | string | Yes | Source component name (registry-based) |
| `source` | string | Yes | `"drone"`, `"gcs"`, `"frontend"`, `"infra"` |
| `drone_id` | int or null | Yes | Hardware ID (null for GCS/infra/frontend logs) |
| `session_id` | string | Yes | Links log to a mission/session |
| `msg` | string | Yes | Human-readable message |
| `extra` | object or null | No | Structured context data (varies by component) |

## 6. Session Management

- **Session** = one logical run (mission execution, server startup-to-shutdown, SITL test)
- **Naming**: `s_{YYYYMMDD}_{HHMMSS}` (e.g., `s_20260319_143000`)
- **Uniqueness**: Session IDs are unique per device. When aggregating across drones, the tuple `(drone_id, session_id)` provides global uniqueness. If two sessions start in the same second on the same device (unlikely), a `_2` suffix is appended.
- **Storage**: `logs/sessions/{session_id}.jsonl` (one file per session)
- **Coexistence**: `logs/sessions/` is a new subdirectory that does not conflict with legacy `logs/*.log` files during the transition period. Legacy `.log` files are cleaned up in the final migration step (Phase 1, step 1.14).
- **Symlink**: `logs/current` → active session file
- **Retention** (configurable via env vars):
  - `MDS_LOG_MAX_SESSIONS=10` — keep last N sessions
  - `MDS_LOG_MAX_SIZE_MB=100` (drone) / `500` (GCS) — hard cap
  - Oldest sessions pruned first when either limit is hit
  - Cleanup runs at session start

### Log Directory Layout

```
logs/
├── sessions/
│   ├── s_20260319_143000.jsonl    ← most recent
│   ├── s_20260319_120000.jsonl
│   ├── s_20260318_090000.jsonl
│   └── ...                        ← max 10 files, max 100MB
├── current -> sessions/s_20260319_143000.jsonl
└── .gitkeep
```

## 7. Environment Variables

Unified `MDS_LOG_*` prefix across all components:

| Variable | Default | Description |
|----------|---------|-------------|
| `MDS_LOG_LEVEL` | `INFO` | Console output level |
| `MDS_LOG_FILE_LEVEL` | `DEBUG` | File output level |
| `MDS_LOG_MAX_SESSIONS` | `10` | Max sessions to retain |
| `MDS_LOG_MAX_SIZE_MB` | `100` | Max total log size in MB |
| `MDS_LOG_DIR` | `logs/sessions` | Log directory path |
| `MDS_LOG_CONSOLE_FORMAT` | `text` | Console format: `text` (colored) or `json` |
| `MDS_LOG_FLUSH` | `true` | Flush after every write (crash safety) |

Old env vars (`DRONE_LOG_LEVEL`, `DRONE_ULTRA_QUIET`, etc.) supported via deprecation shim for one release cycle.

## 8. Console Output Format

For terminal/SSH/journal, colored human-readable text:

```
14:32:01.123 INFO  [coordinator] Armed successfully (flight_mode=OFFBOARD)
14:32:01.456 WARN  [telemetry]  GPS HDOP degraded (hdop=3.2)
14:32:01.789 ERROR [drone_api]  Command rejected: not armed
```

- Color-coded by level (green=INFO, yellow=WARN, red=ERROR)
- Component name in brackets
- `extra` fields appended as key=value pairs

## 9. CLI Flags

All Python entry points get unified flags via `mds_logging/cli.py`:

| Flag | Effect |
|------|--------|
| `--verbose` | Sets `MDS_LOG_LEVEL=DEBUG` for console |
| `--quiet` | Sets `MDS_LOG_LEVEL=WARNING` for console |
| `--log-dir PATH` | Override `MDS_LOG_DIR` |
| `--log-json` | Sets `MDS_LOG_CONSOLE_FORMAT=json` |

## 10. Component Registry

Self-registration pattern — no hardcoded list:

```python
# Any component at startup:
from mds_logging import register_component
register_component("coordinator", "drone", "System initialization and heartbeat")
```

GCS exposes `GET /api/logs/sources` which returns the registry. The frontend auto-discovers available sources.

Adding a new component = one `register_component()` call.
Removing a component = delete that call.

## 11. Log Aggregation API

### 11.1 Drone-Side Endpoints (added to `drone_api_server.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/logs/sessions` | GET | List available sessions |
| `GET /api/logs/sessions/{session_id}` | GET | Download session JSONL (supports query filters) |
| `GET /api/logs/stream` | GET (SSE) | Stream current session in real-time |

Query parameters for filtering: `?level=`, `?component=`, `?since=`, `?limit=`

### 11.2 GCS-Side Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/logs/sources` | GET | List all registered components + connected drones |
| `GET /api/logs/sessions` | GET | List GCS sessions |
| `GET /api/logs/sessions/{session_id}` | GET | Retrieve GCS session logs |
| `GET /api/logs/stream` | GET (SSE) | Real-time GCS log stream |
| `GET /api/logs/drone/{drone_id}/stream` | GET (SSE) | Proxy real-time stream from drone |
| `GET /api/logs/drone/{drone_id}/sessions` | GET | List sessions on drone |
| `GET /api/logs/drone/{drone_id}/sessions/{session_id}` | GET | Fetch session from drone |
| `POST /api/logs/export` | POST | Export sessions as JSONL or ZIP |
| `POST /api/logs/frontend` | POST | Receive frontend error reports |

### 11.3 Bandwidth Protection

| Protection | Mechanism |
|------------|-----------|
| No auto-push | Drones never send logs unless GCS asks |
| Level filtering | Default aggregation only pulls WARNING+ from drones |
| Throttling | SSE streams capped at 10 lines/sec at INFO+ level; DEBUG streams allow up to 50 lines/sec (configurable via `?throttle=` query param) |
| Pagination | Historical queries paginated with `?limit=` and `?offset=` |
| Timeout | Drone log fetch times out after 5 seconds |
| Circuit breaker | Unreachable drone skipped immediately |
| No broadcast pull | UI fetches from one drone at a time |
| Compression | JSONL responses use gzip encoding |

### 11.4 Real-Time Streaming (SSE)

In-memory pub/sub via `mds_logging/watcher.py`:

- `LogWatcher.publish(entry)` — called by log handler on every write
- `LogWatcher.subscribe(**filters)` — async generator for SSE endpoint
- Buffer of last 100 entries for new subscribers (immediate context)
- Zero subscribers = zero overhead (no buffer writes if nobody listening)

### 11.5 Offline Handling

- Unreachable drone: session list returns cached last-known (if available)
- SSE proxy: emits `{"event": "error", "data": {"drone_id": N, "msg": "unreachable"}}`
- UI shows "offline" badge immediately, no spinner or hanging request
- Logs accumulate locally on drone, available when connection restores

### 11.6 Security

Log endpoints follow the same trust model as existing drone/GCS API endpoints — they are expected to operate on a private network (direct WiFi, Netbird VPN, or local SITL). Network-level access control is the security boundary. No application-level authentication is added in this iteration, consistent with the existing API surface. If authentication is added to the main API in the future, log endpoints inherit the same middleware.

### 11.7 Periodic Background Pull (Optional Safety Net)

**Problem:** If a drone crashes or loses connectivity mid-mission, its logs are lost until (if ever) it comes back online. With pure on-demand pull, there's no safety net.

**Solution:** An optional background task on GCS that periodically pulls recent WARNING+ logs from all connected drones and stores them locally on GCS. **Disabled by default** — only enabled when bandwidth allows (test missions, good WiFi, SITL).

**Configuration:**

| Variable | Default | Description |
|----------|---------|-------------|
| `MDS_LOG_BACKGROUND_PULL` | `false` | Enable periodic log collection from drones |
| `MDS_LOG_PULL_INTERVAL_SEC` | `30` | How often to pull (seconds) |
| `MDS_LOG_PULL_LEVEL` | `WARNING` | Minimum level to collect (WARNING+ by default) |
| `MDS_LOG_PULL_MAX_DRONES` | `10` | Max concurrent drone pulls (prevents network flood) |

**Behavior:**
- Runs as an async background task in GCS FastAPI (similar to existing telemetry polling)
- For each drone, fetches `GET /api/logs/stream?since={last_pull_timestamp}&level=WARNING`
- Stores collected entries in GCS-side session files under `logs/sessions/drone_{id}/`
- Respects circuit breaker: skips unreachable drones immediately
- Sequential drone polling with concurrency cap (`MDS_LOG_PULL_MAX_DRONES`)
- If disabled (default), zero overhead — task does not start

**UI toggle:** The Log Viewer UI includes a toggle in the toolbar: "Background Collection: OFF/ON" which maps to `POST /api/logs/config` to change the setting at runtime without restart.

**Implementation:** Added in Phase 2 (aggregation layer), after core endpoints are working.

## 12. Frontend Log Viewer

### 12.1 Navigation

New sidebar section added in `src/components/SidebarMenu.js`:

```
System
  └── Log Viewer          (route: /logs)
```

The sidebar menu file and `App.js` route definitions must both be updated.

### 12.2 Two-Mode UI

**Operations Mode** (default):
- System health bar: GCS status, drone count, error count, session duration
- Source filter: GCS Server, All Drones, individual drones
- Level filter: default WARNING+ (errors and warnings only)
- Live event feed with auto-scroll and pause button
- Color-coded rows: red=ERROR, amber=WARNING, blue=INFO
- Clean, minimal — field operators see only what matters

**Developer Mode**:
- Full component tree in left sidebar (auto-populated from registry)
- All log levels visible (DEBUG through CRITICAL)
- Search with optional regex
- Multi-filter: level + component + drone + session
- Virtual scroll via MUI DataGrid (handles 100K+ rows)
- Click any row to expand raw JSON
- Session selector: current live or historical sessions
- Export: download filtered results as JSONL or CSV

### 12.3 Components

```
src/
├── pages/
│   └── LogViewer.js
├── components/
│   └── logs/
│       ├── LogViewerToolbar.js
│       ├── LogHealthBar.js
│       ├── LogSourceTree.js
│       ├── LogTable.js
│       ├── LogRowDetail.js
│       ├── LogLiveIndicator.js
│       ├── LogSessionSelector.js
│       └── LogExportDialog.js
├── hooks/
│   └── useLogStream.js
├── services/
│   └── logService.js
└── styles/
    └── LogViewer.css
```

### 12.4 `useLogStream` Hook

- Connects to SSE endpoint via `EventSource`
- **200ms batching** — prevents React re-render per log line
- **`MAX_LOG_LINES = 5000`** — ring buffer in UI, prevents memory bloat
- **Auto-reconnect** — `EventSource` built-in behavior
- **Server-side filtering** — query params filter before data leaves server

### 12.5 Historical Session View

- Session dropdown selects past sessions
- SSE disconnects; data fetched via `GET /api/logs/sessions/{id}`
- MUI DataGrid with pagination for large sessions
- Same search, filter, export as live view

### 12.6 Export

- Formats: `.jsonl` (machine) or `.csv` (spreadsheet)
- Scope: current filtered view or full session
- Multi-session export as `.zip`
- Filename: `mds_logs_{session_id}_{timestamp}.{ext}`

### 12.7 Error Boundary

React `ErrorBoundary` component wraps `App.js`:
- Catches render errors
- POSTs to `POST /api/logs/frontend` on GCS
- Error appears in log viewer under `frontend` source

### 12.8 UI/UX Standards

| Requirement | Implementation |
|-------------|----------------|
| Responsive | MUI Grid breakpoints, tablet-friendly (1024px+) |
| Cross-platform | Standard React + MUI |
| Not overwhelming | Operations mode default, WARNING+ only |
| Intuitive | Familiar log viewer UX (browser DevTools style) |
| Fast | Virtual scroll, 200ms batching, server-side filtering |
| Accessible | ARIA labels, keyboard nav, color + icon (not color alone) |
| Dark/Light | Respects existing ThemeContext |
| No data loss | Pause freezes view, data continues buffering |

## 13. Backend Migration Plan

### 13.1 Strategy

Migrate one file at a time, test after each, never break the running system.

### 13.2 GCS Server Migration

**Group A — Files importing `from gcs_logging import ...` (major migration):**

These files use the custom `DroneSwarmLogger` system and need their imports replaced:

1. `gcs-server/app_fastapi.py` — imports `get_logger`, `log_system_error`, `log_system_warning`, `log_system_event` from `gcs_logging` → replace with `from mds_logging.server import ...`
2. `gcs-server/command.py` — imports `get_logger`, `log_drone_command`, `log_system_error`, `log_system_warning` from `gcs_logging` → replace with `from mds_logging import get_logger`
3. `gcs-server/telemetry.py` — uses `get_logger()` from `gcs_logging` → replace
4. `gcs-server/git_status.py` — uses `gcs_logging` in `__main__` block → replace

**Group B — Files using bare `import logging` (consistency migration):**

These files use standard `logging.getLogger(__name__)` and should adopt `mds_logging` for unified format:

5. `gcs-server/heartbeat.py` — `logging.getLogger(__name__)` → `from mds_logging import get_logger`
6. `gcs-server/utils.py` — bare `logging.info/error` calls → `from mds_logging import get_logger`
7. `gcs-server/config.py` — `logging.getLogger(__name__)` → same
8. `gcs-server/command_tracker.py` — `logging.getLogger(__name__)` → same
9. `gcs-server/origin.py` — `logging.basicConfig()` + `logging.getLogger(__name__)` → remove `basicConfig`, use `mds_logging`
10. `gcs-server/sar/routes.py` — `logging.getLogger(__name__)` → same
11. `gcs-server/sar/coverage_planner.py` — same
12. `gcs-server/sar/mission_manager.py` — same
13. `gcs-server/sar/poi_manager.py` — same
14. `gcs-server/sar/terrain.py` — same

### 13.3 Drone Side Migration

**Group A — Files with their own logging setup (replace entire setup):**

1. `coordinator.py` — has own `RotatingFileHandler` setup (lines 54-78). Replace with `from mds_logging.drone import init_drone_logging`. Remove custom handler setup.
2. `actions.py` — has own `RotatingFileHandler` setup (lines 76-94). Same replacement.

**Group B — Files importing `configure_logging` from `drone_show_src/utils.py` (third logging system):**

These import and call `configure_logging(mission_type)` from `drone_show_src/utils.py`, which creates a `FileHandler` in overwrite mode. Each call site must be replaced with `init_drone_logging()`:

3. `drone_show.py` — imports at line 127, calls at line 2159 → replace with `init_drone_logging()`
4. `swarm_trajectory_mission.py` — imports at line 115, calls at line 1553 → replace
5. `smart_swarm.py` — imports at line 121, calls at line 1298 → replace

**Group C — Files using bare `import logging` (consistency migration):**

6. `src/drone_api_server.py` — bare `logging.*()` → `from mds_logging import get_logger`
7. `src/drone_communicator.py` — bare `logging.*()` → same
8. `src/heartbeat_sender.py` — bare `logging.*()` → same
9. `src/drone_setup.py` — `logging.getLogger(__name__)` → same
10. `src/connectivity_checker.py` — bare `logging` → same
11. `src/led_controller.py` — `logging.getLogger(__name__)` + `print()` statements → replace both with `get_logger()`

### 13.4 Cleanup — Additional `logging.basicConfig()` Sites

These files also use `logging.basicConfig()` which conflicts with `mds_logging.init_logging()`:

- `gcs-server/origin.py` (line 14) — remove `basicConfig`, use `mds_logging`
- `quickscout_mission.py` — remove `basicConfig`, use `mds_logging`
- `process_formation.py` (line 16) — remove `basicConfig`, use `mds_logging`
- `functions/file_management.py` (line 7) — remove `basicConfig`, use `mds_logging`
- `src/origin_cache.py` (line 197, `__main__` block) — remove `basicConfig`, use `mds_logging`
- `led_indicator.py` — replace `print()` and `logging.basicConfig()` with `get_logger()`
- `tests/test_led_controller.py` (line 6) — replace with test fixture that uses isolated `mds_logging` setup (see Section 15)

### 13.5 Shell Script Logging

Shell script JSONL logging is **deferred to a later iteration**. The current shell logging (`log_info`, `log_warn`, `log_error` in `tools/mds_init_lib/common.sh`) remains as-is. Rationale: shell scripts run infrequently (installation/setup), their logs go to syslog which is already queryable via `journalctl`, and adding JSONL to bash is fragile. If needed later, a `mds_log()` bash function can be added to `common.sh`.

### 13.6 DroneSwarmLogger Dashboard Deprecation

`gcs-server/logging_config.py` contains 857 lines including active runtime logic beyond logging:
- `DroneSwarmLogger` class with background threads for dashboard rendering
- Health monitoring and system stats aggregation
- Drone status tracking with color-coded terminal output
- Display modes (DASHBOARD, STREAM, HYBRID)

**Decision:** These features are **deprecated and replaced by the React Log Viewer (Phase 3)**. Terminal output reverts to the simpler `ConsoleFormatter` from `mds_logging/formatter.py`. The `DRONE_ULTRA_QUIET` / `DRONE_DISPLAY_MODE` behaviors are superseded by `MDS_LOG_LEVEL` (e.g., `MDS_LOG_LEVEL=WARNING` replaces `ULTRA_QUIET`).

### 13.7 Files to Delete (after verification)

| File | Replaced By | Note |
|------|-------------|------|
| `gcs-server/logging_config.py` | `mds_logging/server.py` | 857-line file including DroneSwarmLogger — fully replaced |
| `gcs-server/gcs_logging.py` | `mds_logging/server.py` | PYTHONPATH workaround no longer needed |
| `src/logging_config.py` | `mds_logging/drone.py` | Drone-side logging config |
| `logs/gcs.log` (committed stub) | `.gitignore` | Remove from git tracking |
| `logs/drone_swarm.log` (committed stub) | `.gitignore` | Remove from git tracking |

**Note:** `drone_show_src/utils.py` is NOT deleted — it contains other utilities (`read_hw_id`, `clamp_led_value`, etc.). Only the `configure_logging()` function is removed from it.

Deletion rule: no file is deleted until grep confirms zero references and all tests pass.

### 13.8 Environment Variable Migration

| Old | New | Action |
|-----|-----|--------|
| `DRONE_LOG_LEVEL` | `MDS_LOG_LEVEL` | Shim + deprecation warning |
| `DRONE_ULTRA_QUIET` | `MDS_LOG_LEVEL=WARNING` | Remove (superseded by log level) |
| `DRONE_DISPLAY_MODE` | `MDS_LOG_CONSOLE_FORMAT` | Remove (terminal dashboard replaced by React UI) |
| `DRONE_LOG_FILE` | `MDS_LOG_DIR` | Shim + deprecation warning |

## 14. Documentation Plan

| Document | Action | Content |
|----------|--------|---------|
| `docs/guides/logging-system.md` | CREATE | Full guide: architecture, env vars, CLI flags, adding sources, JSONL reference, session management, log viewer UI, troubleshooting |
| `docs/apis/gcs-api-server.md` | UPDATE | Add all `/api/logs/*` endpoints |
| `docs/apis/drone-api-server.md` | UPDATE | Add drone-side `/api/logs/*` endpoints |
| `docs/guides/sitl-comprehensive.md` | UPDATE | Replace old logging references |
| `docs/guides/gcs-setup.md` | UPDATE | Update env vars, mention log viewer |
| `docs/guides/mds-init-setup.md` | UPDATE | Update logging section |
| `CHANGELOG.md` | UPDATE | Document logging overhaul |

## 15. Test Plan

### 15.1 Unit Tests (`tests/test_mds_logging/`)

| Test File | Coverage |
|-----------|----------|
| `test_schema.py` | JSONL format validation |
| `test_session.py` | Session lifecycle, rotation, cleanup |
| `test_formatter.py` | Console + JSONL formatter output |
| `test_handlers.py` | File handler, flush behavior |
| `test_registry.py` | Component registration |
| `test_watcher.py` | Pub/sub, buffer, filtering |
| `test_cli.py` | CLI flag parsing |
| `test_constants.py` | Env var reading, defaults, deprecation shim |

### 15.2 Integration Tests

| Test File | Coverage |
|-----------|----------|
| `test_migration_gcs.py` | GCS components produce valid JSONL |
| `test_migration_drone.py` | Drone components produce valid JSONL |
| `test_log_api_drone.py` | Drone-side `/api/logs/*` endpoints |
| `test_log_api_gcs.py` | GCS-side `/api/logs/*` endpoints |
| `test_sse_stream.py` | SSE streaming, filtering, throttle |
| `test_proxy.py` | GCS-to-drone proxy, offline handling |
| `test_bandwidth.py` | Throttle limits, timeout, circuit breaker |

### 15.3 Frontend Tests

| Test File | Coverage |
|-----------|----------|
| `LogViewer.test.js` | Page renders, mode toggle |
| `LogTable.test.js` | Virtual scroll, row expansion |
| `LogViewerToolbar.test.js` | Filter changes trigger re-fetch |
| `useLogStream.test.js` | SSE connect/disconnect/reconnect/batching |
| `logService.test.js` | API calls |
| `ErrorBoundary.test.js` | Catches errors, reports to backend |

### 15.4 Verification Checklist (post-migration)

```bash
# Zero old imports (each should return 0 results)
grep -r "from gcs_logging" --include="*.py" .
grep -r "from logging_config import" --include="*.py" .
grep -r "from drone_show_src.utils import.*configure_logging" --include="*.py" .
grep -r "from drone_show_src\.utils import.*configure_logging" --include="*.py" .
grep -r "logging\.basicConfig" --include="*.py" .   # except test fixtures if isolated
grep -r "DRONE_ULTRA_QUIET" .                        # expect: 0
grep -r "DRONE_DISPLAY_MODE" .                       # expect: 0

# Deprecation shims only (allowed temporarily)
grep -r "DRONE_LOG_LEVEL" .          # only in mds_logging/constants.py shim
grep -r "DRONE_LOG_FILE" .           # only in mds_logging/constants.py shim

# Old files removed
test ! -f gcs-server/logging_config.py
test ! -f gcs-server/gcs_logging.py
test ! -f src/logging_config.py
test ! -f logs/gcs.log
test ! -f logs/drone_swarm.log

# configure_logging removed from drone_show_src/utils.py but file still exists
python -c "from drone_show_src.utils import configure_logging" 2>&1 | grep -q "cannot import"

# All tests pass
pytest tests/ -v

# New system works
python -c "from mds_logging import get_logger; l = get_logger('test'); l.info('works')"
```

## 16. Implementation Phases

### Phase 1: Foundation (mds_logging package + backend migration)

Steps 1.1-1.17 — create package, migrate all components, delete old code, update docs, verify.

### Phase 2: Aggregation (REST + SSE endpoints + drone-GCS pipeline)

Steps 2.1-2.12 — add log API endpoints to both drone and GCS, implement SSE, bandwidth controls, test, document.

### Phase 3: Frontend (React Log Viewer + Error Boundary)

Steps 3.1-3.18 — build all components, integrate SSE hook, Operations + Developer modes, export, error boundary, docs.

### Rollback Plan

- Phase 1: each file migration is a separate commit → `git revert` specific commit
- Phase 2: new endpoints are additive → remove routes, no existing behavior affected
- Phase 3: new page is additive → remove route and sidebar entry

## 17. Final End-to-End Verification

1. Start GCS → verify session JSONL, `/api/logs/sources`, SSE stream
2. Start drone/SITL → verify drone JSONL, drone `/api/logs/*`, GCS proxy
3. Open dashboard `/logs` → verify Operations mode, live feed, drone selection
4. Switch to Developer mode → verify search, filter, historical session, export
5. Stop a drone → verify "offline" badge, no UI freeze
6. Trigger React error → verify appears in log viewer
7. Enable background pull → verify logs accumulate on GCS from drones
8. Disable background pull → verify zero overhead
9. Run full grep verification → zero old references
10. Run full test suite → 100% pass

## 18. Future Phase: PX4 Flight Log Management

**Not in scope for this spec**, but planned for a dedicated future phase:

- **PX4 ULG flight logs** stored on drone SD cards are binary flight data files (10-100MB each)
- MAVSDK provides a `log_files` plugin to list and download these logs
- A future "Flight Logs" tab in the Log Viewer could show available ULG files per drone, with download/delete capabilities
- Requires: robust download with progress bar, resume on disconnect, cancel support, size warnings
- This is fundamentally different from application JSONL logs (binary vs text, large vs small, flight data vs operational logs) and warrants its own design spec
- The modular Log Viewer UI is designed to accommodate this as a future tab without architectural changes
