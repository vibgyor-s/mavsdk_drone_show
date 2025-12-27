# tests/fixtures/mission_samples.py
"""
Mission Sample Fixtures
=======================
Pre-built mission configurations for testing mission execution.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

# Path configuration is handled by conftest.py
from src.enums import Mission as MissionEnum, State as StateEnum


# ============================================================================
# Mission State Constants (imported from src/enums.py)
# ============================================================================

class MissionState:
    """Mission state constants - wrapper for src.enums.State"""
    IDLE = StateEnum.IDLE.value
    MISSION_READY = StateEnum.MISSION_READY.value
    MISSION_EXECUTING = StateEnum.MISSION_EXECUTING.value
    UNKNOWN = StateEnum.UNKNOWN.value


class Mission:
    """Mission type constants - wrapper for src.enums.Mission"""
    NONE = MissionEnum.NONE.value
    DRONE_SHOW_FROM_CSV = MissionEnum.DRONE_SHOW_FROM_CSV.value
    SMART_SWARM = MissionEnum.SMART_SWARM.value
    CUSTOM_CSV_DRONE_SHOW = MissionEnum.CUSTOM_CSV_DRONE_SHOW.value
    SWARM_TRAJECTORY = MissionEnum.SWARM_TRAJECTORY.value
    REBOOT_FC = MissionEnum.REBOOT_FC.value
    REBOOT_SYS = MissionEnum.REBOOT_SYS.value
    TEST_LED = MissionEnum.TEST_LED.value
    TAKE_OFF = MissionEnum.TAKE_OFF.value
    TEST = MissionEnum.TEST.value
    LAND = MissionEnum.LAND.value
    HOLD = MissionEnum.HOLD.value
    UPDATE_CODE = MissionEnum.UPDATE_CODE.value
    RETURN_RTL = MissionEnum.RETURN_RTL.value
    KILL_TERMINATE = MissionEnum.KILL_TERMINATE.value
    HOVER_TEST = MissionEnum.HOVER_TEST.value
    INIT_SYSID = MissionEnum.INIT_SYSID.value
    APPLY_COMMON_PARAMS = MissionEnum.APPLY_COMMON_PARAMS.value


# ============================================================================
# Mission Configuration Builder
# ============================================================================

@dataclass
class MissionConfig:
    """Configuration for a mission"""
    mission_type: int
    trigger_time: int
    takeoff_altitude: float = 10.0
    auto_global_origin: bool = False
    use_global_setpoints: bool = False
    origin: Optional[Dict[str, float]] = None
    target_drones: Optional[List[int]] = None

    def to_drone_setup_params(self) -> Dict[str, Any]:
        """Convert to parameters for DroneSetup"""
        params = {
            'mission': self.mission_type,
            'trigger_time': self.trigger_time,
            'takeoff_altitude': self.takeoff_altitude,
            'auto_global_origin': self.auto_global_origin,
            'use_global_setpoints': self.use_global_setpoints,
        }
        if self.origin:
            params['origin'] = self.origin
        if self.target_drones:
            params['target_drones'] = self.target_drones
        return params


# ============================================================================
# Trajectory Data
# ============================================================================

def sample_trajectory_csv() -> str:
    """Generate sample trajectory CSV data"""
    # Header
    header = "t,px,py,pz,vx,vy,vz,ax,ay,az,yaw,r,g,b,w"

    # Waypoints: takeoff, hover, move, return, land
    # Format: time(s), pos_x(m), pos_y(m), pos_z(m), vel_xyz, acc_xyz, yaw, RGBW colors
    waypoints = [
        "0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,255,0,0,0",      # Start
        "5.0,0.0,0.0,10.0,0.0,0.0,2.0,0.0,0.0,0.0,0.0,0,255,0,0",     # Takeoff
        "10.0,0.0,0.0,10.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,0,255,0",    # Hover
        "20.0,10.0,0.0,10.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,255,255,0,0", # Move
        "30.0,10.0,10.0,10.0,0.0,1.0,0.0,0.0,0.0,0.0,90.0,255,0,255,0", # Move
        "40.0,0.0,0.0,10.0,-1.0,-1.0,0.0,0.0,0.0,0.0,180.0,0,255,255,0", # Return
        "50.0,0.0,0.0,0.0,0.0,0.0,-2.0,0.0,0.0,0.0,0.0,255,255,255,0",  # Land
    ]

    return header + "\n" + "\n".join(waypoints)


def hover_test_trajectory_csv() -> str:
    """Generate hover test trajectory CSV"""
    header = "t,px,py,pz,vx,vy,vz,ax,ay,az,yaw,r,g,b,w"
    waypoints = [
        "0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,0,0,0",
        "10.0,0.0,0.0,10.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,255,255,255,0",
        "60.0,0.0,0.0,10.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,255,255,255,0",
        "70.0,0.0,0.0,0.0,0.0,0.0,-1.0,0.0,0.0,0.0,0.0,0,0,0,0",
    ]
    return header + "\n" + "\n".join(waypoints)


def swarm_leader_trajectory_csv() -> str:
    """Generate swarm leader trajectory CSV"""
    header = "t,px,py,pz,vx,vy,vz,ax,ay,az,yaw,r,g,b,w"
    waypoints = [
        "0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,255,0,0,0",
        "10.0,0.0,0.0,15.0,0.0,0.0,1.5,0.0,0.0,0.0,0.0,0,255,0,0",
        "30.0,20.0,0.0,15.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0,0,0,255,0",
        "50.0,20.0,20.0,15.0,0.0,1.0,0.0,0.0,0.0,0.0,90.0,255,255,0,0",
        "70.0,0.0,0.0,15.0,-1.0,-1.0,0.0,0.0,0.0,0.0,180.0,255,0,255,0",
        "90.0,0.0,0.0,0.0,0.0,0.0,-1.5,0.0,0.0,0.0,0.0,0,0,0,0",
    ]
    return header + "\n" + "\n".join(waypoints)


# ============================================================================
# Pre-built Mission Configurations
# ============================================================================

def mission_idle() -> MissionConfig:
    """Idle mission (no operation)"""
    return MissionConfig(
        mission_type=Mission.NONE,
        trigger_time=0
    )


def mission_takeoff(altitude: float = 10.0, delay_seconds: int = 5) -> MissionConfig:
    """Takeoff mission"""
    return MissionConfig(
        mission_type=Mission.TAKE_OFF,
        trigger_time=int(time.time()) + delay_seconds,
        takeoff_altitude=altitude
    )


def mission_land(delay_seconds: int = 5) -> MissionConfig:
    """Landing mission"""
    return MissionConfig(
        mission_type=Mission.LAND,
        trigger_time=int(time.time()) + delay_seconds
    )


def mission_hold(delay_seconds: int = 5) -> MissionConfig:
    """Hold position mission"""
    return MissionConfig(
        mission_type=Mission.HOLD,
        trigger_time=int(time.time()) + delay_seconds
    )


def mission_rtl(delay_seconds: int = 5) -> MissionConfig:
    """Return to launch mission"""
    return MissionConfig(
        mission_type=Mission.RETURN_RTL,
        trigger_time=int(time.time()) + delay_seconds
    )


def mission_drone_show(delay_seconds: int = 10) -> MissionConfig:
    """Drone show from CSV mission"""
    return MissionConfig(
        mission_type=Mission.DRONE_SHOW_FROM_CSV,
        trigger_time=int(time.time()) + delay_seconds,
        auto_global_origin=True,
        use_global_setpoints=True,
        origin={
            'lat': 47.397742,
            'lon': 8.545594,
            'alt': 488.0
        }
    )


def mission_smart_swarm(delay_seconds: int = 10) -> MissionConfig:
    """Smart swarm mission"""
    return MissionConfig(
        mission_type=Mission.SMART_SWARM,
        trigger_time=int(time.time()) + delay_seconds
    )


def mission_swarm_trajectory(delay_seconds: int = 10) -> MissionConfig:
    """Swarm trajectory mission"""
    return MissionConfig(
        mission_type=Mission.SWARM_TRAJECTORY,
        trigger_time=int(time.time()) + delay_seconds,
        auto_global_origin=True,
        origin={
            'lat': 47.397742,
            'lon': 8.545594,
            'alt': 488.0
        }
    )


def mission_hover_test(delay_seconds: int = 10) -> MissionConfig:
    """Hover test mission"""
    return MissionConfig(
        mission_type=Mission.HOVER_TEST,
        trigger_time=int(time.time()) + delay_seconds,
        takeoff_altitude=10.0
    )


def mission_emergency_kill() -> MissionConfig:
    """Emergency kill mission (immediate)"""
    return MissionConfig(
        mission_type=Mission.KILL_TERMINATE,
        trigger_time=int(time.time())  # Immediate
    )


# ============================================================================
# Mission Scenario Builders
# ============================================================================

def mission_sequence_basic() -> List[MissionConfig]:
    """Basic mission sequence: takeoff -> hover -> land"""
    now = int(time.time())
    return [
        MissionConfig(Mission.TAKE_OFF, now + 5, takeoff_altitude=10.0),
        MissionConfig(Mission.HOLD, now + 20),
        MissionConfig(Mission.LAND, now + 35),
    ]


def mission_sequence_show() -> List[MissionConfig]:
    """Full show sequence"""
    now = int(time.time())
    return [
        MissionConfig(
            Mission.DRONE_SHOW_FROM_CSV,
            now + 10,
            auto_global_origin=True,
            origin={'lat': 47.397742, 'lon': 8.545594, 'alt': 488.0}
        ),
        MissionConfig(Mission.RTL, now + 120),
    ]


def mission_sequence_swarm() -> List[MissionConfig]:
    """Swarm mission sequence"""
    now = int(time.time())
    return [
        MissionConfig(Mission.SMART_SWARM, now + 10),
        MissionConfig(Mission.HOLD, now + 60),
        MissionConfig(Mission.LAND, now + 75),
    ]


# ============================================================================
# Origin Data
# ============================================================================

def origin_zurich() -> Dict[str, Any]:
    """Zurich test origin"""
    return {
        'lat': 47.397742,
        'lon': 8.545594,
        'alt': 488.0,
        'alt_source': 'manual',
        'timestamp': '2025-12-27T10:00:00Z',
        'version': 2
    }


def origin_sf() -> Dict[str, Any]:
    """San Francisco test origin"""
    return {
        'lat': 37.7749,
        'lon': -122.4194,
        'alt': 10.0,
        'alt_source': 'elevation_api',
        'timestamp': '2025-12-27T10:00:00Z',
        'version': 2
    }


def origin_invalid() -> Dict[str, Any]:
    """Invalid origin data"""
    return {
        'lat': 999.0,
        'lon': 999.0,
        'alt': -9999.0
    }


# ============================================================================
# Swarm Configuration Samples
# ============================================================================

def swarm_config_single_leader() -> List[Dict[str, Any]]:
    """Swarm config with single leader"""
    return [
        {'hw_id': '1', 'follow': 0, 'offset_n': 0, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '2', 'follow': 1, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '3', 'follow': 1, 'offset_n': -5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '4', 'follow': 1, 'offset_n': 0, 'offset_e': 5, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '5', 'follow': 1, 'offset_n': 0, 'offset_e': -5, 'offset_alt': 0, 'body_coord': 0},
    ]


def swarm_config_multi_leader() -> List[Dict[str, Any]]:
    """Swarm config with multiple leaders"""
    return [
        {'hw_id': '1', 'follow': 0, 'offset_n': 0, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '2', 'follow': 0, 'offset_n': 0, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '3', 'follow': 1, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
        {'hw_id': '4', 'follow': 1, 'offset_n': -5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
        {'hw_id': '5', 'follow': 2, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
        {'hw_id': '6', 'follow': 2, 'offset_n': -5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
    ]


def swarm_config_chain() -> List[Dict[str, Any]]:
    """Swarm config with chain following"""
    return [
        {'hw_id': '1', 'follow': 0, 'offset_n': 0, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 0},
        {'hw_id': '2', 'follow': 1, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
        {'hw_id': '3', 'follow': 2, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
        {'hw_id': '4', 'follow': 3, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
        {'hw_id': '5', 'follow': 4, 'offset_n': 5, 'offset_e': 0, 'offset_alt': 0, 'body_coord': 1},
    ]


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    'MissionState',
    'Mission',
    'MissionConfig',
    'sample_trajectory_csv',
    'hover_test_trajectory_csv',
    'swarm_leader_trajectory_csv',
    'mission_idle',
    'mission_takeoff',
    'mission_land',
    'mission_hold',
    'mission_rtl',
    'mission_drone_show',
    'mission_smart_swarm',
    'mission_swarm_trajectory',
    'mission_hover_test',
    'mission_emergency_kill',
    'mission_sequence_basic',
    'mission_sequence_show',
    'mission_sequence_swarm',
    'origin_zurich',
    'origin_sf',
    'origin_invalid',
    'swarm_config_single_leader',
    'swarm_config_multi_leader',
    'swarm_config_chain',
]
