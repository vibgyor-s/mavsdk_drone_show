# gcs-server/sar/routes.py
"""
QuickScout SAR - API Routes

FastAPI APIRouter for all SAR endpoints.
"""

import os
import sys
import uuid
import time
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sar.schemas import (
    QuickScoutMissionRequest, CoveragePlanResponse, MissionStatus,
    POI, DroneProgressReport,
)
from sar.coverage_planner import BoustrophedonPlanner
from sar.terrain import apply_terrain_following, batch_get_elevations
from sar.mission_manager import get_mission_manager
from sar.poi_manager import get_poi_manager

from telemetry import telemetry_data_all_drones, data_lock as telemetry_lock
from config import load_config
from command import send_commands_to_selected
from enums import Mission
from mds_logging import get_logger

logger = get_logger("sar_routes")

router = APIRouter(prefix="/api/sar", tags=["QuickScout SAR"])


def _resolve_pos_ids_to_hw_ids(pos_ids: Optional[List[int]]) -> Optional[List[str]]:
    """Resolve pos_ids to hw_ids using drone config. Returns None if pos_ids is None (= all drones)."""
    if pos_ids is None:
        return None
    try:
        drones_config = load_config()
        hw_ids = []
        for d in drones_config:
            pid = int(d.get('pos_id', -1))
            if pid in pos_ids:
                hw_ids.append(str(d.get('hw_id', '')))
        return hw_ids if hw_ids else [str(p) for p in pos_ids]  # Fallback: treat pos_ids as hw_ids
    except Exception:
        return [str(p) for p in pos_ids]


def _send_control_command(mission_type_value: int, hw_ids: Optional[List[str]] = None):
    """Send a control command (HOLD, RTL, etc.) to drones via MDS command infrastructure."""
    try:
        drones_config = load_config()
    except Exception as e:
        logger.error(f"Failed to load drone config for control command: {e}")
        return
    if hw_ids is None:
        target_ids = [str(d.get('hw_id', '')) for d in drones_config]
    else:
        target_ids = hw_ids
    command_data = {'missionType': mission_type_value}
    for hw_id in target_ids:
        try:
            send_commands_to_selected(drones_config, command_data, [hw_id])
        except Exception as e:
            logger.warning(f"Control command {mission_type_value} to {hw_id} failed: {e}")


def _get_drone_gps_positions(pos_ids: Optional[List[int]] = None) -> dict:
    """Get current GPS positions from telemetry. Returns {pos_id_str: (lat, lng)}."""
    positions = {}
    with telemetry_lock:
        for hw_id, data in telemetry_data_all_drones.items():
            if not data:
                continue
            lat = data.get('position_lat')
            lng = data.get('position_long')
            pos_id = data.get('pos_id')
            if lat is not None and lng is not None and pos_id is not None:
                if pos_ids is None or int(pos_id) in pos_ids:
                    positions[str(pos_id)] = (float(lat), float(lng))
    if not positions:
        try:
            drones = load_config()
            for d in drones:
                pid = int(d.get('pos_id', -1))
                if pos_ids is None or pid in pos_ids:
                    positions[str(pid)] = (0.0, 0.0)
        except Exception:
            pass
    return positions


@router.post("/mission/plan", response_model=CoveragePlanResponse)
async def plan_mission(request: QuickScoutMissionRequest):
    """Compute coverage plan without launching."""
    try:
        drone_positions = _get_drone_gps_positions(request.pos_ids)
        if not drone_positions:
            raise HTTPException(status_code=400, detail="No drones available for mission planning")

        planner = BoustrophedonPlanner()
        plans, total_area = planner.plan(
            polygon_points=request.search_area.points,
            drone_positions=drone_positions,
            config=request.survey_config,
        )
        if not plans:
            raise HTTPException(status_code=400, detail="Coverage planning produced no plans")

        if request.survey_config.use_terrain_following:
            for plan in plans:
                plan.waypoints = await apply_terrain_following(
                    plan.waypoints,
                    request.survey_config.survey_altitude_agl,
                    request.survey_config.cruise_altitude_msl,
                )

        try:
            drones_config = load_config()
            hw_map = {str(d.get('pos_id', '')): str(d.get('hw_id', '')) for d in drones_config}
            for plan in plans:
                if str(plan.pos_id) in hw_map:
                    plan.hw_id = hw_map[str(plan.pos_id)]
        except Exception:
            pass

        mission_id = str(uuid.uuid4())
        est_time = max((p.estimated_duration_s for p in plans), default=0)

        manager = get_mission_manager()
        manager.create_mission(mission_id, plans, request.survey_config)

        return CoveragePlanResponse(
            mission_id=mission_id, plans=plans, total_area_sq_m=total_area,
            estimated_coverage_time_s=est_time, algorithm_used=request.survey_config.algorithm,
        )
    except HTTPException:
        raise
    except ImportError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Coverage planning failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Coverage planning failed: {str(e)}")


