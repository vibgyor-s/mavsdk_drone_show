# QuickScout SAR/Reconnaissance Module — Full Implementation Prompt

> **Target**: Claude Code Opus 4.6 session with full tool access (Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, Task agents)
> **Project**: MAVSDK Drone Show (MDS) v4.4.0 at `/opt/mavsdk_drone_show`, branch `main-candidate`
> **Scope**: Implement a complete new mission mode — "QuickScout" (cooperative multi-drone search/survey/reconnaissance) — from design through implementation, testing, and documentation.

---

## PHASE 0 — MANDATORY PRE-WORK (Do This First)

Before writing a single line of code, you **must** complete ALL of these steps:

### 0.1 Read the QuickScout Proposal
Read the full proposal document at `~/quickscout_poc_proposal_v1.1.md` (or search `~` for `quickscout` or `proposal`). Extract and internalize every technical requirement, KPI, CONOPS flow, and system architecture detail. This is a defense/enterprise proposal — every stated requirement is binding.

### 0.2 Deep-Read the Existing Codebase
Read and understand these critical files end-to-end (not skim — read fully):

**Mission system (understand how missions work):**
- `src/enums.py` — Mission types, State machine, CommandErrorCode ranges
- `src/drone_config/` — All config data structures
- `src/drone_api_server.py` — Drone-side FastAPI (port 7070), command reception
- `src/drone_communicator.py` — How commands reach MAVSDK
- `src/drone_setup.py` — Pre-flight checks
- `src/params.py` — Global config, sim_mode detection, environment variables

**Existing mission implementations (pattern reference):**
- `swarm_trajectory_mission.py` — **Primary reference**: Uses PositionGlobalYaw, has initial climb, end behaviors, LED feedback. The SAR mission runner should follow this file's patterns most closely.
- `smart_swarm.py` — Leader-follower architecture, Kalman filter, PD controller, dynamic swarm.csv re-read. Understand how follower drones poll leader state.
- `drone_show.py` — Dual setpoint modes, auto global origin, drift compensation. Understand Phase 2 origin system.

**GCS server (understand the API layer):**
- `gcs-server/app_fastapi.py` — All 71+ endpoints, WebSocket handlers, background services
- `gcs-server/schemas.py` — Every Pydantic model (follow these patterns exactly)
- `gcs-server/command.py` — Command dispatch to drones
- `gcs-server/command_tracker.py` — Command lifecycle tracking
- `gcs-server/swarm_trajectory_routes.py` — How trajectory endpoints are organized (follow this pattern for SAR routes)
- `gcs-server/config.py` — Drone/swarm CSV management
- `gcs-server/get_elevation.py` — Elevation API (opentopodata SRTM 90m)

**Frontend (understand UI patterns):**
- `app/dashboard/drone-dashboard/src/App.js` — Router, page structure
- `app/dashboard/drone-dashboard/src/components/SidebarMenu.js` — Navigation categories
- `app/dashboard/drone-dashboard/src/pages/TrajectoryPlanning.js` — Most complex page, Mapbox integration, waypoint system
- `app/dashboard/drone-dashboard/src/pages/Overview.js` — Dashboard layout, CommandSender
- `app/dashboard/drone-dashboard/src/components/CommandSender.js` — How missions are dispatched from UI
- `app/dashboard/drone-dashboard/src/components/DronePositionMap.js` — Leaflet map, drone markers
- `app/dashboard/drone-dashboard/src/services/droneApiService.js` — API client
- `app/dashboard/drone-dashboard/src/services/TerrainService.js` — Elevation service with caching
- `app/dashboard/drone-dashboard/src/utilities/utilities.js` — getBackendURL(), coordinate helpers
- `app/dashboard/drone-dashboard/package.json` — Current dependencies

**Data processing (understand pipeline patterns):**
- `functions/swarm_trajectory_processor.py` — Trajectory processing pipeline
- `functions/swarm_analyzer.py` — Swarm structure analysis

**Configuration:**
- `config.csv` / `config_sitl.csv` — Drone config format (8 columns)
- `swarm.csv` / `swarm_sitl.csv` — Swarm topology format (6 columns)

**Tests (understand testing patterns):**
- `tests/conftest.py` — Fixtures
- `tests/test_gcs_api_http.py` — GCS API test patterns
- `tests/test_drone_api_http.py` — Drone API test patterns
- `tests/test_command_system.py` — Command system tests

**Documentation:**
- `docs/apis/gcs-api-server.md` — API documentation format
- `docs/features/swarm-trajectory.md` — Feature documentation format
- `CHANGELOG.md` — Changelog format

### 0.3 Research Online (Fill Knowledge Gaps)
Use WebSearch to research:
- **Coverage Path Planning (CPP)** algorithms for multi-UAV: DARP algorithm, Boustrophedon decomposition, Voronoi partitioning
- **Fields2Cover** library (Python bindings for coverage planning) — evaluate if suitable or if pure-Python implementation is better for this project
- **Shapely** library for polygon operations in Python
- **Leaflet-Geoman** (`@geoman-io/leaflet-geoman-free`) for polygon drawing on Leaflet maps
- **PX4 offboard mode** survey patterns via MAVSDK-Python
- Any MDS-specific patterns you need to clarify

### 0.4 Create Implementation Plan
After completing 0.1–0.3, create a detailed task list using TaskCreate. Break the work into granular, ordered tasks. Get confirmation before proceeding to implementation.

---

## PHASE 1 — ARCHITECTURE & DATA MODELS

### 1.1 New Mission Type Registration

Add to `src/enums.py`:
```python
QUICKSCOUT = 5  # New mission type for SAR/reconnaissance survey
```

Add corresponding error codes in the E4xx range if needed (e.g., `SEARCH_AREA_INVALID = "E406"`, `COVERAGE_PLAN_FAILED = "E407"`).

### 1.2 Backend Data Models

Create `gcs-server/sar/` package with these Pydantic schemas in `gcs-server/sar/schemas.py`. Follow the exact patterns from `gcs-server/schemas.py` — use `Field(...)` with descriptions, proper validators, `ConfigDict`, etc.

**Core schemas needed:**

