# gcs-server/schemas.py
"""
GCS Server Pydantic Schemas
===========================
Comprehensive request/response models for all GCS API endpoints.
Ensures type safety and automatic validation for FastAPI migration.

Author: MAVSDK Drone Show Team
Last Updated: 2025-11-22
"""

import os
import sys

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

# Import shared enums from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from enums import CommandStatus


# ============================================================================
# Enums for Type Safety
# ============================================================================

class DroneState(str, Enum):
    """Drone operational states"""
    IDLE = "idle"
    ARMED = "armed"
    TAKING_OFF = "taking_off"
    FLYING = "flying"
    LANDING = "landing"
    LANDED = "landed"
    ERROR = "error"
    UNKNOWN = "unknown"


class FlightMode(str, Enum):
    """MAVLink flight modes"""
    MANUAL = "MANUAL"
    STABILIZED = "STABILIZED"
    ACRO = "ACRO"
    ALTCTL = "ALTCTL"
    POSCTL = "POSCTL"
    OFFBOARD = "OFFBOARD"
    AUTO_MISSION = "AUTO.MISSION"
    AUTO_LOITER = "AUTO.LOITER"
    AUTO_RTL = "AUTO.RTL"
    AUTO_LAND = "AUTO.LAND"
    AUTO_TAKEOFF = "AUTO.TAKEOFF"


class GitStatus(str, Enum):
    """Git repository status"""
    SYNCED = "synced"
    AHEAD = "ahead"
    BEHIND = "behind"
    DIVERGED = "diverged"
    UNKNOWN = "unknown"


# ============================================================================
# Configuration Schemas
# ============================================================================

