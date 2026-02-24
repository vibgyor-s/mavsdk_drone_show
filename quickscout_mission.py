#!/usr/bin/env python3
"""
QuickScout Mission Script

Executes a survey mission using PX4 Mission Mode.
Receives pre-computed waypoints from GCS, uploads as MAVSDK Mission items,
arms, and starts autonomous mission execution. Reports progress back to GCS.

Usage:
    python quickscout_mission.py --waypoints-file PATH --mission-id ID --hw-id HW_ID --return-behavior RTL
"""

import os
import sys
import json
import time
import asyncio
import logging
import argparse
import math

import requests
from mavsdk import System
from mavsdk.mission import MissionItem, MissionPlan

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from params import Params
from led_controller import LEDController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [QuickScout] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description='QuickScout Mission Executor')
    parser.add_argument('--waypoints-file', required=True, help='Path to waypoints JSON file')
    parser.add_argument('--mission-id', required=True, help='Mission ID for progress reporting')
    parser.add_argument('--hw-id', required=True, help='Hardware ID of this drone')
    parser.add_argument('--return-behavior', default='return_home',
                        choices=['return_home', 'land_current', 'hold_position'],
                        help='End-of-mission behavior')
    parser.add_argument('--gcs-url', default=None, help='GCS server URL for progress reports')
    return parser.parse_args()