```python
# Search area definition
class SearchAreaPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)

class SearchArea(BaseModel):
    """GeoJSON-compatible polygon for search region"""
    type: str = Field(default="polygon")
    points: List[SearchAreaPoint] = Field(..., min_length=3)
    area_sq_m: Optional[float] = Field(None, ge=0)

# Survey configuration
class SurveyConfig(BaseModel):
    algorithm: str = Field(default="boustrophedon", pattern="^(boustrophedon|spiral|sector|parallel_track)$")
    sweep_width_m: float = Field(default=30.0, gt=0, le=500, description="Sweep lane width (meters)")
    overlap_percent: float = Field(default=10.0, ge=0, le=50, description="Overlap between adjacent sweep lanes (%)")
    cruise_altitude_msl: float = Field(..., gt=0, description="Altitude MSL (meters) for transit to/from survey area")
    survey_altitude_agl: float = Field(default=50.0, gt=5, le=400, description="Altitude AGL (meters) during survey sweeps")
    cruise_speed_ms: float = Field(default=10.0, gt=0, le=25, description="Transit speed (m/s)")
    survey_speed_ms: float = Field(default=5.0, gt=0, le=15, description="Survey sweep speed (m/s)")
    use_terrain_following: bool = Field(default=True, description="Adjust altitude per-waypoint to maintain constant AGL using DEM data")
    camera_interval_s: float = Field(default=2.0, gt=0, le=30, description="Auto photo capture interval (seconds). Uses PX4 native MAV_CMD_IMAGE_START_CAPTURE.")

# Mission request
class QuickScoutMissionRequest(BaseModel):
    search_area: SearchArea
    survey_config: SurveyConfig
    pos_ids: List[int] = Field(..., min_length=1, description="Target drone position IDs (consistent with MDS SubmitCommandRequest.pos_ids)")
    return_behavior: str = Field(default="return_home", pattern="^(return_home|land_current|hold_position)$")

# Coverage plan (computed by backend)
class CoverageWaypoint(BaseModel):
    lat: float
    lng: float
    alt_msl: float
    alt_agl: float
    ground_elevation: float
    is_survey_leg: bool  # True=active survey sweep, False=transit/turn
    sequence: int

class DroneCoveragePlan(BaseModel):
    hw_id: str
    pos_id: int
    waypoints: List[CoverageWaypoint]
    assigned_area_sq_m: float
    estimated_duration_s: float
    total_distance_m: float

class CoveragePlanResponse(BaseModel):
    mission_id: str
    plans: List[DroneCoveragePlan]
    total_area_sq_m: float
    estimated_coverage_time_s: float
    algorithm_used: str

# POI (Point of Interest) system
class POI(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str = Field(default="generic", pattern="^(person|vehicle|vessel|structure|anomaly|generic)$")
    priority: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    alt_msl: Optional[float] = None
    timestamp: int = Field(...)  # Unix ms
    reported_by_drone: Optional[str] = None  # hw_id of nearby drone
    drone_position: Optional[SearchAreaPoint] = None
    notes: str = Field(default="", max_length=1000)
    status: str = Field(default="new", pattern="^(new|acknowledged|investigating|resolved|dismissed)$")

# Mission state tracking
class DroneSurveyState(BaseModel):
    hw_id: str
    state: str  # idle|preflight|armed|taking_off|cruising_to_area|surveying|paused|returning|landing|emergency
    current_waypoint_index: int = 0
    total_waypoints: int = 0
    coverage_percent: float = 0.0
    distance_covered_m: float = 0.0
    estimated_remaining_s: float = 0.0

class MissionStatus(BaseModel):
    mission_id: str
    state: str  # planning|ready|executing|paused|completed|aborted
    drone_states: Dict[str, DroneSurveyState]
    pois: List[POI]
    total_coverage_percent: float
    elapsed_time_s: float
    started_at: Optional[int] = None
```

### 1.3 Mission Execution Model: Cooperative Independent Sectors

**Critical architectural decision — DO NOT implement leader-follower for QuickScout.**

Even though MDS has Smart Swarm (leader-follower with PD controller + Kalman filter via `swarm.csv` offsets), QuickScout uses a fundamentally different model: **Cooperative Independent Sectors**.

**Why NOT leader-follower for SAR:**
- Followers maintaining formation offsets means N drones cover ~same ground (no parallel speedup)
- Boustrophedon turns cause offset-tracking chaos (PD controller fights the geometry)
- Single point of failure: leader down = all followers enter failsafe
- `swarm.csv` offsets are formation-defined, not sensor-coverage-aligned

**Why cooperative independent sectors:**
- N drones → area surveyed N× faster (linear speedup)
- Each drone gets a standalone waypoint list — zero inter-drone communication during flight
- Fault tolerant: 1 drone fails → only 1/N coverage lost, others unaffected
- Clean turns: each drone handles its own boustrophedon independently
- Simple assignment: partition area, assign sectors by proximity to current GPS position

**How drone selection works:**
- User selects drones by `pos_id` (same as `SubmitCommandRequest.pos_ids` convention)
- User can select individual drones, or pick all drones from a swarm cluster — either way, all selected drones are treated as independent survey agents
- The `swarm.csv` leader/follower topology is IGNORED during QuickScout — it only matters for Smart Swarm mode

**Starting position optimization (with graceful fallback):**
- At plan-compute time (`POST /api/sar/mission/plan`), the backend fetches current GPS positions of all assigned drones from the in-memory telemetry store
- After partitioning the search area into N sectors, sectors are assigned to drones by **minimum total transit distance** (greedy nearest-assignment or Hungarian algorithm for optimal matching)
- Transit waypoints are prepended: drone's current GPS → assigned sector entry point at cruise altitude
- **Fallback when GPS unavailable**: If some/all drones lack telemetry positions (powered off, no GPS fix), the planner still works:
  - Drones WITH GPS → assigned by proximity
  - Drones WITHOUT GPS → assigned remaining sectors in `pos_id` order (no transit optimization)
  - Frontend shows a warning: "Drone positions unavailable for N drones — sector assignment not optimized"
  - Transit waypoints are omitted for GPS-less drones (they will fly directly from takeoff to first survey waypoint)
  - The plan is still valid and launchable — just suboptimal transit routing

> **Future phase (not PoC):** Add a "Formation Survey" mode that computes one survey path for a leader and uses Smart Swarm's leader-follower with sweep-width-aligned offsets. Useful for close-formation multi-sensor missions (RGB + thermal on adjacent drones). Out of scope for this implementation.

### 1.4 Backend Module Organization

Create this structure inside `gcs-server/`:
```
gcs-server/
  sar/
    __init__.py
    schemas.py          # All Pydantic models above
    routes.py           # FastAPI router (APIRouter prefix="/api/sar")
    mission_manager.py  # Mission lifecycle, state machine, in-memory mission store
    coverage_planner.py # Area decomposition + path generation algorithms
    terrain.py          # Batch elevation queries, terrain-following altitude computation
    poi_manager.py      # POI CRUD + broadcast
```

Register the router in `app_fastapi.py`:
```python
from sar.routes import router as sar_router
app.include_router(sar_router)
```

### 1.5 Coverage Path Planning Algorithm

Implement in `gcs-server/sar/coverage_planner.py`. This is the computational core.

**Algorithm: Boustrophedon (back-and-forth sweep) with multi-drone cooperative partitioning**

For the initial implementation (demo-ready, extensible later):

1. **Input**: Polygon (list of lat/lng vertices), list of drone starting GPS positions (from telemetry), sweep width, overlap
2. **Coordinate transform**: Convert all lat/lng to a local metric frame (use pymap3d — already in requirements.txt — ENU from polygon centroid as origin). All geometry math happens in meters, convert back to lat/lng for output.
3. **Bounding box**: Compute the axis-aligned bounding box of the polygon in the local frame
4. **Optimal sweep angle**: Compute the angle that minimizes the number of turns (align sweeps with the longest axis of the polygon using PCA on polygon vertices or simply using the longest edge direction)
5. **Generate sweep lines**: Create parallel lines across the polygon at `sweep_width * (1 - overlap/100)` spacing, rotated to optimal angle
6. **Clip to polygon**: Use Shapely to intersect sweep lines with the polygon boundary. Each clipped segment becomes a survey leg.
7. **Connect into boustrophedon path**: Alternate direction on each sweep line (zigzag). This produces one continuous coverage path.
8. **Multi-drone partitioning**: Divide the sweep lines into N contiguous groups (N = number of drones). Each group has approximately equal total path length.
9. **Sector assignment by proximity**: Convert drone starting positions to the local frame. Assign sectors to drones using greedy nearest-match: for each sector's entry point, find the nearest unassigned drone. This minimizes total transit distance.
10. **Add transit waypoints**: For each drone, prepend waypoints from current GPS position to assigned sector entry point at cruise altitude, append waypoints for return (sector exit → home position or designated landing zone)
11. **Terrain adjustment**: For each survey waypoint, query elevation (batch) and compute `alt_msl = ground_elevation + survey_altitude_agl`. For transit waypoints, use `cruise_altitude_msl`.

