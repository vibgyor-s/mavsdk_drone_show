# QuickScout SAR Module - Code Review Report

**Date:** 2026-02-24
**Branch:** `main-candidate`
**Commits:** `72035d5a` (implementation), `2b3068c6` (docs/changelog)
**Author:** AI-assisted implementation (Claude Opus 4.6)
**Status:** Pre-review, NOT flight-tested

---

## 1. What Was Implemented

A complete SAR/Reconnaissance module (mission mode `QUICKSCOUT = 5`) enabling multi-drone cooperative area survey. The implementation spans:

- **7 new backend Python modules** in `gcs-server/sar/`
- **1 drone-side executor** (`quickscout_mission.py`)
- **2 modified drone-side files** (`drone_communicator.py`, `drone_setup.py`)
- **1 modified server file** (`app_fastapi.py` — router registration)
- **12 new frontend files** (React page, 9 components, API service, CSS)
- **2 modified frontend files** (`App.js` route, `SidebarMenu.js` menu item)
- **3 test files** (50 tests, all passing)
- **1 doc file** + CHANGELOG v5.0 entry

### File Inventory (31 files total)

| Category | Files |
|----------|-------|
| Backend models | `sar/schemas.py`, `src/enums.py` |
| Algorithm | `sar/coverage_planner.py`, `sar/terrain.py` |
| Mission management | `sar/mission_manager.py`, `sar/poi_manager.py` |
| API routes | `sar/routes.py`, `gcs-server/app_fastapi.py` (modified) |
| Drone-side | `quickscout_mission.py`, `src/drone_communicator.py` (modified), `src/drone_setup.py` (modified) |
| Frontend page | `pages/QuickScoutPage.js` |
| Frontend components | 9 files in `components/sar/` |
| Frontend service | `services/sarApiService.js` |
| Frontend styling | `styles/QuickScout.css` |
| Frontend integration | `App.js` (modified), `SidebarMenu.js` (modified) |
| Tests | `test_sar_schemas.py`, `test_sar_coverage_planner.py`, `test_sar_api.py` |
| Docs | `docs/quickscout.md`, `CHANGELOG.md` |

---

## 2. Deviations From Plan

### 2.1 Intentional Deviations
- **No `docs/features/` subdirectory** — existing docs are flat in `docs/`, so `docs/quickscout.md` follows convention.
- **Frontend build skipped** — resource-constrained environment; frontend was not `npm run build` verified.
- **`QUICKSCOUT_IMPLEMENTATION_PROMPT.md`** was accidentally committed in the first commit (60KB raw prompt file). Removed in the second commit and added to `.gitignore`.

### 2.2 Deviations Due to Network Disconnections
The implementation session experienced **2 network disconnections**. Work was recovered by verifying file state on disk before continuing. No work was lost, but some files may have been written in slightly different sessions which could affect code consistency.

---

## 3. Known Issues - CRITICAL (Must Fix Before Any Testing)

### 3.1 [C1] Command Injection via `action.split()` on Drone Side
**Files:** `src/drone_setup.py:201`, `src/drone_communicator.py:240-243`

The `execute_mission_script()` method splits a string argument with `.split()`. The `mission_id`, `hw_id`, and `return_behavior` values come directly from the GCS network command with **no sanitization**. If any field contains spaces or special characters, extra arguments are injected into the subprocess command.

**Note:** This is a **pre-existing pattern** in `drone_setup.py` — all mission scripts use `action.split()`. QuickScout inherited this pattern. However, QuickScout is the first mission type where the argument string contains multiple attacker-influenced fields (mission_id, return_behavior).

**Recommendation:** Refactor `execute_mission_script` to accept a list of arguments instead of a string, or validate all fields against `^[a-zA-Z0-9_-]+$` before use.

### 3.2 [C2] Unsanitized File Path in `/tmp`
**File:** `src/drone_communicator.py:240`

```python
waypoints_file = f"/tmp/quickscout_{hw_id}_{mission_id}.json"
```

No path sanitization on `hw_id` or `mission_id`. Path traversal possible if either contains `../`. Symlink attacks possible since the path is predictable.

**Recommendation:** Validate fields, use `os.path.basename()`, or use `tempfile.mkstemp()`.

### 3.3 [C3] Dynamic Attributes on DroneConfig Bypass Property System
**File:** `src/drone_communicator.py:246-248`