@router.post("/mission/launch")
async def launch_mission(mission_id: str = Query(..., description="Mission ID to launch")):
    """Launch a previously planned mission."""
    manager = get_mission_manager()
    plans = manager.get_plans(mission_id)
    config = manager.get_config(mission_id)
    if not plans:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")

    try:
        drones_config = load_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load drone config: {e}")

    trigger_time = int(time.time()) + 5
    return_behavior = config.return_behavior if config and hasattr(config, 'return_behavior') else 'return_home'
    successes = 0
    failures = 0

    for plan in plans:
        waypoints_data = [wp.model_dump() for wp in plan.waypoints]
        command_data = {
            'missionType': Mission.QUICKSCOUT.value,
            'triggerTime': trigger_time,
            'mission_id': mission_id,
            'waypoints': waypoints_data,
            'return_behavior': return_behavior,
            'survey_config': config.model_dump() if config else {},
        }
        hw_id = plan.hw_id
        try:
            result = send_commands_to_selected(drones_config, command_data, [hw_id])
            logger.info(f"Command sent to drone {hw_id}: {result.get('result_summary', 'unknown')}")
            successes += 1
        except Exception as e:
            logger.error(f"Failed to send command to drone {hw_id}: {e}")
            failures += 1

    if successes == 0:
        raise HTTPException(
            status_code=502,
            detail=f"All {failures} drone(s) failed to accept mission command"
        )

    manager.start_mission(mission_id)
    return {
        "success": True, "mission_id": mission_id,
        "drones_launched": successes, "drones_failed": failures,
        "trigger_time": trigger_time,
        "message": f"Mission launched with {successes}/{successes + failures} drones",
    }


@router.get("/mission/{mission_id}/status", response_model=MissionStatus)
async def get_mission_status(mission_id: str):
    manager = get_mission_manager()
    status = manager.get_status(mission_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    return status


@router.post("/mission/{mission_id}/pause")
async def pause_mission(mission_id: str, pos_ids: Optional[List[int]] = Query(None)):
    hw_ids = _resolve_pos_ids_to_hw_ids(pos_ids)
    manager = get_mission_manager()
    if not manager.pause_mission(mission_id, hw_ids):
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    # Send HOLD command to actual drones
    _send_control_command(Mission.HOLD.value, hw_ids)
    return {"success": True, "message": "Mission paused"}


@router.post("/mission/{mission_id}/resume")
async def resume_mission(mission_id: str, pos_ids: Optional[List[int]] = Query(None)):
    hw_ids = _resolve_pos_ids_to_hw_ids(pos_ids)
    manager = get_mission_manager()
    if not manager.resume_mission(mission_id, hw_ids):
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    # Note: PX4 Mission Mode resume from HOLD requires drone.mission.start_mission()
    # For PoC, the operator can re-arm the mission from the flight controller.
    # Full resume support requires drone-side command handler extension.
    return {"success": True, "message": "Mission resumed (GCS state updated, drone resume requires FC interaction)"}


@router.post("/mission/{mission_id}/abort")
async def abort_mission(mission_id: str, pos_ids: Optional[List[int]] = Query(None), return_behavior: str = Query("return_home")):
    hw_ids = _resolve_pos_ids_to_hw_ids(pos_ids)
    manager = get_mission_manager()
    if not manager.abort_mission(mission_id, hw_ids, return_behavior):
        raise HTTPException(status_code=404, detail=f"Mission {mission_id} not found")
    # Send RTL command to actual drones
    _send_control_command(Mission.RETURN_RTL.value, hw_ids)
    return {"success": True, "message": "Mission aborted", "return_behavior": return_behavior}


@router.post("/mission/{mission_id}/progress")
async def report_progress(mission_id: str, report: DroneProgressReport):
    manager = get_mission_manager()
    success = manager.update_drone_progress(
        mission_id=mission_id, hw_id=report.hw_id,
        current_waypoint_index=report.current_waypoint_index,
        total_waypoints=report.total_waypoints,
        distance_covered_m=report.distance_covered_m, state=report.state,
    )
    if not success:
        raise HTTPException(status_code=404, detail="Mission or drone not found")
    return {"success": True}


@router.post("/poi", response_model=POI)
async def create_poi(poi: POI, mission_id: str = Query(..., description="Mission ID")):
    return get_poi_manager().add_poi(mission_id, poi)


@router.get("/poi", response_model=List[POI])
async def list_pois(mission_id: str = Query(..., description="Mission ID")):
    return get_poi_manager().get_pois(mission_id)


@router.patch("/poi/{poi_id}", response_model=POI)
async def update_poi(poi_id: str, updates: dict):
    poi = get_poi_manager().update_poi(poi_id, updates)
    if not poi:
        raise HTTPException(status_code=404, detail=f"POI {poi_id} not found")
    return poi


@router.delete("/poi/{poi_id}")
async def delete_poi(poi_id: str):
    if not get_poi_manager().delete_poi(poi_id):
        raise HTTPException(status_code=404, detail=f"POI {poi_id} not found")
    return {"success": True, "message": f"POI {poi_id} deleted"}


@router.post("/elevation/batch")
async def batch_elevation(points: List[dict]):
    try:
        elevations = await batch_get_elevations(points)
        return {"elevations": elevations, "count": len(elevations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Elevation query failed: {str(e)}")