**Dependencies to use:**
- `shapely` — Polygon operations (intersection, contains, area, bounds)
- `numpy` — Efficient coordinate math
- `pymap3d` — Already in requirements.txt, use for coordinate conversions

Do NOT add `fields2cover` as a dependency — it has complex C++ build requirements. Implement the algorithm in pure Python using Shapely + NumPy. This keeps the project dependency-light and deployable on Raspberry Pi.

**Algorithm extensibility**: Structure the planner with a base class pattern so future algorithms can be added:
```python
class BaseCoveragePlanner:
    def plan(self, polygon, drone_positions, config) -> List[DroneCoveragePlan]: ...

class BoustrophedonPlanner(BaseCoveragePlanner): ...
# Future: class SpiralPlanner(BaseCoveragePlanner): ...
# Future: class SectorPlanner(BaseCoveragePlanner): ...
```

### 1.6 Flight Execution: PX4 Mission Mode (NOT Offboard)

**Critical architectural decision: Use PX4 Mission Mode via MAVSDK Mission plugin, NOT Offboard Mode.**

While all existing MDS missions (drone_show, smart_swarm, swarm_trajectory) use offboard mode, QuickScout should use **Mission Mode** because:

1. **Survey waypoints are pre-computed and static** — exactly what Mission Mode is designed for
2. **Built-in pause/resume**: `pause_mission()` → drone loiters, `start_mission()` → resumes from interrupted waypoint. Zero custom state management needed.
3. **Built-in progress**: `mission_progress()` yields `(current_item, total_items)` — no custom tracking loop
4. **FC-autonomous after upload**: If companion computer (RPi) crashes, flight controller continues the mission. With offboard, a 2-second communication gap triggers failsafe.
5. **Native waypoint navigation**: PX4's navigator handles turns, acceptance radius, speed changes
6. **Camera integration**: `MissionItem.CameraAction` can trigger photos at each waypoint (useful for future vision integration)
7. **Dramatically simpler code**: ~50 lines vs ~150 lines for offboard waypoint loop

The MAVSDK Mission plugin provides: `upload_mission()`, `start_mission()`, `pause_mission()`, `clear_mission()`, `mission_progress()`, `set_current_mission_item(index)`.

Create `quickscout_mission.py` at the project root (same level as `swarm_trajectory_mission.py`).

**Follow `swarm_trajectory_mission.py` patterns for:**
- Argument parsing structure
- MAVSDK connection flow
- LED feedback patterns (add SAR-specific colors: e.g., blue pulsing = cruising, green sweep = surveying, yellow = paused)
- Logging patterns

**But use Mission Mode for flight execution (new pattern for MDS):**

**Mission execution flow:**
```
1. Parse args (start_time, mission_id, hw_id, waypoints_json_path)
2. Connect MAVSDK
3. Pre-flight checks (GPS, home position, battery)
4. Load waypoints from JSON file
5. Build MissionItem list:
   - FIRST item (survey start): MissionItem with camera_action=START_PHOTO_INTERVAL
     and camera_photo_interval_s=config.camera_interval_s (default 2.0s)
   - For each survey waypoint: MissionItem(
       latitude_deg=wp.lat,
       longitude_deg=wp.lng,
       relative_altitude_m=wp.alt_msl - home_alt_msl,  # Convert AMSL to relative-to-home
       speed_m_s=wp.speed,
       is_fly_through=True,  # Don't stop at each waypoint (PX4 native fly-through)
       acceptance_radius_m=3.0,  # Configurable (PX4 NAV_ACC_RAD default)
       yaw_deg=wp.yaw,  # Heading toward next waypoint
       camera_action=CameraAction.NONE  # Interval trigger handles auto-capture
     )
   - LAST survey item: camera_action=STOP_PHOTO_INTERVAL (stop capturing before return transit)
   - Transit waypoints (to/from survey area): camera_action=NONE, speed=cruise_speed
   - NOTE: PX4 natively handles camera triggers via MAV_CMD_IMAGE_START/STOP_CAPTURE.
     MAVSDK's MissionItem.CameraAction maps directly to these MAVLink commands.
     This is the standard PX4 way — no custom camera control code needed.
6. Upload mission: await drone.mission.upload_mission(MissionPlan(items))
7. Wait for start_time (synchronized launch)
8. Arm: await drone.action.arm()
9. Start mission: await drone.mission.start_mission()
10. Monitor progress loop:
    async for progress in drone.mission.mission_progress():
      - Report to GCS: POST /api/sar/mission/{id}/progress
      - Check for pause command (poll GCS endpoint)
      - If pause: await drone.mission.pause_mission()
        - Wait for resume command
        - await drone.mission.start_mission()
      - If abort: await drone.action.return_to_launch()
      - If progress.current == progress.total: mission complete
11. Execute return behavior (RTL/land/hold)
12. Report mission complete to GCS
```

**Altitude handling (important):**
- `MissionItem.relative_altitude_m` = altitude relative to HOME (takeoff position)
- Backend computes `alt_msl` (AMSL) for each waypoint
- Drone-side converts: `relative_alt = waypoint.alt_msl - home_position.alt_msl`
- Home position is obtained via `drone.telemetry.home()` after GPS fix

**Waypoint data source**: The drone receives its waypoint list from the GCS at mission dispatch time. The GCS command includes a `waypoints_json` field in params. The drone-side API writes this to a temp file and passes the path to `quickscout_mission.py`.

> **Future extension**: If dynamic path modification is needed (e.g., mid-flight re-routing to investigate a POI), add an offboard-mode executor as an alternative flight engine. The coverage planner (backend) is decoupled from the flight executor (drone-side), so both can coexist.

### 1.7 Command Integration

Modify `src/drone_api_server.py` to handle `QUICKSCOUT = 5`:
- Accept the mission command with `waypoints` in params
- Launch `quickscout_mission.py` as subprocess (same pattern as other missions)
- Pass waypoints via a temp JSON file or stdin

Modify `gcs-server/command.py` to support the new mission type:
- Add QUICKSCOUT to the mission type handler
- Ensure the command payload includes per-drone waypoint data

---

## PHASE 2 — FRONTEND IMPLEMENTATION

> **UI/UX Design Philosophy**: Based on research of QGroundControl, Auterion Mission Control, FlytBase Fleet View 2.0, UgCS Commander, DroneDeploy, and Pix4Dcapture — every major GCS uses a **single-page with Plan/Monitor mode toggle**, NOT separate pages. The map is always the dominant element (70-80% of screen). Progressive disclosure handles beginner vs. expert users. Target: **3 clicks + polygon draw** from "new mission" to "drones flying."