QuickScout stores state (`quickscout_mission_id`, `quickscout_waypoints_file`, `quickscout_return_behavior`) as ad-hoc instance attributes on `DroneConfig`. These fields are **not declared** in `DroneConfig`, `DroneConfigData`, or `DroneState`. They work only because Python allows dynamic attribute assignment, but they bypass the class's property/state architecture entirely.

**Recommendation:** Add these fields to `DroneState` as proper mutable fields, or use a separate state dict.

### 3.4 [C4] Mission Launches Even When All Drone Commands Fail
**File:** `gcs-server/sar/routes.py:148-157`

`manager.start_mission()` is called unconditionally after the send loop, even if every `send_commands_to_selected()` call threw an exception. The API returns `{"success": True}` while zero drones received commands. The operator sees success; no drones fly.

Also: `return_behavior` is **hardcoded to `'return_home'`** on line 143, ignoring the user's selection.

**Recommendation:** Track send failures, only start mission if at least one drone succeeded, pass actual `return_behavior` from the plan.

### 3.5 [C5] React Rules of Hooks Violations (Frontend)
**Files:** `SearchAreaDrawer.js:54-56`, `CoveragePreview.js:23-26`

Both files call hooks (`useControl`, `useMemo`) **after conditional early returns**. This violates React's Rules of Hooks and will crash in React Strict Mode when conditions change between renders.

**Recommendation:** Move early returns after all hook calls, or split into wrapper + inner components.

### 3.6 [C6] Map Viewport Control is Non-Functional
**File:** `QuickScoutPage.js:78,248`

`initialViewState={viewport}` is a one-time initialization prop in react-map-gl v7. All subsequent `setViewport()` calls (center on drone, center on POI) update React state but have **zero effect on the map**. Every "center map" feature is broken.

**Recommendation:** Use a map ref with `mapRef.current.flyTo()` or switch to controlled mode with `viewState` + `onMove`.

---

## 4. Known Issues - HIGH (Should Fix Before Real Operations)

### 4.1 [H1] Terrain Following Blocks the Async Event Loop
**Files:** `sar/routes.py:81-87`, `sar/terrain.py:23-46`

`batch_get_elevations` makes synchronous `requests.get()` calls (one per waypoint) inside an async FastAPI handler. This blocks the entire event loop for the duration — potentially minutes for large surveys. All other API endpoints (telemetry, heartbeat) are unresponsive during this time.

### 4.2 [H2] Drone-Side Ignores Trigger Time
**File:** `src/drone_setup.py:632-645`

`_execute_quickscout` does **not** call `_check_mission_conditions()`, unlike every other mission handler. The drone launches immediately when the handler runs, ignoring the `trigger_time` set by GCS. Multi-drone synchronized launch is broken.

### 4.3 [H3] No Timeout on MAVSDK Connection/GPS Wait Loops
**File:** `quickscout_mission.py:109-118`

Two `async for` loops (connection state, GPS health) have **no timeout**. If the drone never connects or never gets GPS fix, the script hangs forever. The process is never cleaned up, blocking future missions.

### 4.4 [H4] Camera Actions Never Fire
**File:** `quickscout_mission.py:146-152`

`START_PHOTO_INTERVAL` is conditioned on `is_survey and i == 0`, but waypoint index 0 is always a transit waypoint (`is_survey_leg=False`). The camera start condition is never met. The entire SAR photography capability is non-functional.

### 4.5 [H5] Pause/Resume/Abort Don't Actually Command Drones
**File:** `gcs-server/sar/routes.py:171-192`

These endpoints only update in-memory state on the GCS. No commands are sent to the drones. A "paused" mission is still flying. An "aborted" mission does not actually command drones to land/RTL.

### 4.6 [H6] Unbounded In-Memory Growth
**Files:** `sar/mission_manager.py`, `sar/poi_manager.py`

No eviction policy, no TTL, no maximum size, no cleanup method, no persistence. For long-running SAR operations, this means: OOM accumulation without restart, data loss on restart.

### 4.7 [H7] Frontend: Drone ID Casing Mismatch
**File:** `MissionPlanSidebar.js:57-64`

Uses both `hw_ID` and `hw_id`, `pos_id` and `pos_ID`. The telemetry response uses `hw_ID` from the existing codebase, but the sidebar fallback checks `hw_id`. Drone selection checkboxes are likely broken.

