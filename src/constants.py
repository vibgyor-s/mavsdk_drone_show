# src/constants.py
"""
Constants Module
================
Centralized constants for the MAVSDK Drone Show project.

This module provides named constants for magic numbers used throughout
the codebase, improving readability and maintainability.

Usage:
    from src.constants import PacketMarkers, TrajectoryState, NetworkDefaults
"""

from enum import IntEnum


# ============================================================================
# Telemetry Packet Protocol Constants
# ============================================================================

class PacketMarkers:
    """
    Markers used in the custom telemetry packet protocol.

    The telemetry protocol uses fixed byte markers to identify
    the start and end of valid packets.
    """
    HEADER = 77        # Start marker for telemetry packets
    TERMINATOR = 88    # End marker for telemetry packets


# ============================================================================
# Trajectory Execution States
# ============================================================================

class TrajectoryState(IntEnum):
    """
    State codes used during trajectory execution.

    These represent the phases a drone goes through when executing
    a trajectory mission.
    """
    INITIAL_CLIMB = 10          # Initial climbing state
    HOLDING_AFTER_CLIMB = 20    # Initial holding after climb
    MOVING_TO_START = 30        # Moving to start point
    HOLDING_AT_START = 40       # Holding at start point
    MOVING_TO_MANEUVER = 50     # Moving to maneuvering start point
    HOLDING_AT_MANEUVER = 60    # Holding at maneuver start point
    MANEUVERING = 70            # Maneuvering (trajectory execution)
    HOLDING_AT_END = 80         # Holding at the end of trajectory
    RETURNING_HOME = 90         # Returning to home coordinate
    LANDING = 100               # Landing

    @classmethod
    def get_description(cls, code: int) -> str:
        """Get human-readable description for a state code."""
        descriptions = {
            cls.INITIAL_CLIMB: "Initial climbing state",
            cls.HOLDING_AFTER_CLIMB: "Initial holding after climb",
            cls.MOVING_TO_START: "Moving to start point",
            cls.HOLDING_AT_START: "Holding at start point",
            cls.MOVING_TO_MANEUVER: "Moving to maneuvering start point",
            cls.HOLDING_AT_MANEUVER: "Holding at maneuver start point",
            cls.MANEUVERING: "Maneuvering (trajectory)",
            cls.HOLDING_AT_END: "Holding at end of trajectory",
            cls.RETURNING_HOME: "Returning to home coordinate",
            cls.LANDING: "Landing"
        }
        return descriptions.get(code, f"Unknown state: {code}")

    @classmethod
    def is_maneuvering(cls, code: int) -> bool:
        """Check if the state code indicates active maneuvering."""
        return code == cls.MANEUVERING


# ============================================================================
# Network Defaults
# ============================================================================

class NetworkDefaults:
    """
    Default network configuration values.

    These are fallback values used when configuration is not provided.
    Production values should be set in Params or environment variables.
    """
    MAVLINK_PORT = 14550          # Default MAVLink UDP port
    GRPC_BASE_PORT = 50040        # Base gRPC port (actual = base + hw_id)
    SOCKET_BUFFER_SIZE = 1024     # UDP socket receive buffer size
    THREAD_POOL_WORKERS = 10      # Default thread pool max workers


# ============================================================================
# Telemetry Data Indices
# ============================================================================

class TelemetryIndex:
    """
    Indices for accessing fields in the telemetry data tuple.

    The telemetry packet is parsed into a tuple, and these constants
    provide named access to each field.
    """
    HEADER = 0
    HW_ID = 1
    POS_ID = 2
    STATE = 3
    MISSION = 4
    LATITUDE = 5
    LONGITUDE = 6
    ALTITUDE = 7
    HEADING = 8
    VELOCITY_NORTH = 9
    VELOCITY_EAST = 10
    VELOCITY_DOWN = 11
    YAW = 12
    BATTERY_VOLTAGE = 13
    FOLLOW_MODE = 14
    UPDATE_TIME = 15
    TERMINATOR = 16


# ============================================================================
# Time Constants
# ============================================================================

class TimeConstants:
    """
    Common time-related constants.
    """
    MS_PER_SECOND = 1000
    SECONDS_PER_MINUTE = 60
    MINUTES_PER_HOUR = 60