### 2.1 Single-Page Architecture: Plan Mode ↔ Monitor Mode

Create `app/dashboard/drone-dashboard/src/pages/QuickScoutPage.js`

This is a **single page** with two internal modes that share the same map view, same WebSocket connection, and same state — the mode just changes what's visible in the sidebar and toolbar.

**PLAN MODE** (mission setup — before launch):
```
┌──[Plan]──[Monitor]──────────────────────────── Status Bar ──┐
│                                                              │
│ ┌─ Left Toolbar ─┐  ┌──────── MAP (75%) ──────────┐ ┌────┐ │
│ │ [Draw Polygon]  │  │                              │ │ R  │ │
│ │ [Draw Rectangle]│  │   (Leaflet with satellite)   │ │ i  │ │
│ │ [Edit Area]     │  │                              │ │ g  │ │
│ │ [Clear]         │  │  ┌────────────────────────┐  │ │ h  │ │
│ │                 │  │  │   Search area polygon   │  │ │ t  │ │
│ │                 │  │  │   (editable vertices)   │  │ │    │ │
│ │                 │  │  │                         │  │ │ S  │ │
│ │                 │  │  │  ══ coverage preview ══ │  │ │ i  │ │
│ │                 │  │  │  ══ (colored per drn) ═ │  │ │ d  │ │
│ │                 │  │  │                         │  │ │ e  │ │
│ │                 │  │  └────────────────────────┘  │ │ b  │ │
│ │                 │  │                              │ │ a  │ │
│ │                 │  │  Area: 0.5 km²  ETA: 12min  │ │ r  │ │
│ └─────────────────┘  └──────────────────────────────┘ │    │ │
│                                                       │    │ │
│  RIGHT SIDEBAR (collapsible, ~280px):                 │    │ │
│  ┌──────────────────────────────────────────┐         │    │ │
│  │ DRONE SELECTION                          │  <------│    │ │
│  │ [✓] Drone 1 (Online, GPS OK, Bat 92%)   │         │    │ │
│  │ [✓] Drone 2 (Online, GPS OK, Bat 88%)   │         │    │ │
│  │ [ ] Drone 3 (Offline)                    │         │    │ │
│  │                                          │         └────┘ │
│  │ QUICK CONFIG (always visible)            │                │
│  │ Survey Alt (AGL): [50m ▼]                │                │
│  │ Cruise Alt (MSL): [180m] (auto-filled)   │                │
│  │                                          │                │
│  │ ▸ More Options (collapsed by default)    │                │
│  │   Sweep Width: [30m]                     │                │
│  │   Overlap: [10%]                         │                │
│  │   Survey Speed: [5 m/s]                  │                │
│  │   Algorithm: [Boustrophedon ▼]           │                │
│  │   Camera Interval: [2s ▼]               │                │
│  │   Return Behavior: [RTL ▼]              │                │
│  │                                          │                │
│  │ [  Compute Plan  ] ← primary action      │                │
│  │ [▶ START MISSION ] ← slide-to-confirm    │                │
│  │        (disabled until plan computed)     │                │
│  └──────────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────────┘
```

**MONITOR MODE** (during mission execution — auto-switches on launch):
```
┌──[Plan]──[Monitor]──────────────────────────── Status Bar ──┐
│  Coverage: 34%  |  Elapsed: 04:12  |  ETA: 08:30            │
│                                                              │
│ ┌─ Action Bar ─┐  ┌──────── MAP (75%) ──────────┐ ┌──────┐ │
│ │              │  │                              │ │Drone │ │
│ │ [▶ Resume]   │  │  (Live drone positions)      │ │Status│ │
│ │  (green)     │  │  (Coverage heat overlay)     │ │Cards │ │
│ │              │  │  (POI markers)               │ │──────│ │
│ │ [⏸ Pause]   │  │                              │ │Drn 1 │ │
│ │  (amber,     │  │  [1]──sweep──>               │ │Survey│ │
│ │   hold 1s)   │  │        <──sweep──[1]         │ │45%   │ │
│ │              │  │                              │ │52m   │ │
│ │ [↩ RTL ]    │  │   [2]──sweep──>              │ │88%bat│ │
│ │  (orange,    │  │         <──sweep──[2]        │ │[⏸][↩]│ │
│ │   slide)     │  │                              │ │──────│ │
│ │              │  │  📍 POI-1 (person, high)     │ │Drn 2 │ │
│ │ [■ ABORT]   │  │                              │ │Survey│ │
│ │  (red,       │  │                              │ │32%   │ │
│ │   hold 3s)   │  │                              │ │48m   │ │
│ │              │  │                              │ │91%bat│ │
│ │──────────────│  │                              │ │[⏸][↩]│ │
│ │ POI Tools:   │  │                              │ │──────│ │
│ │ [📍Mark POI] │  │                              │ │      │ │
│ │              │  │                              │ │ POIs │ │
│ │ Scope:       │  │                              │ │ (3)  │ │
│ │ ○ All Drones │  │                              │ │14:23 │ │
│ │ ● Selected   │  │                              │ │Person│ │
│ └──────────────┘  └──────────────────────────────┘ └──────┘ │
└──────────────────────────────────────────────────────────────┘
```

**Critical UX behavior:**
- When user clicks "START MISSION" in Plan mode → page **auto-transitions** to Monitor mode (same map, same zoom, no page reload)
- When mission completes/aborts → user can switch back to Plan mode to start a new mission
- Map state (zoom, center, layers) is preserved across mode switches
- The Plan/Monitor tabs are always visible at top — user can peek at the plan during monitoring (read-only)

### 2.2 Progressive Disclosure: Three Levels

This is how the interface handles both beginners (simple SAR sweep) and experts (complex military ops):

**Level 1 — Quick Start (always visible):**
- Draw area on map (polygon or rectangle)
- Select drones (checkboxes with live status)
- Survey altitude AGL: `[50m]` (pre-filled sensible default)
- Cruise altitude MSL: `[auto-filled from elevation]`
- `[Compute Plan]` → `[START MISSION]`
- **This covers 80% of SAR missions with 3 clicks + draw.**

**Level 2 — More Options (collapsed section, toggle open):**
- Sweep width, overlap %, survey speed, cruise speed
- Algorithm selector (Boustrophedon is default, future: spiral, sector)
- Camera capture interval (auto photo every N seconds, default 2s)
- Return behavior (RTL / Land in place / Hold position)
- This opens inline, no page change.

**Level 3 — Advanced (separate slide-out panel via "Advanced" link):**
- Custom sweep angle override
- Terrain-following enable/disable
- Min/max altitude constraints
- Battery endurance limit (% at which auto-RTL)
- Acceptance radius per waypoint
- Camera trigger mode (interval vs. distance-based)
- This is a future extension point — for PoC, Level 1+2 are sufficient.

### 2.3 Map Drawing Integration

Install `@geoman-io/leaflet-geoman-free` as a new dependency:
```bash
cd app/dashboard/drone-dashboard && npm install @geoman-io/leaflet-geoman-free
```