### 4.8 [H8] Frontend: RTL and Abort Are Identical
**File:** `QuickScoutPage.js:302-307`

Both buttons call `handleAbort()`. In drone ops, RTL and Abort are operationally different. The UI presents them as separate actions but they do the same thing.

---

## 5. Known Issues - MEDIUM

| ID | File | Issue |
|----|------|-------|
| M1 | `sar/routes.py:220` | `PATCH /poi` accepts raw `dict`, no Pydantic validation — enum bypass possible |
| M2 | `sar/routes.py:234` | `POST /elevation/batch` accepts arbitrary `List[dict]`, no size limit — DoS vector |
| M3 | `coverage_planner.py` | `pos_id` vs `hw_id` type confusion — targeted pause/resume may silently fail |
| M4 | `coverage_planner.py:161` | `survey_distance` computed but never used — dead code |
| M5 | `terrain.py:85` | No minimum altitude safety floor — negative terrain elevations produce dangerous waypoints |
| M6 | `terrain.py:23` | `chunk_size` parameter documented but never implemented — serial HTTP calls |
| M7 | `routes.py:162+` | No authentication on progress endpoint — any network host can corrupt mission state |
| M8 | `QuickScoutPage.js` | Status polling never stops after mission completes/aborts |
| M9 | `sarApiService.js` | No request timeouts — hung requests in poor network conditions |
| M10 | `sarApiService.js:28` | URL query params built by string concatenation, not `URLSearchParams` |
| M11 | `MissionActionBar.js:36` | `window.confirm()` for abort — blocks thread, untestable, inconsistent |
| M12 | `QuickScout.css:506` | Dead CSS for confirm slider — never used |
| M13 | `All frontend` | No PropTypes — null safety assumed throughout |
| M14 | `QuickScout.css:541` | Mobile layout completely broken — sidebar overflows on small screens |
| M15 | `QuickScoutPage.js:330` | Inline arrow functions cause unnecessary re-renders every 2s |

---

## 6. Known Issues - LOW

| ID | File | Issue |
|----|------|-------|
| L1 | Multiple SAR files | `sys.path.insert(0, ...)` anti-pattern — redundant with app_fastapi's path setup |
| L2 | `schemas.py:57` | `algorithm` field accepted but always ignored — response lies about algorithm used |
| L3 | `schemas.py:50` | `SearchArea.type` field accepted but never validated or used |
| L4 | `quickscout_mission.py:97` | GCS IP defaults to `127.0.0.1` — progress reports silently fail on real drones |
| L5 | `schemas.py:148` | `PLANNING` survey state defined but never used anywhere |
| L6 | `quickscout_mission.py:232` | Mission progress exit may be off-by-one (exits at `total-1` instead of `total`) |
| L7 | Frontend | Clickable `<div>` elements lack keyboard accessibility/ARIA roles |

---

## 7. Architecture Considerations for Reviewer

### 7.1 First Use of APIRouter Pattern
`sar/routes.py` is the **first module** in this codebase to use FastAPI's `APIRouter`. All other endpoints are defined directly on the `app` object in `app_fastapi.py`. This is architecturally better but creates an inconsistency. The reviewer should decide: adopt this pattern going forward, or keep everything in `app_fastapi.py` for consistency.

### 7.2 Singleton Managers
`mission_manager.py` and `poi_manager.py` use the same singleton pattern as `get_command_tracker()`. This is consistent with existing patterns. However, singletons with in-memory state are inherently non-persistent and non-scalable. If MDS ever needs multi-GCS or GCS failover, this architecture breaks.

### 7.3 Coverage Planner Is GCS-Only
The boustrophedon algorithm, Shapely, and pymap3d are GCS-server-only dependencies. Drones receive pre-computed waypoints. This is correct — drones should not need heavy geospatial libraries. The graceful import pattern (`try/except ImportError`) ensures drones don't crash if SAR modules are imported.

### 7.4 PX4 Mission Mode (Not Offboard)
QuickScout deliberately uses PX4 Mission Mode (waypoint upload via MAVSDK `Mission`), NOT Offboard Mode. This means:
- The flight controller executes autonomously once the mission is uploaded
- GCS loses fine-grained real-time control
- Pause/resume requires PX4 mission pause commands (currently not implemented — see H5)
- This is the correct choice for survey flights but limits mid-flight path replanning

