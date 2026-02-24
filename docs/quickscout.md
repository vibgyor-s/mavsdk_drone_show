# QuickScout - SAR/Reconnaissance Module

Multi-drone cooperative area survey using boustrophedon (lawn-mower) coverage path planning with PX4 Mission Mode execution.

## Overview

QuickScout adds a new mission mode (`QUICKSCOUT = 5`) for Search and Rescue (SAR) and reconnaissance operations. The GCS computes optimal coverage paths, partitions them across available drones, and each drone executes its assigned sector autonomously via PX4 Mission Mode.

## Architecture

```
GCS Dashboard (React)               GCS Server (FastAPI)                Drone (PX4)
  QuickScoutPage.js          -->    POST /api/sar/mission/plan    -->  coverage_planner.py
  Draw polygon + config             BoustrophedonPlanner                Compute paths
  Review coverage preview           Partition & assign sectors

  Click "Launch"             -->    POST /api/sar/mission/launch  -->  drone_communicator.py
                                    send_commands_to_selected()         Write waypoints JSON
                                                                        drone_setup.py
                                                                        quickscout_mission.py
                                                                        (PX4 Mission upload)

  Monitor progress           <--    GET /api/sar/mission/{id}/status
  DroneStatusCards                  mission_manager.py            <--  POST /progress reports
  POI markers                       poi_manager.py
```

## Algorithm: Boustrophedon Coverage

1. Convert polygon vertices from lat/lng to local ENU (East-North-Up) coordinates using `pymap3d`
2. Create a Shapely polygon from ENU coordinates
3. Generate parallel sweep lines across the polygon's bounding box (spaced by `sweep_width_m * (1 - overlap_percent/100)`)
4. Clip sweep lines to the polygon boundary
5. Connect clipped segments in alternating direction (boustrophedon/lawn-mower pattern)
6. For N drones: partition waypoints into N roughly-equal sectors
7. Assign sectors to drones by GPS proximity (greedy nearest-match)
8. Convert ENU waypoints back to lat/lng with altitude

## API Endpoints

All endpoints are prefixed with `/api/sar`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/mission/plan` | Compute coverage plan for a search area |
| POST | `/mission/launch` | Launch a planned mission to drones |
| GET | `/mission/{id}/status` | Get mission status and drone progress |
| POST | `/mission/{id}/pause` | Pause executing drones |
| POST | `/mission/{id}/resume` | Resume paused drones |
| POST | `/mission/{id}/abort` | Abort mission with return behavior |
| POST | `/mission/{id}/progress` | Drone progress report (from drone) |
| POST | `/poi` | Create a Point of Interest |
| GET | `/poi` | List POIs for a mission |
| PATCH | `/poi/{id}` | Update a POI |
| DELETE | `/poi/{id}` | Delete a POI |
| POST | `/elevation/batch` | Batch terrain elevation lookup |

## Configuration

### Survey Parameters (SurveyConfig)

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `sweep_width_m` | 30.0 | 0-500 | Width between sweep lines (meters) |
| `overlap_percent` | 10.0 | 0-50 | Overlap between adjacent sweeps |
| `cruise_altitude_msl` | 50.0 | 0-500 | Transit altitude MSL (meters) |
| `survey_altitude_agl` | 40.0 | 0-300 | Survey altitude AGL (meters) |
| `cruise_speed_ms` | 10.0 | 0-25 | Transit speed (m/s) |
| `survey_speed_ms` | 5.0 | 0-15 | Survey speed (m/s) |
| `camera_interval_s` | 2.0 | 0-30 | Camera capture interval (seconds) |
| `use_terrain_following` | true | - | Adjust altitude for terrain |

### Return Behaviors

- `return_home` (default): RTL after survey completion
- `land_current`: Land at current position
- `hold_position`: Hold/loiter at last waypoint

## Dependencies

**GCS Server only** (not needed on drones):
- `shapely>=2.0.0` - Polygon operations and sweep line clipping
- `pymap3d` - Coordinate conversions (lat/lng <-> ENU)

**Frontend**:
- `@mapbox/mapbox-gl-draw` - Polygon drawing on map
- `react-map-gl` / `mapbox-gl` - Map rendering (existing dependency)

## Frontend

The QuickScout page is accessible from the sidebar menu and provides two modes:

- **Plan Mode**: Draw search area polygon, configure survey parameters, select drones, compute and preview coverage paths
- **Monitor Mode**: Real-time drone progress cards, coverage percentage, elapsed time, POI management

The map view shows coverage paths color-coded per drone (solid for survey legs, dashed for transit).

## File Structure

```
gcs-server/sar/
  __init__.py
  schemas.py              # Pydantic models
  coverage_planner.py     # Boustrophedon algorithm
  terrain.py              # Terrain elevation helpers
  mission_manager.py      # Mission lifecycle (singleton)
  poi_manager.py          # POI CRUD (singleton)
  routes.py               # FastAPI APIRouter

quickscout_mission.py     # Drone-side PX4 mission executor

app/dashboard/drone-dashboard/src/
  pages/QuickScoutPage.js
  components/sar/          # All SAR UI components
  services/sarApiService.js
  styles/QuickScout.css

tests/
  test_sar_schemas.py
  test_sar_coverage_planner.py
  test_sar_api.py
```

## Drone-Side Execution

The drone receives waypoints via the standard command dispatch flow:

1. GCS sends QUICKSCOUT command with waypoints array
2. `drone_communicator.py` writes waypoints to `/tmp/quickscout_{hw_id}_{mission_id}.json`
3. `drone_setup.py` launches `quickscout_mission.py` as a subprocess
4. `quickscout_mission.py`:
   - Connects to PX4 via MAVSDK
   - Builds `MissionItem` list from waypoints (with camera actions)
   - Uploads mission, arms, and starts
   - Monitors progress and reports to GCS via POST `/api/sar/mission/{id}/progress`
   - LED feedback: blue (init) -> yellow (upload) -> white (executing) -> green (complete)