Create `app/dashboard/drone-dashboard/src/components/sar/SearchAreaDrawer.js`:
- Use `useMap()` hook from react-leaflet
- Initialize Leaflet-Geoman controls (`map.pm.addControls`) in the left toolbar area
- Enable: Polygon, Rectangle drawing; Edit mode; Cut mode (for no-fly zones later)
- On `pm:create` event: extract GeoJSON coordinates, compute area via `@turf/turf`, call parent callback
- On `pm:edit` event: update coordinates and re-compute area
- Display computed area (sq m for <1km², sq km for >=1km²) as a map overlay label
- Only allow ONE search area at a time (new draw clears old). Confirmation if replacing existing.
- Double-click to close polygon (standard Leaflet-Geoman behavior)

### 2.4 Coverage Plan Visualization

Create `app/dashboard/drone-dashboard/src/components/sar/CoveragePreview.js`:
- Render computed coverage paths as Leaflet Polylines
- **Color-code by drone** (assign consistent colors: drone 1 = blue, drone 2 = green, drone 3 = orange, etc. — match existing MDS drone color conventions if any)
- Differentiate visually: **solid line** = active survey leg, **dashed line** = transit leg
- Show waypoint dots with sequence numbers (only when zoomed in to avoid clutter)
- During mission execution (Monitor mode):
  - **Completed legs**: thick solid line (opaque)
  - **Current position**: animated pulsing dot on the drone
  - **Remaining legs**: thin semi-transparent line
  - **Coverage overlay**: green-tinted filled polygon over swept areas (using Turf.js buffer on completed legs)
- Show computed stats above map: Area, Total distance, ETA, Drones assigned

### 2.5 POI Marker System

Create `app/dashboard/drone-dashboard/src/components/sar/POIMarkerSystem.js`:
- **In Monitor mode**: Click `[Mark POI]` button → click on map → POI popup appears
- Popup form (compact): type dropdown, priority selector (4 color-coded buttons), notes text field (1 line), auto-filled: timestamp, nearest drone ID + its GPS position at that moment
- Custom Leaflet marker icons per POI type (use simple SVG or Font Awesome icons with colored backgrounds: red=person, blue=vehicle, cyan=vessel, yellow=anomaly, grey=generic)
- POI list in the right sidebar (below drone cards in Monitor mode): chronological, showing timestamp + type + priority badge
- Click a POI in list → map pans/zooms to it
- POIs persist across mode switches (stored in mission state)

### 2.6 Drone Status Cards (Monitor Mode)

Create `app/dashboard/drone-dashboard/src/components/sar/DroneStatusCard.js`:
- Compact card per drone in the right sidebar during Monitor mode
- Shows: drone name/ID, mission state (colored badge), coverage %, altitude, battery %, speed
- **Per-drone controls**: small `[⏸]` pause and `[↩]` RTL buttons on each card
- Color-coded border: green=surveying, amber=paused, blue=cruising, red=emergency
- Click card → map centers on that drone

### 2.7 Mission Action Controls (Monitor Mode)

Create `app/dashboard/drone-dashboard/src/components/sar/MissionActionBar.js`:

**Action hierarchy with progressive confirmation friction** (industry standard):

| Action | Button Style | Confirmation | Scope Toggle |
|--------|-------------|--------------|--------------|
| **Resume** | Green filled | Click (instant) | All / Selected |
| **Pause** | Amber outlined | Hold 1 second | All / Selected |
| **RTL** | Orange outlined | Slide-to-confirm | All / Selected |
| **ABORT** | Red filled | Hold 3 seconds + "Are you sure?" dialog | All only |

- **Scope toggle**: Radio buttons "All Drones" / "Selected" at bottom of action bar. When "Selected", actions only apply to drones checked in the status cards.
- Spatial separation: Resume/Pause at top, RTL in middle, ABORT at bottom with visual divider
- All buttons show brief toast confirmation on action: "Paused 2 drones", "RTL sent to Drone 1"

### 2.8 Navigation Integration

Add to `SidebarMenu.js` menuItems array:
```javascript
{ to: '/quickscout', icon: FaSearchLocation, label: 'QuickScout', category: 'workflow' }
```

Import `FaSearchLocation` from `react-icons/fa` (or `FaCrosshairs` — choose whichever is available in the installed react-icons version).

Add route in `App.js`:
```javascript
import QuickScoutPage from './pages/QuickScoutPage';
// ...
<Route path="/quickscout" element={<QuickScoutPage />} />
```

### 2.9 Auto-Fill Altitude Logic

When user draws/edits a search area, **immediately** (debounced 500ms):
1. Sample elevation at polygon vertices + centroid using `TerrainService.js` (existing service)
2. Compute: `recommended_cruise_alt = max(sampled_elevations) + 80m` (configurable buffer constant)
3. Auto-fill cruise altitude field (MSL) — show tooltip: "Auto-computed: terrain max Xm + 80m buffer"
4. Pre-fill survey altitude AGL = 50m (configurable default constant)
5. User can override both — field shows "(auto)" badge until manually changed
6. If elevation API fails: leave cruise altitude blank, show info message "Enter cruise altitude manually (elevation data unavailable)", survey AGL default still applies

### 2.10 Component File Structure

```
src/
  pages/
    QuickScoutPage.js           # Main page, mode state management, composition
  components/
    sar/
      SearchAreaDrawer.js        # Leaflet-Geoman polygon drawing
      CoveragePreview.js         # Coverage path visualization on map
      MissionPlanSidebar.js      # Right sidebar for Plan mode (config + compute + launch)
      MissionMonitorSidebar.js   # Right sidebar for Monitor mode (drone cards + POI list)
      MissionActionBar.js        # Left action bar for Monitor mode (pause/resume/RTL/abort)
      DroneStatusCard.js         # Individual drone status card
      POIMarkerSystem.js         # POI click-to-mark + popup + list
      PlanMonitorToggle.js       # Plan/Monitor tab toggle at top
      MissionStatsBar.js         # Coverage %, ETA, elapsed time status bar
  services/
    sarApiService.js             # All SAR API calls (plan, launch, pause, resume, abort, POI CRUD)
  styles/
    QuickScout.css               # All QuickScout-specific styles (scoped)
```

---

## PHASE 3 — API ENDPOINTS

### 3.1 SAR REST Endpoints

Create in `gcs-server/sar/routes.py` using `APIRouter(prefix="/api/sar", tags=["QuickScout SAR"])`:

```
POST /api/sar/mission/plan
  Body: QuickScoutMissionRequest
  Response: CoveragePlanResponse
  → Computes coverage plan without launching. Frontend shows preview.

POST /api/sar/mission/launch
  Body: { mission_id: str, confirm: bool }
  Response: SubmitCommandResponse (reuse existing schema)
  → Dispatches QUICKSCOUT=5 command to assigned drones with their waypoints.

GET /api/sar/mission/{mission_id}/status
  Response: MissionStatus
  → Returns current state of all drones in this mission + POIs + coverage.

POST /api/sar/mission/{mission_id}/pause
  Body: { pos_ids: Optional[List[int]] }  # None = all drones in mission
  Response: { success: bool, message: str }

POST /api/sar/mission/{mission_id}/resume
  Body: { pos_ids: Optional[List[int]] }
  Response: { success: bool, message: str }

POST /api/sar/mission/{mission_id}/abort
  Body: { pos_ids: Optional[List[int]], return_behavior: str }
  Response: { success: bool, message: str }

POST /api/sar/mission/{mission_id}/progress
  Body: DroneSurveyState (called by drone-side to report progress)
  Response: { received: bool }

# POI endpoints
POST /api/sar/poi
  Body: POI (without id — server generates)
  Response: POI (with id)

GET /api/sar/poi?mission_id={id}
  Response: { pois: List[POI] }

PATCH /api/sar/poi/{poi_id}
  Body: { status?, notes?, priority? }
  Response: POI

DELETE /api/sar/poi/{poi_id}
  Response: { success: bool }

# Elevation batch helper
POST /api/sar/elevation/batch
  Body: { points: List[{lat, lng}] }
  Response: { elevations: List[{lat, lng, elevation_m}] }
```