### 7.5 Frontend is Mapbox-Dependent But Gracefully Degrades
The map features require Mapbox GL. If no Mapbox token is configured, the components show a setup instructions panel instead of crashing. However, without Mapbox, the entire QuickScout page is non-functional (can't draw search area). Consider whether Leaflet (already used elsewhere in the dashboard) should be an alternative.

---

## 8. What Was NOT Implemented (Scope Gaps)

These items were in the conceptual scope of a SAR module but were NOT in the implementation plan and are NOT present:

1. **No real-time drone path replay** — monitor shows status cards, not live path on map
2. **No geofence / no-fly-zone enforcement** — search area is trusted as-is
3. **No sensor integration** — camera triggers are PX4 mission items, no image capture/downlink
4. **No automatic POI detection** — POIs are manually created by operator
5. **No mission persistence** — all mission state lost on GCS restart
6. **No multi-GCS coordination** — single GCS assumed
7. **No sector rebalancing** — if a drone fails, its sector is abandoned
8. **No weather/wind consideration** — sweep direction is geometric, not wind-optimized
9. **No battery-aware planning** — flight time limits not factored into sector assignment
10. **No actual PX4 pause/resume commands** — pause only updates GCS state

---

## 9. Questions for Reviewer

1. **DroneConfig attribute storage (C3):** Should we add QuickScout fields to `DroneState`, or use a separate mission-specific state dict? What's the preferred pattern for mission-type-specific data?

2. **APIRouter pattern (7.1):** Should we adopt the `APIRouter` pattern for future modules, or revert to adding endpoints directly to `app_fastapi.py`?

3. **Terrain API blocking (H1):** The existing `get_elevation.py` is synchronous. Should we: (a) make it async with `httpx`, (b) use `asyncio.to_thread()` as a wrapper, or (c) pre-compute terrain offline?

4. **Pause/Resume/Abort commands (H5):** The drones are in PX4 Mission Mode. What's the preferred MAVSDK command for pausing a mission? Should we use `Mission.pause_mission()` via a separate drone API endpoint, or add a command type to the existing command dispatch?

5. **Camera triggering (H4):** Should camera actions be per-waypoint MissionItem actions, or should we use a distance/time-based trigger set once? The current approach is broken.

6. **Frontend Mapbox dependency (7.5):** Should we add Leaflet Draw as a fallback for environments without Mapbox, or is Mapbox a hard requirement for QuickScout?

7. **Acceptable risk for first test:** Given the critical issues listed, what's the minimum set of fixes required before a controlled SITL test?

---

## 10. Test Results

| Suite | Tests | Result |
|-------|-------|--------|
| Schema validation | 23 | 23 PASS |
| Coverage planner algorithm | 10 | 10 PASS |
| API endpoint integration | 17 | 17 PASS |
| **Total SAR** | **50** | **50 PASS** |
| Existing GCS API (regression) | 22 | 22 PASS |
| Existing Drone API (regression) | 13 | 13 PASS |

**Note:** Tests cover schema validation, algorithm correctness, and API request/response contracts. They do **not** test:
- Actual PX4 mission upload
- Real MAVSDK connection
- Frontend rendering
- End-to-end drone behavior
- Concurrent mission management under load

---

## 11. Recommended Fix Priority for Next Session

| Priority | Issue | Effort |
|----------|-------|--------|
| 1 | C4: Mission launch ignores failures + hardcoded return_behavior | 30 min |
| 2 | C3: DroneConfig dynamic attributes → proper state fields | 1 hr |
| 3 | C5+C6: React hooks violations + viewport fix | 1 hr |
| 4 | H4: Camera action logic fix | 30 min |
| 5 | H5: Pause/Resume/Abort must command actual drones | 2 hr |
| 6 | H2: Add trigger time check to _execute_quickscout | 30 min |
| 7 | H3: Add timeouts to MAVSDK wait loops | 30 min |
| 8 | C1+C2: Input sanitization for file path and args | 1 hr |
| 9 | H7: Frontend drone ID casing consistency | 30 min |
| 10 | H1: Async terrain elevation or thread wrapper | 1 hr |

---

*This report was generated with full transparency. Every known issue, shortcut, and concern has been disclosed. The implementation is functional for demonstration purposes but requires the fixes listed above before any real flight testing.*