class DroneConfig(BaseModel):
    """Individual drone configuration matching 6-column config.csv format"""
    model_config = ConfigDict(extra='ignore')  # Ignore unknown fields for forward compatibility

    hw_id: int = Field(..., ge=1, description="Hardware ID (unique physical drone identifier)")
    pos_id: int = Field(..., ge=1, description="Position ID (1-based, maps to trajectory 'Drone {pos_id}.csv')")
    ip: str = Field(..., pattern=r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', description="IP address")
    mavlink_port: str = Field(..., description="MAVLink UDP port")
    serial_port: str = Field('', description="Serial port device path (empty for SITL)")
    baudrate: str = Field('', description="Serial baudrate (empty for SITL)")

    @validator('ip')
    def validate_ip(cls, v):
        """Validate IP address format"""
        octets = v.split('.')
        if len(octets) != 4:
            raise ValueError('Invalid IP address format')
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                raise ValueError('IP octets must be 0-255')
        return v


class ConfigListResponse(BaseModel):
    """Response for GET /config"""
    drones: List[DroneConfig] = Field(..., description="List of drone configurations")
    total_drones: int = Field(..., ge=0, description="Total number of drones")
    timestamp: int = Field(..., description="Unix timestamp (ms)")


class ConfigUpdateRequest(BaseModel):
    """Request for POST /config"""
    drones: List[DroneConfig] = Field(..., min_length=1, description="Updated drone configurations")


class ConfigUpdateResponse(BaseModel):
    """Response for POST /config"""
    success: bool = Field(..., description="Update success status")
    message: str = Field(..., description="Status message")
    updated_count: int = Field(..., ge=0, description="Number of drones updated")


# ============================================================================
# Telemetry Schemas
# ============================================================================

class PositionNED(BaseModel):
    """NED (North-East-Down) position"""
    north: float = Field(..., description="North position (m)")
    east: float = Field(..., description="East position (m)")
    down: float = Field(..., description="Down position (m)")


class PositionGPS(BaseModel):
    """GPS coordinates"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (degrees)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (degrees)")
    altitude: float = Field(..., description="Altitude above MSL (m)")


class VelocityNED(BaseModel):
    """NED velocity components"""
    vn: float = Field(..., description="North velocity (m/s)")
    ve: float = Field(..., description="East velocity (m/s)")
    vd: float = Field(..., description="Down velocity (m/s)")


class AttitudeEuler(BaseModel):
    """Euler angles for attitude"""
    roll: float = Field(..., description="Roll angle (degrees)")
    pitch: float = Field(..., description="Pitch angle (degrees)")
    yaw: float = Field(..., description="Yaw angle (degrees)")


class BatteryStatus(BaseModel):
    """Battery telemetry"""
    voltage: float = Field(..., ge=0, description="Battery voltage (V)")
    current: Optional[float] = Field(None, description="Battery current (A)")
    remaining: Optional[float] = Field(None, ge=0, le=100, description="Battery remaining (%)")


class DroneTelemetry(BaseModel):
    """Complete drone telemetry snapshot"""
    model_config = ConfigDict(extra='ignore')  # Ignore unknown fields for forward compatibility

    # Identity
    pos_id: int = Field(..., ge=0, description="Position ID")
    hw_id: str = Field(..., description="Hardware ID")

    # State
    state: DroneState = Field(..., description="Current drone state")
    flight_mode: FlightMode = Field(..., description="Current flight mode")
    armed: bool = Field(..., description="Armed status")
    in_air: bool = Field(..., description="In air status")

    # Position
    position_gps: Optional[PositionGPS] = Field(None, description="GPS position")
    position_ned: Optional[PositionNED] = Field(None, description="NED position")

    # Velocity & Attitude
    velocity_ned: Optional[VelocityNED] = Field(None, description="NED velocity")
    attitude: Optional[AttitudeEuler] = Field(None, description="Attitude (Euler angles)")

    # Battery
    battery: Optional[BatteryStatus] = Field(None, description="Battery status")

    # Health
    health_ok: bool = Field(..., description="Overall health status")
    gps_fix: Optional[int] = Field(None, ge=0, le=6, description="GPS fix type (0-6)")
    num_satellites: Optional[int] = Field(None, ge=0, description="Number of satellites")

    # Timestamps
    timestamp: int = Field(..., description="Telemetry timestamp (Unix ms)")
    last_heartbeat: Optional[int] = Field(None, description="Last heartbeat timestamp (Unix ms)")


class TelemetryResponse(BaseModel):
    """Response for GET /telemetry"""
    telemetry: Dict[str, DroneTelemetry] = Field(..., description="Telemetry by pos_id")
    total_drones: int = Field(..., ge=0, description="Total drones")
    online_drones: int = Field(..., ge=0, description="Online drones")
    timestamp: int = Field(..., description="Server timestamp (Unix ms)")


# ============================================================================
# Heartbeat Schemas
# ============================================================================

class HeartbeatData(BaseModel):
    """Individual drone heartbeat data"""
    pos_id: int = Field(..., ge=0, description="Position ID")
    hw_id: str = Field(..., description="Hardware ID")
    ip: str = Field(..., description="Drone IP address")
    last_heartbeat: Optional[int] = Field(None, description="Last heartbeat timestamp (Unix ms)")
    online: bool = Field(..., description="Online status")
    latency_ms: Optional[float] = Field(None, ge=0, description="Network latency (ms)")


class HeartbeatResponse(BaseModel):
    """Response for GET /get-heartbeats"""
    heartbeats: List[HeartbeatData] = Field(..., description="Heartbeat data for all drones")
    total_drones: int = Field(..., ge=0, description="Total drones")
    online_count: int = Field(..., ge=0, description="Online drones")
    timestamp: int = Field(..., description="Server timestamp (Unix ms)")


class HeartbeatRequest(BaseModel):
    """Request for POST /heartbeat"""
    pos_id: int = Field(..., ge=0, description="Position ID")
    hw_id: str = Field(..., description="Hardware ID")
    timestamp: Optional[int] = Field(None, description="Client timestamp (Unix ms)")


class HeartbeatPostResponse(BaseModel):
    """Response for POST /heartbeat"""
    success: bool = Field(..., description="Heartbeat received status")
    message: str = Field(..., description="Status message")
    server_time: int = Field(..., description="Server timestamp (Unix ms)")


# ============================================================================
# Git Status Schemas
# ============================================================================

class DroneGitStatus(BaseModel):
    """Git status for individual drone"""
    pos_id: int = Field(..., ge=1, description="Position ID")
    hw_id: str = Field(..., description="Hardware ID")
    ip: str = Field(..., description="Drone IP")

    # Git information
    current_branch: str = Field(..., description="Current git branch")
    latest_commit: str = Field(..., description="Latest commit hash (short)")
    commit_message: Optional[str] = Field(None, description="Latest commit message")
    status: GitStatus = Field(..., description="Git sync status")

    # Synchronization
    commits_ahead: int = Field(..., ge=0, description="Commits ahead of origin")
    commits_behind: int = Field(..., ge=0, description="Commits behind origin")
    has_uncommitted: bool = Field(..., description="Has uncommitted changes")

    # Timestamps
    last_check: int = Field(..., description="Last status check timestamp (Unix ms)")
    last_sync: Optional[int] = Field(None, description="Last successful sync timestamp (Unix ms)")


class GitStatusResponse(BaseModel):
    """Response for GET /git-status"""
    git_status: Dict[str, DroneGitStatus] = Field(..., description="Git status by pos_id")
    total_drones: int = Field(..., ge=0, description="Total drones")
    synced_count: int = Field(..., ge=0, description="Drones fully synced")
    needs_sync_count: int = Field(..., ge=0, description="Drones needing sync")
    timestamp: int = Field(..., description="Server timestamp (Unix ms)")


class SyncReposRequest(BaseModel):
    """Request for POST /sync-repos"""
    pos_ids: Optional[List[int]] = Field(None, description="Specific drone IDs to sync (all if empty)")
    force_pull: bool = Field(False, description="Force pull from origin")


class SyncReposResponse(BaseModel):
    """Response for POST /sync-repos"""
    success: bool = Field(..., description="Sync operation status")
    message: str = Field(..., description="Status message")
    synced_drones: List[int] = Field(..., description="Successfully synced drone IDs")
    failed_drones: List[int] = Field(..., description="Failed drone IDs")
    total_attempted: int = Field(..., ge=0, description="Total sync attempts")


# ============================================================================
# Swarm Trajectory Schemas
# ============================================================================

class TrajectoryPoint(BaseModel):
    """Single trajectory waypoint"""
    t: float = Field(..., ge=0, description="Time (seconds)")
    x: float = Field(..., description="X coordinate (meters)")
    y: float = Field(..., description="Y coordinate (meters)")
    z: float = Field(..., ge=0, description="Z coordinate (meters)")
    yaw: Optional[float] = Field(0.0, description="Yaw angle (degrees)")


class DroneTrajectory(BaseModel):
    """Complete trajectory for one drone"""
    pos_id: int = Field(..., ge=1, description="Position ID")
    hw_id: Optional[str] = Field(None, description="Hardware ID")
    waypoints: List[TrajectoryPoint] = Field(..., min_length=1, description="Trajectory waypoints")
    total_duration: float = Field(..., ge=0, description="Total trajectory duration (s)")


class SwarmTrajectory(BaseModel):
    """Complete swarm trajectory"""
    show_name: str = Field(..., min_length=1, description="Show/trajectory name")
    drones: List[DroneTrajectory] = Field(..., min_length=1, description="Trajectories for all drones")
    total_drones: int = Field(..., ge=1, description="Total number of drones")
    max_duration: float = Field(..., ge=0, description="Maximum trajectory duration (s)")
    created_at: Optional[int] = Field(None, description="Creation timestamp (Unix ms)")


class TrajectoryListItem(BaseModel):
    """Trajectory summary for list view"""
    name: str = Field(..., description="Trajectory name")
    drone_count: int = Field(..., ge=0, description="Number of drones")
    duration: float = Field(..., ge=0, description="Duration (seconds)")
    file_size: int = Field(..., ge=0, description="File size (bytes)")
    created: Optional[str] = Field(None, description="Creation date (ISO format)")
    has_preview: bool = Field(..., description="Has plot preview available")


class TrajectoryListResponse(BaseModel):
    """Response for GET /api/swarm/trajectories"""
    trajectories: List[TrajectoryListItem] = Field(..., description="Available trajectories")
    total_count: int = Field(..., ge=0, description="Total trajectory count")
    current_trajectory: Optional[str] = Field(None, description="Currently active trajectory")


class TrajectoryUploadResponse(BaseModel):
    """Response for POST /api/swarm/trajectory/upload"""
    success: bool = Field(..., description="Upload success status")
    message: str = Field(..., description="Status message")
    trajectory_name: str = Field(..., description="Uploaded trajectory name")
    drone_count: int = Field(..., ge=0, description="Number of drones in trajectory")
    duration: float = Field(..., ge=0, description="Trajectory duration (s)")
    preview_url: Optional[str] = Field(None, description="Preview plot URL")


class SetActiveTrajectoryRequest(BaseModel):
    """Request for POST /api/swarm/trajectory/set-active"""
    trajectory_name: str = Field(..., min_length=1, description="Trajectory name to activate")


class SetActiveTrajectoryResponse(BaseModel):
    """Response for POST /api/swarm/trajectory/set-active"""
    success: bool = Field(..., description="Activation success status")
    message: str = Field(..., description="Status message")
    active_trajectory: str = Field(..., description="Now active trajectory")


class TrajectoryDeleteRequest(BaseModel):
    """Request for DELETE /api/swarm/trajectory/{name}"""
    confirm: bool = Field(False, description="Confirm deletion")


class TrajectoryDeleteResponse(BaseModel):
    """Response for DELETE /api/swarm/trajectory/{name}"""
    success: bool = Field(..., description="Deletion success status")
    message: str = Field(..., description="Status message")
    deleted_files: List[str] = Field(..., description="Deleted file paths")


# ============================================================================
# Show Control Schemas
# ============================================================================

class ShowImportRequest(BaseModel):
    """Request metadata for POST /import-show"""
    show_name: str = Field(..., min_length=1, description="Show name")
    overwrite: bool = Field(False, description="Overwrite existing show")


class ShowImportResponse(BaseModel):
    """Response for POST /import-show"""
    success: bool = Field(..., description="Import success status")
    message: str = Field(..., description="Status message")
    show_name: str = Field(..., description="Imported show name")
    files_processed: int = Field(..., ge=0, description="Number of files processed")
    drones_configured: int = Field(..., ge=0, description="Number of drones configured")


class CommandRequest(BaseModel):
    """Request schema for commands (used internally, not directly exposed)"""
    command: str = Field(..., min_length=1, description="Command to send")
    drone_ids: Optional[List[int]] = Field(None, description="Target drone IDs (all if empty)")
    params: Optional[Dict[str, Any]] = Field(None, description="Command parameters")


class CommandResponse(BaseModel):
    """Response for POST /submit_command (GCS endpoint for command submission)"""
    success: bool = Field(..., description="Command sent status")
    message: str = Field(..., description="Status message")
    command: str = Field(..., description="Command that was sent")
    target_drones: List[int] = Field(..., description="Targeted drone IDs")
    sent_count: int = Field(..., ge=0, description="Successfully sent count")


# ============================================================================
# Origin & GPS Schemas
# ============================================================================

class OriginRequest(BaseModel):
    """Request for POST /set-origin - Flask-compatible format"""
    lat: float = Field(..., ge=-90, le=90, description="Origin latitude")
    lon: float = Field(..., ge=-180, le=180, description="Origin longitude")
    alt: float = Field(..., description="Origin altitude (m MSL)")
    alt_source: Optional[str] = Field('manual', description="Altitude source (manual/drone)")


class OriginResponse(BaseModel):
    """Response for GET/POST origin endpoints - Flask-compatible format"""
    lat: float = Field(..., description="Origin latitude")
    lon: float = Field(..., description="Origin longitude")
    alt: float = Field(..., description="Origin altitude (m MSL)")
    timestamp: Optional[int] = Field(None, description="Last update timestamp (Unix ms)")


class GPSGlobalOriginResponse(BaseModel):
    """Response for GET /get-gps-global-origin"""
    latitude: float = Field(..., description="GPS global origin latitude")
    longitude: float = Field(..., description="GPS global origin longitude")
    altitude: float = Field(..., description="GPS global origin altitude (m MSL)")
    has_origin: bool = Field(..., description="Origin has been set")


# ============================================================================
# Network & System Schemas
# ============================================================================

class NetworkStatus(BaseModel):
    """Network connectivity status"""
    pos_id: int = Field(..., ge=1, description="Position ID")
    ip: str = Field(..., description="IP address")
    reachable: bool = Field(..., description="Network reachable")
    latency_ms: Optional[float] = Field(None, ge=0, description="Ping latency (ms)")
    packet_loss: Optional[float] = Field(None, ge=0, le=100, description="Packet loss (%)")
    last_check: int = Field(..., description="Last check timestamp (Unix ms)")


class NetworkStatusResponse(BaseModel):
    """Response for GET /get-network-status"""
    network_status: Dict[str, NetworkStatus] = Field(..., description="Network status by pos_id")
    total_drones: int = Field(..., ge=0, description="Total drones")
    reachable_count: int = Field(..., ge=0, description="Reachable drones")
    timestamp: int = Field(..., description="Server timestamp (Unix ms)")


class HealthCheckResponse(BaseModel):
    """Response for GET /ping or /health"""
    status: str = Field(..., description="Health status")
    timestamp: int = Field(..., description="Server timestamp (Unix ms)")
    uptime_seconds: Optional[float] = Field(None, ge=0, description="Server uptime")
    version: Optional[str] = Field(None, description="Server version")


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorDetail(BaseModel):
    """Detailed error information"""
    loc: Optional[List[str]] = Field(None, description="Error location path")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[Union[str, List[ErrorDetail]]] = Field(None, description="Detailed error info")
    timestamp: int = Field(..., description="Error timestamp (Unix ms)")
    path: Optional[str] = Field(None, description="Request path that caused error")


# ============================================================================
# WebSocket Message Schemas
# ============================================================================

class WebSocketMessage(BaseModel):
    """Base WebSocket message structure"""
    type: str = Field(..., description="Message type")
    timestamp: int = Field(..., description="Message timestamp (Unix ms)")
    data: Dict[str, Any] = Field(..., description="Message payload")


class TelemetryStreamMessage(WebSocketMessage):
    """WebSocket telemetry stream message"""
    type: str = Field(default="telemetry", description="Message type")
    data: Dict[str, DroneTelemetry] = Field(..., description="Telemetry data by pos_id")


class GitStatusStreamMessage(WebSocketMessage):
    """WebSocket git status stream message"""
    type: str = Field(default="git_status", description="Message type")
    data: Dict[str, DroneGitStatus] = Field(..., description="Git status by pos_id")


class HeartbeatStreamMessage(WebSocketMessage):
    """WebSocket heartbeat stream message"""
    type: str = Field(default="heartbeat", description="Message type")
    data: List[HeartbeatData] = Field(..., description="Heartbeat data for all drones")


# ============================================================================
# Command Tracking Schemas
# ============================================================================
# Note: CommandStatus enum is imported from src/enums.py to avoid duplication

class DroneAckDetail(BaseModel):
    """Acknowledgment detail from a single drone"""
    status: str = Field(
        ...,
        pattern="^(accepted|offline|rejected|error)$",
        description="'accepted', 'offline', 'rejected', or 'error'"
    )
    category: str = Field(
        "accepted",
        pattern="^(accepted|offline|rejected|error)$",
        description="Result category: 'accepted' (success), 'offline' (unreachable - neutral), 'rejected' (drone refused), 'error' (unexpected)"
    )
    message: Optional[str] = Field(None, max_length=500, description="Status message")
    error_code: Optional[str] = Field(None, pattern="^E[0-9]{3}$", description="Error code if rejected/error (e.g., E202)")
    error_detail: Optional[str] = Field(None, max_length=500, description="Detailed error information")
    timestamp: int = Field(..., ge=0, description="ACK timestamp (Unix ms)")


class DroneExecutionDetail(BaseModel):
    """Execution detail from a single drone"""
    success: bool = Field(..., description="Whether execution succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")
    exit_code: Optional[int] = Field(None, description="Script exit code")
    duration_ms: Optional[int] = Field(None, description="Execution duration (ms)")
    timestamp: int = Field(..., description="Execution timestamp (Unix ms)")


class AckSummary(BaseModel):
    """Summary of acknowledgments for a command"""
    expected: int = Field(..., ge=0, description="Number of ACKs expected")
    received: int = Field(..., ge=0, description="Number of ACKs received")
    accepted: int = Field(..., ge=0, description="Number accepted")
    offline: int = Field(0, ge=0, description="Number offline (unreachable - neutral, not an error)")
    rejected: int = Field(0, ge=0, description="Number rejected (drone refused command)")
    errors: int = Field(0, ge=0, description="Number with unexpected errors")
    result_summary: Optional[str] = Field(None, description="Human-readable result summary (e.g., '1 accepted, 4 offline')")
    details: Dict[str, DroneAckDetail] = Field(default_factory=dict, description="Per-drone ACK details")


class ExecutionSummary(BaseModel):
    """Summary of executions for a command"""
    expected: int = Field(..., ge=0, description="Number of executions expected")
    received: int = Field(..., ge=0, description="Number of executions received")
    succeeded: int = Field(..., ge=0, description="Number succeeded")
    failed: int = Field(..., ge=0, description="Number failed")
    details: Dict[str, DroneExecutionDetail] = Field(default_factory=dict, description="Per-drone execution details")


class CommandStatusResponse(BaseModel):
    """Detailed command status response"""
    command_id: str = Field(..., description="Command UUID")
    mission_type: int = Field(..., description="Mission type code")
    mission_name: str = Field(..., description="Human-readable mission name")
    target_drones: List[str] = Field(..., description="Target drone hardware IDs")
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    status: CommandStatus = Field(..., description="Current command status")

    # Timing
    created_at: int = Field(..., description="Creation timestamp (Unix ms)")
    submitted_at: Optional[int] = Field(None, description="Submission timestamp (Unix ms)")
    completed_at: Optional[int] = Field(None, description="Completion timestamp (Unix ms)")
    updated_at: int = Field(..., description="Last update timestamp (Unix ms)")

    # Summaries
    acks: AckSummary = Field(..., description="Acknowledgment summary")
    executions: ExecutionSummary = Field(..., description="Execution summary")

    error_summary: Optional[str] = Field(None, description="Error summary if failed/partial")


class CommandListResponse(BaseModel):
    """Response for command list endpoint"""
    commands: List[CommandStatusResponse] = Field(..., description="List of commands")
    total: int = Field(..., ge=0, description="Total commands returned")
    timestamp: int = Field(..., description="Response timestamp (Unix ms)")


class CommandStatisticsResponse(BaseModel):
    """Response for command statistics endpoint"""
    total_commands: int = Field(..., ge=0, description="Total commands ever tracked")
    successful_commands: int = Field(..., ge=0, description="Number of successful commands")
    failed_commands: int = Field(..., ge=0, description="Number of failed commands")
    partial_commands: int = Field(..., ge=0, description="Number of partial success commands")
    timeout_commands: int = Field(..., ge=0, description="Number of timed out commands")
    cancelled_commands: int = Field(..., ge=0, description="Number of cancelled commands")
    active_commands: int = Field(..., ge=0, description="Currently active commands")
    tracked_commands: int = Field(..., ge=0, description="Commands in tracking history")
    success_rate: float = Field(..., ge=0, le=100, description="Success rate percentage")
    timestamp: int = Field(..., description="Response timestamp (Unix ms)")


class SubmitCommandRequest(BaseModel):
    """Request to submit a command to drones"""
    model_config = ConfigDict(extra='allow')  # Allow additional fields

    missionType: int = Field(..., description="Mission type code")
    triggerTime: Optional[int] = Field(0, ge=0, description="Trigger time (Unix epoch seconds)")
    pos_ids: Optional[List[int]] = Field(None, description="Target position IDs (None = all drones)")

    # Optional fields depending on mission type
    takeoff_altitude: Optional[float] = Field(None, gt=0, description="Takeoff altitude (m)")
    origin_lat: Optional[float] = Field(None, ge=-90, le=90, description="Origin latitude")
    origin_lon: Optional[float] = Field(None, ge=-180, le=180, description="Origin longitude")
    trajectory_id: Optional[str] = Field(None, description="Trajectory file identifier")

    # Control options
    wait_for_ack: bool = Field(False, description="Wait for all drone ACKs before returning")
    ack_timeout_ms: int = Field(5000, gt=0, description="ACK wait timeout (ms)")


class SubmitCommandResponse(BaseModel):
    """Response for command submission"""
    success: bool = Field(..., description="Whether command was successfully sent to at least one drone")
    command_id: str = Field(..., description="Command tracking UUID")
    status: str = Field(..., description="Submission status ('submitted', 'partial', 'offline', or 'failed')")
    mission_type: int = Field(..., description="Mission type code")
    mission_name: str = Field(..., description="Human-readable mission name")
    target_drones: List[str] = Field(..., description="Target drone hardware IDs")
    submitted_count: int = Field(..., ge=0, description="Number of drones command was sent to")

    # Immediate categorized results (always populated)
    results_summary: Optional[Dict[str, int]] = Field(
        None,
        description="Categorized results: {'accepted': N, 'offline': N, 'rejected': N, 'errors': N}"
    )

    # If wait_for_ack=true, these will be populated
    ack_summary: Optional[AckSummary] = Field(None, description="ACK summary if wait_for_ack=true")

    message: str = Field(..., description="Human-readable status message")
    timestamp: int = Field(..., description="Response timestamp (Unix ms)")


class ExecutionReportRequest(BaseModel):
    """Request from drone reporting execution result"""
    command_id: str = Field(..., description="Command UUID from GCS")
    hw_id: str = Field(..., description="Reporting drone's hardware ID")
    success: bool = Field(..., description="Whether execution succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    exit_code: Optional[int] = Field(None, description="Script exit code")
    script_output: Optional[str] = Field(None, description="Script output/logs (truncated)")
    duration_ms: Optional[int] = Field(None, ge=0, description="Execution duration (ms)")


class ExecutionReportResponse(BaseModel):
    """Response for execution report"""
    received: bool = Field(..., description="Whether report was recorded")
    command_id: str = Field(..., description="Command UUID")
    command_status: CommandStatus = Field(..., description="Updated command status")
    message: str = Field(..., description="Status message")
    timestamp: int = Field(..., description="Response timestamp (Unix ms)")