### 3.2 WebSocket Channel (Optional Enhancement)

If needed for real-time updates, add a WebSocket endpoint:
```python
@app.websocket("/ws/sar/{mission_id}")
```
Broadcasts: drone state changes, coverage updates, new POIs.

However: **start with polling** (consistent with existing MDS pattern where frontend polls `/telemetry` every 1-2s). Add WebSocket only if polling proves insufficient. Keep it simple.

---

## PHASE 4 — TESTING

### 4.1 Backend Unit Tests

Create `tests/test_sar_coverage_planner.py`:
- Test boustrophedon sweep generation for simple rectangle
- Test boustrophedon for concave polygon
- Test multi-drone partitioning (2, 3, 5 drones)
- Test terrain-following altitude adjustment
- Test edge cases: tiny polygon, single drone, polygon with < 3 vertices
- Test sweep angle optimization

Create `tests/test_sar_api.py`:
- Test `POST /api/sar/mission/plan` with valid request
- Test `POST /api/sar/mission/plan` with invalid polygon (< 3 points)
- Test `POST /api/sar/mission/plan` with invalid drone IDs
- Test `POST /api/sar/mission/launch` lifecycle
- Test `POST /api/sar/poi` CRUD operations
- Test mission state transitions (plan → launch → pause → resume → complete)
- Test `POST /api/sar/elevation/batch`

Create `tests/test_sar_schemas.py`:
- Test all Pydantic schema validation (valid and invalid inputs)
- Test SearchArea polygon validation
- Test SurveyConfig range constraints

### 4.2 Frontend Tests

At minimum, test the coverage planner API integration and key component rendering. Follow patterns from existing test files if any.

### 4.3 Integration Testing

Provide a SITL test scenario:
- Configure 3 drones in `config_sitl.csv` (if not already)
- Define a test search area polygon (use coordinates near the SITL home position)
- Document step-by-step manual test procedure

---

## PHASE 5 — DOCUMENTATION

### 5.1 Feature Documentation

Create `docs/features/quickscout.md` following the format of `docs/features/swarm-trajectory.md`:
- Overview & purpose
- Architecture diagram (ASCII)
- Configuration reference
- API reference (all endpoints with examples)
- UI walkthrough
- Algorithm description
- SITL testing guide

### 5.2 API Documentation

Update `docs/apis/gcs-api-server.md` to add all new SAR endpoints.

### 5.3 Changelog

Add entry to `CHANGELOG.md` following existing format.

---

## CRITICAL CONSTRAINTS & STANDARDS

### Code Quality Standards
- **Zero TypeScript** — Frontend is plain JavaScript (React). Do not introduce TypeScript.
- **Zero new frameworks** — Use existing: React, MUI, Leaflet, Axios, react-toastify. Only add `@geoman-io/leaflet-geoman-free` for drawing.
- **Pydantic V2** — All schemas use `model_config = ConfigDict(...)`, V2 validators. Match `gcs-server/schemas.py` exactly.
- **FastAPI async** — All new endpoints use `async def`. Match existing patterns.
- **Python 3.11+** — Use modern Python features but nothing that breaks 3.11.
- **No magic numbers** — All configurable values as constants or config parameters.
- **Logging** — Use `logging.getLogger(__name__)` pattern. Match existing log levels.

### Naming Conventions (Match Existing)
- **Python**: snake_case functions, PascalCase classes, UPPER_SNAKE constants
- **JavaScript**: camelCase functions, PascalCase components, UPPER_SNAKE constants
- **API routes**: kebab-case paths (`/api/sar/mission/plan`)
- **Files**: snake_case.py (Python), PascalCase.js (React components), camelCase.js (utilities/services)
- **CSS**: Follow existing BEM-like patterns, use CSS modules or scoped classes

### PX4 Adherence Principle (CRITICAL)
- **Always use standard PX4 modes and MAVLink commands** — never invent custom protocols when PX4 has a native way.
- **Mission Mode** for survey: uses standard MAV_CMD_NAV_WAYPOINT, MAV_CMD_IMAGE_START_CAPTURE, etc. These are stable across PX4 versions.
- **Camera triggers**: Use `MissionItem.CameraAction.START_PHOTO_INTERVAL` → maps to `MAV_CMD_IMAGE_START_CAPTURE`. This is the standard PX4 camera trigger mechanism. Do NOT build custom camera control.
- **Pause/Resume**: Use `pause_mission()` / `start_mission()` which map to MAV_CMD_DO_PAUSE_CONTINUE. This is standard PX4 behavior.
- **RTL**: Use `action.return_to_launch()` → MAV_CMD_NAV_RETURN_TO_LAUNCH. Standard PX4.
- **Altitude**: Use `relative_altitude_m` in MissionItems (relative to home). This is how PX4 mission mode handles altitude. Do NOT send raw AMSL unless using mission_raw plugin.
- **Acceptance radius**: Respect PX4's `NAV_ACC_RAD` parameter default (configurable). MissionItem.acceptance_radius_m maps directly to this.
- **Speed**: MissionItem.speed_m_s maps to `MAV_CMD_DO_CHANGE_SPEED`. PX4 handles speed transitions natively between waypoints.
- **Fly-through**: `is_fly_through=True` tells PX4 to not stop at waypoints (MAV_CMD_NAV_WAYPOINT with acceptance radius). Standard behavior for survey.
- **Why this matters**: PX4 is actively developed. Custom workarounds break on updates. Standard MAVLink commands are maintained for backward compatibility across PX4 versions. By using native PX4 mission mode, QuickScout automatically benefits from PX4 improvements (better path smoothing, terrain following, geofence integration) without code changes.

### Architecture Principles
- **Consistency first**: Every pattern must match an existing MDS pattern. If unsure, find the most similar existing feature and mirror it.
- **No breaking changes**: All existing endpoints, configs, and behaviors must continue working unchanged.
- **Offline-capable**: The coverage algorithm runs server-side (Python), not in browser. Frontend only visualizes.
- **Graceful degradation**: If elevation API is unavailable, system still works (manual altitude input). If a drone disconnects mid-survey, remaining drones continue.
- **Sim/real mode**: All new code must respect `Params.sim_mode`. Use `config_sitl.csv`/`config.csv` accordingly.
- **No hardcoded IPs/ports**: Use existing `getBackendURL()` pattern in frontend, environment variables in backend.