def load_waypoints(filepath):
    """Load waypoints from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def report_progress(gcs_url, mission_id, hw_id, waypoint_index, total_waypoints, distance_m=0, state=None):
    """Report progress to GCS server (best-effort, non-blocking)."""
    if not gcs_url:
        return
    try:
        data = {
            'hw_id': hw_id,
            'current_waypoint_index': waypoint_index,
            'total_waypoints': total_waypoints,
            'distance_covered_m': distance_m,
        }
        if state:
            data['state'] = state
        requests.post(
            f"{gcs_url}/api/sar/mission/{mission_id}/progress",
            json=data, timeout=2
        )
    except Exception:
        pass


async def run_mission(args):
    """Main mission execution."""
    led = None
    try:
        led = LEDController.get_instance()
    except Exception:
        logger.warning("LED controller not available")

    if led:
        led.set_color(0, 0, 255)  # Blue: initializing

    logger.info(f"Loading waypoints from {args.waypoints_file}")
    waypoints = load_waypoints(args.waypoints_file)
    total_waypoints = len(waypoints)
    logger.info(f"Loaded {total_waypoints} waypoints for mission {args.mission_id}")

    if total_waypoints == 0:
        logger.error("No waypoints to execute")
        return 1

    gcs_url = args.gcs_url
    if not gcs_url:
        gcs_ip = os.environ.get('GCS_IP', '127.0.0.1')
        gcs_port = getattr(Params, 'gcs_port', 5000)
        gcs_url = f"http://{gcs_ip}:{gcs_port}"

    grpc_port = getattr(Params, 'mavsdk_grpc_port', 50051)
    drone = System(mavsdk_server_address="127.0.0.1", port=grpc_port)
    await drone.connect(system_address=f"udp://:{Params.mavsdk_port}")

    logger.info(f"Connecting to drone via MAVSDK on gRPC port {grpc_port}")

    logger.info("Waiting for drone connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            logger.info("Drone connected")
            break

    logger.info("Waiting for GPS fix...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            logger.info("GPS fix and home position OK")
            break

    home_position = None
    async for pos in drone.telemetry.home():
        home_position = pos
        break

    if not home_position:
        logger.error("Failed to get home position")
        return 1

    home_alt_msl = home_position.absolute_altitude_m
    logger.info(f"Home position: {home_position.latitude_deg:.6f}, {home_position.longitude_deg:.6f}, alt={home_alt_msl:.1f}m MSL")

    if led:
        led.set_color(255, 255, 0)  # Yellow: building mission

    MIN_SURVEY_ALT_AGL = 10.0  # Safety floor: minimum relative altitude (meters)
    mission_items = []
    camera_running = False
    for i, wp in enumerate(waypoints):
        lat = wp['lat']
        lng = wp['lng']
        alt_msl = wp.get('alt_msl', 50.0)
        is_survey = wp.get('is_survey_leg', True)
        speed = wp.get('speed_ms', 5.0)
        yaw = wp.get('yaw_deg', float('nan'))

        relative_alt = alt_msl - home_alt_msl

        # Camera control: start on first survey waypoint, stop when leaving survey
        camera_action = MissionItem.CameraAction.NONE
        if is_survey and not camera_running:
            camera_action = MissionItem.CameraAction.START_PHOTO_INTERVAL
            camera_running = True
        elif not is_survey and camera_running:
            camera_action = MissionItem.CameraAction.STOP_PHOTO_INTERVAL
            camera_running = False

        camera_interval = wp.get('camera_interval_s', 2.0) if camera_action == MissionItem.CameraAction.START_PHOTO_INTERVAL else float('nan')

        item = MissionItem(
            latitude_deg=lat,
            longitude_deg=lng,
            relative_altitude_m=max(relative_alt, MIN_SURVEY_ALT_AGL),
            speed_m_s=speed,
            is_fly_through=True,
            gimbal_pitch_deg=float('nan'),
            gimbal_yaw_deg=float('nan'),
            camera_action=camera_action,
            loiter_time_s=float('nan'),
            camera_photo_interval_s=camera_interval,
            acceptance_radius_m=3.0,
            yaw_deg=yaw,
            camera_photo_distance_m=float('nan'),
        )
        mission_items.append(item)

    logger.info(f"Uploading mission with {len(mission_items)} items...")
    mission_plan = MissionPlan(mission_items)

    try:
        await drone.mission.upload_mission(mission_plan)
        logger.info("Mission uploaded successfully")
    except Exception as e:
        logger.error(f"Mission upload failed: {e}")
        if led:
            led.set_color(255, 0, 0)
        return 1

    if led:
        led.set_color(255, 255, 255)  # White: ready

    logger.info("Arming drone...")
    try:
        await drone.action.arm()
        logger.info("Drone armed")
    except Exception as e:
        logger.error(f"Arming failed: {e}")
        if led:
            led.set_color(255, 0, 0)
        return 1

    logger.info("Starting mission...")
    try:
        await drone.mission.start_mission()
        logger.info("Mission started")
    except Exception as e:
        logger.error(f"Mission start failed: {e}")
        if led:
            led.set_color(255, 0, 0)
        return 1

    report_progress(gcs_url, args.mission_id, args.hw_id, 0, total_waypoints, state='executing')

    if led:
        led.set_color(0, 255, 0)  # Green: surveying

    distance_covered = 0.0
    last_wp_index = -1

    async for progress in drone.mission.mission_progress():
        current = progress.current
        total = progress.total

        if current != last_wp_index:
            logger.info(f"Mission progress: waypoint {current}/{total}")
            if last_wp_index >= 0 and last_wp_index < len(waypoints) and current < len(waypoints):
                wp_prev = waypoints[last_wp_index]
                wp_curr = waypoints[min(current, len(waypoints) - 1)]
                dlat = math.radians(wp_curr['lat'] - wp_prev['lat'])
                dlng = math.radians(wp_curr['lng'] - wp_prev['lng'])
                a = (math.sin(dlat/2)**2 +
                     math.cos(math.radians(wp_prev['lat'])) * math.cos(math.radians(wp_curr['lat'])) *
                     math.sin(dlng/2)**2)
                distance_covered += 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
            last_wp_index = current
            report_progress(gcs_url, args.mission_id, args.hw_id, current, total, distance_covered)

        if current >= total - 1 and total > 0:
            logger.info("Mission waypoints complete")
            break

    logger.info(f"Mission complete. Total distance: {distance_covered:.0f}m")
    report_progress(gcs_url, args.mission_id, args.hw_id, total_waypoints, total_waypoints, distance_covered, state='completed')

    if args.return_behavior == 'return_home':
        logger.info("Returning to home...")
        await drone.action.return_to_launch()
    elif args.return_behavior == 'land_current':
        logger.info("Landing at current position...")
        await drone.action.land()
    elif args.return_behavior == 'hold_position':
        logger.info("Holding position...")

    if args.return_behavior in ('return_home', 'land_current'):
        from mavsdk.telemetry import LandedState
        async for landed_state in drone.telemetry.landed_state():
            if landed_state == LandedState.ON_GROUND:
                logger.info("Drone landed")
                break
        try:
            await drone.action.disarm()
            logger.info("Drone disarmed")
        except Exception:
            pass

    if led:
        led.set_color(0, 255, 255)  # Cyan: complete

    logger.info("QuickScout mission completed successfully")
    return 0


def main():
    args = parse_args()
    exit_code = asyncio.run(run_mission(args))
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