### Safety-Critical Requirements
- **Pre-flight validation**: Before launch, verify all assigned drones are online, GPS-ready, and battery sufficient.
- **Minimum altitude enforcement**: Survey altitude AGL must be >= 10m. Cruise altitude must clear terrain by >= 30m.
- **Emergency stop**: Abort/RTL must be available at all times during mission execution.
- **Failsafe**: If a drone loses GCS connection for > 30 seconds, it should RTL autonomously (this is PX4 built-in — ensure it's not overridden).
- **Battery monitoring**: Warn if estimated mission time exceeds 70% of battery endurance.

### What NOT to Do
- Do NOT modify `drone_show.py` or `smart_swarm.py` or `swarm_trajectory_mission.py` unless absolutely necessary for integration (and if so, document why)
- Do NOT add new Python dependencies unless listed above (`shapely` is the only new backend dependency expected; it may already be installed)
- Do NOT refactor existing code "for consistency" — only touch existing files to add integration points (new enum value, new route registration, new menu item)
- Do NOT add authentication/authorization (out of scope for PoC)
- Do NOT implement the AI vision/detection system (out of scope — stated as future phase in proposal)
- Do NOT add video streaming (out of scope for PoC)
- Do NOT create Docker/deployment changes
- Do NOT introduce any country-specific naming in code (no "Taiwan", no country names in code/comments — use generic terms like "defense", "maritime", "coastal")

---

## IMPLEMENTATION ORDER (Execute Sequentially)

**Backend Core (Steps 1-9):**
1. **Backend schemas** (`gcs-server/sar/schemas.py`) — Data models first, everything depends on these
2. **Coverage planner** (`gcs-server/sar/coverage_planner.py`) — Core algorithm with base class pattern
3. **Coverage planner tests** (`tests/test_sar_coverage_planner.py`) — Verify algorithm correctness before proceeding
4. **Terrain helper** (`gcs-server/sar/terrain.py`) — Batch elevation, terrain-following altitude computation
5. **Mission manager** (`gcs-server/sar/mission_manager.py`) — FSM state machine, in-memory mission store
6. **POI manager** (`gcs-server/sar/poi_manager.py`) — POI CRUD operations
7. **API routes** (`gcs-server/sar/routes.py`) — Wire everything together as FastAPI APIRouter
8. **Route registration** in `app_fastapi.py` — include SAR router
9. **API + Schema tests** (`tests/test_sar_api.py`, `tests/test_sar_schemas.py`)

**Drone-Side (Steps 10-12):**
10. **Enum update** (`src/enums.py`) — Add `QUICKSCOUT = 5`
11. **Drone-side mission runner** (`quickscout_mission.py`) — PX4 Mission Mode executor with camera auto-interval
12. **Drone API integration** (`src/drone_api_server.py`) — Accept QUICKSCOUT commands, launch mission runner

**Frontend (Steps 13-19):**
13. **Install dependency**: `cd app/dashboard/drone-dashboard && npm install @geoman-io/leaflet-geoman-free`
14. **API service** (`src/services/sarApiService.js`) — All SAR API calls
15. **Map components**: SearchAreaDrawer, CoveragePreview, POIMarkerSystem
16. **Sidebar components**: MissionPlanSidebar, MissionMonitorSidebar, DroneStatusCard
17. **Control components**: MissionActionBar, PlanMonitorToggle, MissionStatsBar
18. **Page composition** (`QuickScoutPage.js`) — Compose all components with Plan/Monitor mode state
19. **Navigation** — Add route in App.js, menu item in SidebarMenu.js

**Verification & Documentation (Steps 20-23):**
20. **End-to-end testing** — Manual SITL verification with test polygon
21. **Documentation** — Feature docs (`docs/features/quickscout.md`), API docs update, SITL guide
22. **CHANGELOG + version bump** — Update changelog and version if needed
23. **Phase 6 Architecture Review** — Run full checklist from Phase 6, fix any issues
24. **Git commit, push, tag** — As specified in Phase 6.10

---

## AGENT STRATEGY

**Your role**: You are the product manager and lead architect for this feature. You have expert-level skills in Python, FastAPI, React, PX4/MAVSDK, coverage planning algorithms, and military-grade GCS development. You are responsible for the complete 0-to-100 implementation, and the code quality is your personal accountability.

**Use the full power of Claude Code Opus 4.6:**

- **Use Task agents as a team** — Launch parallel agents for independent work streams. Example: while you write the coverage planner, spawn an Explore agent to map all existing MDS patterns you'll need to match. While backend tests run, start on frontend components.
- **Use Explore agents** to deep-search the codebase when you need to find specific patterns, understand how something works, or verify your code matches existing conventions.
- **Use WebSearch** for current documentation (Shapely API, Leaflet-Geoman API, PX4 MissionItem reference, etc.). Do not guess API signatures — verify them.
- **Use TaskCreate/TaskUpdate** to track progress through all 24 implementation steps. Mark each step in_progress before starting and completed when done.
- **Read before writing** — ALWAYS read the target file before editing it. Understand existing code before modifying. This is non-negotiable.
- **Test as you go** — After completing each backend module, run its tests before moving to the next. Do not accumulate untested code.
- **Build incrementally** — Get each layer working before building the next. Verify imports, run the server, check for errors at each checkpoint.
- **Ask the human operator** if you encounter ambiguity not covered in this prompt. Do not make assumptions on critical decisions.

**Decision-making priority when this prompt doesn't cover something:**
1. Most consistent with existing MDS patterns
2. Most aligned with standard PX4/MAVLink behavior
3. Simplest to implement correctly
4. Most extensible for future enhancement
5. Most robust for real-world SAR operation

---

## SUCCESS CRITERIA

The implementation is complete when:

1. A user can open the QuickScout page in the dashboard
2. Draw a polygon search area on the map
3. Select drones and configure survey parameters
4. Click "Compute" and see color-coded coverage paths on the map
5. Click "Launch" and see mission dispatch to drones
6. During execution: see real-time coverage progress, pause/resume individual drones
7. Mark POIs on the map with type/priority/notes
8. Abort mission with RTL for all or selected drones
9. All existing MDS features continue to work unchanged
10. Backend tests pass (`pytest tests/test_sar_*.py`)
11. Documentation exists and is accurate
12. Code follows all MDS conventions and patterns
13. The system works in both SITL and real mode configurations

---

## PHASE 6 — ARCHITECTURE REVIEW & CODE HYGIENE (Final Gate)

**Before declaring the implementation complete, perform a full architecture review.**

This is a self-review checkpoint to ensure the codebase remains clean, manageable, and enterprise-grade. Many AI-assisted codebases degrade into unmaintainable spaghetti — this section prevents that.

### 6.1 File & Module Audit

Run through every file you created or modified. For each file, verify:

- [ ] **Single responsibility**: Each file does ONE thing. `coverage_planner.py` does planning, not API routing. `routes.py` does routing, not business logic.
- [ ] **Consistent imports**: No circular imports. No `sys.path.insert` hacks (follow existing patterns where necessary).
- [ ] **No dead code**: No commented-out blocks, no unused imports, no placeholder functions that do nothing.
- [ ] **No TODO/FIXME without tracking**: If you left any TODO comments, create a corresponding section in the documentation noting it as a known future enhancement.
- [ ] **File size sanity**: No single file > 500 lines. If one grew too large, refactor into sub-modules before finishing.

### 6.2 API Contract Consistency

- [ ] All new endpoints return Pydantic response models (not raw dicts)
- [ ] All request/response schemas have `Field(...)` with `description=` strings
- [ ] All `pos_ids` fields are `List[int]` (not `List[str]`, not `hw_id`)
- [ ] All altitude fields clearly specify datum: MSL or AGL in field name or description
- [ ] All timestamp fields are `int` (Unix ms), matching existing MDS convention
- [ ] Error responses follow `ErrorResponse` schema from `schemas.py`
- [ ] HTTP status codes: 200 for success, 400 for validation errors, 404 for not found, 500 for server errors

### 6.3 Frontend Code Quality

- [ ] No inline styles — use CSS classes or MUI `sx` prop matching existing patterns
- [ ] No hardcoded URLs — all API calls go through `getBackendURL()` or the API service layer
- [ ] React state management is clean: no prop drilling > 2 levels, use context/hooks where needed
- [ ] Component files follow existing size patterns (check: no React component > 400 lines)
- [ ] Loading states handled for all async operations (spinner/skeleton)
- [ ] Error states handled for all API calls (toast notifications matching existing pattern)
- [ ] Map cleanup: all Leaflet layers/listeners removed in `useEffect` cleanup functions

### 6.4 Dependency Audit

- [ ] `requirements.txt` (or relevant Python deps file): Only `shapely` added (if not already present). No other new Python deps.
- [ ] `package.json`: Only `@geoman-io/leaflet-geoman-free` added. No other new JS deps.
- [ ] No pinned versions that conflict with existing deps
- [ ] All imports resolve without error

### 6.5 Integration Points Verification

- [ ] `src/enums.py`: `QUICKSCOUT = 5` added, no other values changed
- [ ] `gcs-server/app_fastapi.py`: SAR router included, no existing routes affected
- [ ] `src/drone_api_server.py`: QUICKSCOUT handler added, no existing handlers changed
- [ ] `App.js`: QuickScout route added, no existing routes changed
- [ ] `SidebarMenu.js`: Menu item added, no existing items changed
- [ ] Existing test suite still passes: `pytest tests/test_gcs_api_http.py tests/test_drone_api_http.py tests/test_command_system.py`

### 6.6 Scalability & Future-Proofing Checklist

- [ ] Coverage planner uses base class pattern → new algorithms plug in without modifying existing code
- [ ] POI types and priority levels are defined as enums/constants → adding new types is a one-line change
- [ ] Survey config parameters have sensible defaults → new params can be added with defaults without breaking existing plans
- [ ] Mission state machine transitions are explicit and documented → new states can be added without ambiguity
- [ ] All SAR code is isolated in `gcs-server/sar/` package and `src/components/sar/` directory → can be enabled/disabled as a module
- [ ] No SAR-specific logic leaked into core MDS files (only integration points: enum, route registration, menu item, command handler)

### 6.7 Run Final Validation

Execute these commands and confirm all pass:

```bash
# Backend tests
cd /opt/mavsdk_drone_show && python -m pytest tests/test_sar_*.py -v

# Existing tests still pass (non-breaking)
python -m pytest tests/test_gcs_api_http.py tests/test_drone_api_http.py -v

# Python import check — all new modules importable
python -c "from gcs_server_path import sar; print('SAR module OK')"

# Frontend builds without errors
cd /opt/mavsdk_drone_show/app/dashboard/drone-dashboard && npm run build

# Lint check (if eslint configured)
npm run lint 2>/dev/null || echo "No lint script configured"
```

If any of these fail, fix the issues before declaring completion.

### 6.8 Operator Experience Review

Put yourself in the shoes of a field operator using this in a real SAR scenario:

1. **Time to first survey**: Can they go from opening the page to having drones in the air surveying in < 3 minutes?
2. **Cognitive load**: Is the UI self-explanatory? Are defaults sensible? Can they launch a mission with minimum clicks?
3. **Error recovery**: If something goes wrong (drone disconnects, API timeout, bad polygon), does the user get a clear, actionable error message — not a stack trace or generic "error"?
4. **Situational awareness**: During mission execution, can the operator instantly see: which drones are where, how much area is covered, which drones are paused, where POIs are?
5. **Abort confidence**: When they hit Abort/RTL, do they trust the system will bring all drones home safely?

If any of these feel weak, improve them before finishing.

### 6.9 Documentation & Code Hygiene Final Sweep

**This is NOT optional. Before the final commit, you MUST ensure zero leftover junk:**

- [ ] **No deprecated code**: Remove any code that was written then replaced during development. No commented-out experiments.
- [ ] **No redundant files**: If you created helper files during development that are no longer needed, delete them.
- [ ] **No stale imports**: Every import in every file you touched must be used.
- [ ] **No orphan constants**: If you defined constants that are no longer referenced, remove them.
- [ ] **Docs are accurate**: Every doc you wrote or updated reflects the FINAL state of the code, not an intermediate state.
- [ ] **Tests match implementation**: If the API signature changed during development, tests must reflect the final signature.
- [ ] **CHANGELOG.md updated**: Add a version entry (e.g., v4.6.0 or v5.0.0 — match project versioning convention) with a clear description of what QuickScout adds.
- [ ] **No "TODO" without tracking**: Grep for `TODO`, `FIXME`, `HACK`, `XXX` in all new files. Either resolve them or document in `docs/features/quickscout.md` under a "Known Limitations & Future Work" section.
- [ ] **package.json version**: Update if the project convention bumps version on new features.
- [ ] **No secrets or debug artifacts**: No `console.log` debug statements in frontend (use proper conditional logging). No hardcoded test data in production code.

### 6.10 Git Commit, Push, and Tag

After ALL of the above checks pass:

```bash
# Stage all new and modified files
cd /opt/mavsdk_drone_show
git add -A

# Create a clean, descriptive commit
git commit -m "feat: QuickScout cooperative multi-drone SAR/reconnaissance module

- New mission type QUICKSCOUT (5) with PX4 Mission Mode flight execution
- Coverage path planning: boustrophedon algorithm with multi-drone cooperative sector partitioning
- GCS API: 12 new endpoints under /api/sar/ (plan, launch, pause, resume, abort, POI CRUD)
- Dashboard: Single-page QuickScout planner with Plan/Monitor mode toggle
- Map-based search area drawing (Leaflet-Geoman), coverage preview, POI marking system
- Terrain-following altitude computation, auto-fill from elevation data
- PX4 native camera auto-interval capture during survey legs
- Per-drone and fleet-wide mission control (pause/resume/RTL/abort)
- Drone status cards with real-time coverage progress
- Backend unit tests for coverage planner, API endpoints, schema validation
- Feature documentation, API reference, SITL testing guide

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# Push to main-candidate branch
git push origin main-candidate

# Create annotated tag
git tag -a quickscout-v1.0.0 -m "QuickScout SAR/Reconnaissance Module v1.0.0 - Initial release"
git push origin quickscout-v1.0.0
```

**IMPORTANT**: Do NOT force push. Do NOT amend previous commits. Do NOT push to `main` branch (only `main-candidate`). If there are merge conflicts, resolve them properly — do not discard changes.
