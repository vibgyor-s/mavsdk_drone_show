#!/bin/bash

# =============================================================================
# Script Name: startup_sitl.sh
# Description: Initializes and manages the SITL simulation for MAVSDK_Drone_Show.
#              Configures environment, updates repository, sets system IDs, synchronizes
#              system time with NTP using an external script, and starts the SITL simulation
#              along with coordinator.py and mavlink2rest.
# Author: Alireza Ghaderi
# Date: September 2024
# =============================================================================

# Exit immediately if a command exits with a non-zero status,
# if an undefined variable is used, or if any command in a pipeline fails
set -euo pipefail

# Enable debug mode if needed (uncomment the following line for debugging)
# set -x

# =============================================================================
# Configuration Variables
# =============================================================================

# =============================================================================
# REPOSITORY CONFIGURATION: Environment Variable Support (MDS v3.1+)
# =============================================================================
# This script now supports environment variable override for advanced deployments
# while maintaining 100% backward compatibility for normal users.
#
# FOR NORMAL USERS (99%):
#   - No action required - defaults work identically to previous versions
#   - Uses: https://github.com/alireza787b/mavsdk_drone_show.git@main-candidate
#   - Simply run: bash create_dockers.sh <number_of_drones>
#
# FOR ADVANCED USERS (Custom Forks):
#   - Set environment variables on HOST before running create_dockers.sh:
#     export MDS_REPO_URL="git@github.com:yourcompany/your-fork.git"
#     export MDS_BRANCH="your-production-branch"
#   - Environment variables are automatically passed to containers
#   - All containers will use your custom repository configuration
#
# EXAMPLES:
#   # Use HTTPS URL (no SSH keys needed):
#   export MDS_REPO_URL="https://github.com/company/fork.git"
#   export MDS_BRANCH="production"
#   bash create_dockers.sh 5
#
#   # Use SSH URL (requires SSH keys in Docker image):
#   export MDS_REPO_URL="git@github.com:company/fork.git"
#   export MDS_BRANCH="main"
#   bash create_dockers.sh 10
#
# ENVIRONMENT VARIABLES SUPPORTED:
#   MDS_REPO_URL  - Git repository URL (SSH or HTTPS format)
#   MDS_BRANCH    - Git branch name to checkout and use
#
# NOTE: These variables are checked at container startup time
# =============================================================================

# GitHub Repository Details (with environment variable override support)
DEFAULT_GIT_REMOTE="origin"
DEFAULT_GIT_BRANCH="${MDS_BRANCH:-main-candidate}"
GITHUB_REPO_URL="${MDS_REPO_URL:-https://github.com/alireza787b/mavsdk_drone_show.git}"

# Option to use global Python
USE_GLOBAL_PYTHON=false  # Set to true to use global Python instead of venv

# Default geographic position: Azadi Stadium
DEFAULT_LAT=35.724435686078365
DEFAULT_LON=51.275581311948706
DEFAULT_ALT=1278

# Directory Paths
BASE_DIR="$HOME/mavsdk_drone_show"
VENV_DIR="$BASE_DIR/venv"
CONFIG_FILE="$BASE_DIR/config_sitl.json"
PX4_DIR="$HOME/PX4-Autopilot"
mavlink2rest_CMD="mavlink2rest -c udpin:127.0.0.1:14569 -s 0.0.0.0:8088"
MAVLINK2REST_LOG="$BASE_DIR/logs/mavlink2rest.log"

# MAVLink Router for SITL (external routing - replaces internal MavlinkManager)
MAVLINK_ROUTER_SCRIPT="$BASE_DIR/tools/run_mavlink_router.sh"
MAVLINK_ROUTER_LOG="$BASE_DIR/logs/mavlink_router.log"
PX4_MAVLINK_PORT_DETECTOR="$BASE_DIR/multiple_sitl/detect_px4_mavlink_port.py"

# Path to the external time synchronization script
# SYNC_SCRIPT="$BASE_DIR/tools/sync_time_linux.sh"

# Script Metadata
SCRIPT_NAME=$(basename "$0")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default Simulation Mode (h: headless, g: graphical, j: jmavsim)
SIMULATION_MODE="h"

# Initialize Git variables
GIT_REMOTE="$DEFAULT_GIT_REMOTE"
GIT_BRANCH="$DEFAULT_GIT_BRANCH"

# Verbose Mode Flag
VERBOSE_MODE=false

# =============================================================================
# Function Definitions
# =============================================================================

# Function to display usage information
usage() {
    cat << EOF
Usage: $SCRIPT_NAME [options]

Options:
  -r <git_remote>       Specify the GitHub repository remote name (default: $DEFAULT_GIT_REMOTE)
  -b <git_branch>       Specify the GitHub repository branch name (default: $DEFAULT_GIT_BRANCH)
  -s <simulation_mode>  Specify simulation mode: 'g' for graphical, 'h' for headless, 'j' for jmavsim (default: $SIMULATION_MODE)
  -v, --verbose         Run coordinator.py in verbose mode (foreground with output to screen)
  -h, --help            Display this help message

Examples:
  $SCRIPT_NAME
  $SCRIPT_NAME -r upstream -b develop
  $SCRIPT_NAME -s g
  $SCRIPT_NAME --verbose
EOF
    exit 1
}

# Function to log messages to the terminal with timestamps
log_message() {
    local message="$1"
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $message"
}

# Function to handle script termination and cleanup
cleanup() {
    echo ""
    log_message "Received interrupt signal. Terminating background processes..."

    if [[ -n "${simulation_pid:-}" ]]; then
        kill "$simulation_pid" 2>/dev/null || true
        log_message "Terminated SITL simulation with PID: $simulation_pid"
    fi

    if [ "$VERBOSE_MODE" = false ]; then
        if [[ -n "${coordinator_pid:-}" ]]; then
            kill "$coordinator_pid" 2>/dev/null || true
            log_message "Terminated coordinator.py with PID: $coordinator_pid"
        fi
    else
        log_message "Coordinator.py running in foreground, should receive SIGINT."
    fi

    if [[ -n "${mavlink2rest_pid:-}" ]]; then
        kill "$mavlink2rest_pid" 2>/dev/null || true
        log_message "Terminated mavlink2rest with PID: $mavlink2rest_pid"
    fi

    if [[ -n "${mavlink_router_pid:-}" ]]; then
        kill "$mavlink_router_pid" 2>/dev/null || true
        log_message "Terminated MAVLink router with PID: $mavlink_router_pid"
    fi

    if [ "${USE_GLOBAL_PYTHON:-false}" = false ]; then
        deactivate 2>/dev/null || true
        log_message "Deactivated Python virtual environment."
    fi

    exit 0
}

# Function to install 'bc' if not present
install_bc() {
    log_message "'bc' is not installed. Installing 'bc'..."
    if ! sudo apt-get update && sudo apt-get install -y bc; then
        log_message "ERROR: Failed to install 'bc'. Please install it manually."
        exit 1
    fi
    log_message "'bc' installed successfully."
}

# Function to parse script arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r)
                if [[ -n "${2:-}" && ! $2 =~ ^- ]]; then
                    GIT_REMOTE="$2"
                    shift 2
                else
                    log_message "ERROR: -r requires a non-empty option argument."
                    usage
                fi
                ;;
            -b)
                if [[ -n "${2:-}" && ! $2 =~ ^- ]]; then
                    GIT_BRANCH="$2"
                    shift 2
                else
                    log_message "ERROR: -b requires a non-empty option argument."
                    usage
                fi
                ;;
            -s)
                if [[ -n "${2:-}" && ! $2 =~ ^- ]]; then
                    SIMULATION_MODE="$2"
                    shift 2
                else
                    log_message "ERROR: -s requires a non-empty option argument."
                    usage
                fi
                ;;
            -v|--verbose)
                VERBOSE_MODE=true
                shift
                ;;
            -h|--help)
                usage
                ;;
            *)
                log_message "ERROR: Unknown option: $1"
                usage
                ;;
        esac
    done
}

# Function to check and install dependencies
check_dependencies() {
    if ! command -v bc &> /dev/null; then
        install_bc
    else
        log_message "'bc' is already installed."
    fi
    if ! command -v git &> /dev/null; then
        log_message "'git' is not installed. Installing 'git'..."
        if ! sudo apt-get update && sudo apt-get install -y git; then
            log_message "ERROR: Failed to install 'git'. Please install it manually."
            exit 1
        fi
        log_message "'git' installed successfully."
    else
        log_message "'git' is already installed."
    fi
}

# Function to wait for the .hwID file
wait_for_hwid() {
    log_message "Waiting for .hwID file in $BASE_DIR..."
    while true; do
        HWID_FILE=$(ls "$BASE_DIR"/*.hwID 2>/dev/null | head -n 1 || true)
        if [[ -n "$HWID_FILE" ]]; then
            HWID=$(basename "$HWID_FILE" .hwID)
            log_message "Found .hwID file: $HWID.hwID"
            break
        else
            log_message "  - .hwID file not found. Retrying in 1 second..."
            sleep 1
        fi
    done

    # Validate that HWID is a positive integer
    if ! [[ "$HWID" =~ ^[1-9][0-9]*$ ]]; then
        log_message "ERROR: Extracted HWID '$HWID' is not a positive integer."
        exit 1
    fi
}

# Retry helper for SITL git operations (matches update_repo_ssh.sh pattern)
sitl_retry() {
    local max_retries="${1:-3}"
    local label="$2"
    shift 2
    local attempt=0
    local delay=2
    while [ $attempt -lt "$max_retries" ]; do
        if "$@"; then
            return 0
        fi
        attempt=$((attempt + 1))
        if [ $attempt -lt "$max_retries" ]; then
            # Add jitter (0-2s) to avoid thundering herd with multiple SITL containers
            local jitter=$((RANDOM % 3))
            local wait=$((delay + jitter))
            log_message "[$label] Attempt $attempt/$max_retries failed. Retrying in ${wait}s..."
            sleep "$wait"
            delay=$((delay * 2))
        fi
    done
    log_message "ERROR: [$label] Failed after $max_retries attempts."
    return 1
}

# Function to update the repository
update_repository() {
    local start_time
    start_time=$(date +%s)

    log_message "Navigating to $BASE_DIR..."
    cd "$BASE_DIR"

    if git status --porcelain | grep -q .; then
        log_message "Stashing local changes..."
        git stash push --include-untracked || log_message "WARNING: stash failed, continuing"
    fi

    log_message "Setting Git remote to $GIT_REMOTE..."
    git remote set-url "$GIT_REMOTE" "$GITHUB_REPO_URL" || true

    log_message "Fetching latest changes from $GIT_REMOTE/$GIT_BRANCH..."
    if ! sitl_retry 3 "GIT-FETCH" git fetch "$GIT_REMOTE" "$GIT_BRANCH"; then
        log_message "ERROR: Failed to fetch from $GIT_REMOTE/$GIT_BRANCH."
        echo "GIT_SYNC_RESULT={\"success\":false,\"branch\":\"$GIT_BRANCH\",\"error\":\"fetch_failed\"}"
        exit 1
    fi

    log_message "Checking out branch $GIT_BRANCH..."
    if ! git checkout "$GIT_BRANCH"; then
        log_message "ERROR: Failed to checkout branch $GIT_BRANCH."
        echo "GIT_SYNC_RESULT={\"success\":false,\"branch\":\"$GIT_BRANCH\",\"error\":\"checkout_failed\"}"
        exit 1
    fi

    log_message "Pulling latest changes from $GIT_REMOTE/$GIT_BRANCH..."
    if ! sitl_retry 3 "GIT-PULL" git pull "$GIT_REMOTE" "$GIT_BRANCH"; then
        log_message "ERROR: Failed to pull latest changes from $GIT_REMOTE/$GIT_BRANCH."
        echo "GIT_SYNC_RESULT={\"success\":false,\"branch\":\"$GIT_BRANCH\",\"error\":\"pull_failed\"}"
        exit 1
    fi

    local commit_hash
    commit_hash=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    local commit_message
    commit_message=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown")
    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_message "Repository updated successfully."
    # Escape quotes/backslashes in commit message for valid JSON
    local commit_message_json
    commit_message_json=$(echo "$commit_message" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\n\r')
    echo "GIT_SYNC_RESULT={\"success\":true,\"branch\":\"$GIT_BRANCH\",\"commit\":\"$commit_hash\",\"message\":\"$commit_message_json\",\"duration\":$duration}"
}

# Function to run MAVLink router for SITL (external routing)
# This replaces the internal MavlinkManager and provides MAVLink routing
# from PX4's detected GCS UDP port to mavlink2rest (14569),
# LocalMavlinkController (12550), and remote GCS (24550)
run_mavlink_router() {
    log_message "Starting MAVLink router for SITL..."

    # Ensure the logs directory exists
    mkdir -p "$(dirname "$MAVLINK_ROUTER_LOG")"

    # Export GCS_IP for mavlink router (reads from params via Python)
    # Falls back to Docker gateway if params not available
    cd "$BASE_DIR"
    export GCS_IP=$(python3 -c "from src.params import Params; print(Params.GCS_IP)" 2>/dev/null || echo "172.18.0.1")
    log_message "GCS IP for MAVLink routing: $GCS_IP"

    # Check if mavlink-routerd is installed
    if ! command -v mavlink-routerd &> /dev/null; then
        log_message "WARNING: mavlink-routerd not installed. MAVLink routing cannot start."
        log_message "To install: git clone https://github.com/alireza787b/mavlink-anywhere && cd mavlink-anywhere && sudo ./install_mavlink_router.sh"
        return 1
    fi

    # Run mavlink router in the background
    if [ -x "$MAVLINK_ROUTER_SCRIPT" ]; then
        local router_input_port="${PX4_GCS_MAVLINK_PORT:-14550}"
        log_message "MAVLink router input port: $router_input_port"
        $MAVLINK_ROUTER_SCRIPT "$router_input_port" &> "$MAVLINK_ROUTER_LOG" &
        mavlink_router_pid=$!
        log_message "MAVLink router started with PID: $mavlink_router_pid. Logs: $MAVLINK_ROUTER_LOG"
        sleep 2  # Wait for router to initialize before starting other services
        if ! kill -0 "$mavlink_router_pid" 2>/dev/null; then
            log_message "ERROR: MAVLink router exited during startup. Recent log lines:"
            if [ -f "$MAVLINK_ROUTER_LOG" ]; then
                while IFS= read -r line; do
                    log_message "  $line"
                done < <(tail -n 20 "$MAVLINK_ROUTER_LOG")
            fi
            return 1
        fi
    else
        log_message "WARNING: MAVLink router script not found or not executable: $MAVLINK_ROUTER_SCRIPT"
        return 1
    fi
}

# Detect PX4's live MAVLink GCS output port so the router matches the image's
# actual runtime behavior instead of relying on a single hardcoded assumption.
detect_px4_mavlink_port() {
    local default_port="${MDS_PX4_GCS_PORT:-14550}"
    local detection_log="$BASE_DIR/logs/mavlink_port_detection.log"

    if [ -n "${MDS_PX4_GCS_PORT:-}" ]; then
        PX4_GCS_MAVLINK_PORT="$MDS_PX4_GCS_PORT"
        log_message "Using PX4 MAVLink port override from MDS_PX4_GCS_PORT: $PX4_GCS_MAVLINK_PORT"
        return 0
    fi

    if [ ! -f "$PX4_MAVLINK_PORT_DETECTOR" ]; then
        PX4_GCS_MAVLINK_PORT="$default_port"
        log_message "WARNING: MAVLink port detector not found. Falling back to port $PX4_GCS_MAVLINK_PORT"
        return 0
    fi

    mkdir -p "$(dirname "$detection_log")"
    PX4_GCS_MAVLINK_PORT=$(python3 "$PX4_MAVLINK_PORT_DETECTOR" \
        --default-port "$default_port" \
        --timeout 12 \
        --poll-interval 0.5 \
        --sitl-log "$BASE_DIR/logs/sitl_simulation.log" \
        --exclude-port 12550 \
        --exclude-port 14540 \
        --exclude-port 14569 \
        --exclude-port 24550 \
        2>>"$detection_log")

    if [[ ! "$PX4_GCS_MAVLINK_PORT" =~ ^[0-9]+$ ]]; then
        PX4_GCS_MAVLINK_PORT="$default_port"
        log_message "WARNING: Invalid detected PX4 MAVLink port. Falling back to $PX4_GCS_MAVLINK_PORT"
    fi

    log_message "Detected PX4 MAVLink GCS port: $PX4_GCS_MAVLINK_PORT"
}

# Function to run mavlink2rest in the background
run_mavlink2rest() {
    log_message "Starting mavlink2rest in the background..."

    # Ensure the logs directory exists
    mkdir -p "$(dirname "$MAVLINK2REST_LOG")"

    # Run mavlink2rest in the background, redirecting output to log file
    $mavlink2rest_CMD &> "$MAVLINK2REST_LOG" &
    mavlink2rest_pid=$!
    log_message "mavlink2rest started with PID: $mavlink2rest_pid. Logs: $MAVLINK2REST_LOG"
}

# Function to set up Python environment
setup_python_env() {
    if [ "$USE_GLOBAL_PYTHON" = false ]; then
        if [ ! -d "$VENV_DIR" ]; then
            log_message "Creating a Python virtual environment at $VENV_DIR..."
            python3 -m venv "$VENV_DIR"
            log_message "Virtual environment created successfully."
        else
            log_message "Python virtual environment already exists at $VENV_DIR."
        fi

        log_message "Activating the virtual environment..."
        source "$VENV_DIR/bin/activate"

        log_message "Installing Python requirements..."
        local pip_log="$BASE_DIR/logs/pip_install.log"
        if pip install --upgrade pip -q &>"$pip_log" && pip install -q -r "$BASE_DIR/requirements.txt" &>>"$pip_log"; then
            log_message "Python requirements installed successfully."
        else
            log_message "ERROR: Failed to install Python requirements. See $pip_log for details."
            exit 1
        fi
    else
        log_message "Using global Python installation."
    fi
}

# Function to set MAV_SYS_ID
set_mav_sys_id() {
    log_message "Setting MAV_SYS_ID using set_sys_id.py..."
    if python3 "$BASE_DIR/multiple_sitl/set_sys_id.py"; then
        log_message "MAV_SYS_ID set successfully."
    else
        log_message "ERROR: Failed to set MAV_SYS_ID."
        exit 1
    fi
}

# Function to read offsets from trajectory CSV
# Note: x,y positions now come from trajectory CSV files (single source of truth), not config.json
read_offsets() {
    log_message "Reading offsets from trajectory CSV for HWID: $HWID..."

    OFFSET_X=0
    OFFSET_Y=0

    if [ ! -f "$CONFIG_FILE" ]; then
        log_message "WARNING: Configuration file $CONFIG_FILE does not exist. Using default offsets (0,0)."
        return
    fi

    # Read config.json to get pos_id for this hw_id
    if ! command -v jq &>/dev/null; then
        log_message "ERROR: jq is required. Install with: apt-get install -y jq"
        exit 1
    fi

    local drone_entry
    drone_entry=$(jq -c ".drones[] | select(.hw_id == $HWID)" "$CONFIG_FILE" 2>/dev/null)

    local POS_ID=""
    if [[ -z "$drone_entry" || "$drone_entry" == "null" ]]; then
        log_message "WARNING: HWID $HWID not found in $CONFIG_FILE. Using default offsets (0,0)."
        return
    else
        POS_ID=$(echo "$drone_entry" | jq -r '.pos_id')
        log_message "Found pos_id=$POS_ID for hw_id=$HWID"
    fi

    # Read trajectory CSV to get initial position (px, py from first row)
    TRAJECTORY_FILE="$BASE_DIR/shapes_sitl/swarm/processed/Drone ${POS_ID}.csv"

    if [ ! -f "$TRAJECTORY_FILE" ]; then
        log_message "WARNING: Trajectory file not found: $TRAJECTORY_FILE"
        log_message "Falling back to row spawning with fixed spacing for drone $HWID"
        # Spawn in row with 10m spacing
        OFFSET_X=0
        OFFSET_Y=$((($HWID - 1) * 10))
        log_message "Using fallback offsets - X: $OFFSET_X, Y: $OFFSET_Y (row formation)"
        return
    fi

    # Read first waypoint (skip header, read first data row)
    # Trajectory CSV format: t,px,py,pz,vx,vy,vz,ax,ay,az,yaw,yawspeed
    local LINE_NUM=0
    while IFS=, read -r t px py pz vx vy vz ax ay az yaw yawspeed; do
        LINE_NUM=$((LINE_NUM + 1))
        # Skip header
        if [ "$LINE_NUM" -eq 1 ]; then
            continue
        fi
        # Read first data row
        OFFSET_X="$px"
        OFFSET_Y="$py"
        log_message "Found trajectory offsets from $TRAJECTORY_FILE - X: $OFFSET_X, Y: $OFFSET_Y"
        return
    done < "$TRAJECTORY_FILE"

    log_message "WARNING: Could not read trajectory data from $TRAJECTORY_FILE. Using default offsets (0,0)."
}

# Function to calculate new geographic coordinates
calculate_new_coordinates() {
    log_message "Calculating new geographic coordinates based on offsets..."

    # Constants
    EARTH_RADIUS=6371000  # in meters
    PI=3.141592653589793238

    # Convert latitude from degrees to radians
    LAT_RAD=$(echo "$DEFAULT_LAT * ($PI / 180)" | bc -l)

    # Calculate new latitude based on northward offset (OFFSET_X)
    # Formula: Δφ = (Offset_X / R) * (180 / π)
    NEW_LAT=$(echo "$DEFAULT_LAT + ($OFFSET_X / $EARTH_RADIUS) * (180 / $PI)" | bc -l)

    # Calculate meters per degree of longitude at the current latitude
    # Formula: M_per_degree = (π / 180) * R * cos(lat_rad)
    M_PER_DEGREE=$(echo "scale=10; ($PI / 180) * $EARTH_RADIUS * c($LAT_RAD)" | bc -l)

    # Calculate new longitude based on eastward offset (OFFSET_Y)
    # Formula: Δλ = Offset_Y / M_per_degree
    NEW_LON=$(echo "$DEFAULT_LON + ($OFFSET_Y / $M_PER_DEGREE)" | bc -l)

    log_message "New Coordinates - Latitude: $NEW_LAT, Longitude: $NEW_LON"
}

# Function to export environment variables for PX4 SITL
export_env_vars() {
    log_message "Exporting environment variables for PX4 SITL..."
    export PX4_HOME_LAT="$NEW_LAT"
    export PX4_HOME_LON="$NEW_LON"
    export PX4_HOME_ALT="$DEFAULT_ALT"
    export MAV_SYS_ID="$HWID"
    log_message "Environment variables set: PX4_HOME_LAT=$PX4_HOME_LAT, PX4_HOME_LON=$PX4_HOME_LON, PX4_HOME_ALT=$PX4_HOME_ALT, MAV_SYS_ID=$MAV_SYS_ID"
}

# Function to determine the simulation command
determine_simulation_command() {
    case $SIMULATION_MODE in
        g)
            SIMULATION_COMMAND="make px4_sitl gazebo"
            log_message "Simulation Mode: Graphics Enabled (Gazebo)"
            ;;
        j)
            SIMULATION_COMMAND="make px4_sitl jmavsim"
            log_message "Simulation Mode: Using jmavsim"
            ;;
        h)
            SIMULATION_COMMAND="HEADLESS=1 make px4_sitl gazebo"
            log_message "Simulation Mode: Headless (Graphics Disabled)"
            ;;
        *)
            log_message "Invalid simulation mode: $SIMULATION_MODE. Defaulting to headless mode."
            SIMULATION_COMMAND="HEADLESS=1 make px4_sitl gazebo"
            ;;
    esac

    log_message "Simulation Command: $SIMULATION_COMMAND"
}

# Function to start SITL simulation
start_simulation() {
    log_message "Starting SITL simulation..."
    cd "$PX4_DIR"

    # Export instance identifier
    export px4_instance="${HWID}-1"

    # Execute the simulation command in the background
    eval "$SIMULATION_COMMAND" &> "$BASE_DIR/logs/sitl_simulation.log" &
    simulation_pid=$!
    log_message "SITL simulation started with PID: $simulation_pid. Logs: $BASE_DIR/logs/sitl_simulation.log"
}

# Function to run coordinator.py
run_coordinator() {
    log_message "Starting coordinator.py..."
    cd "$BASE_DIR"
    if [ "$USE_GLOBAL_PYTHON" = false ]; then
        source "$VENV_DIR/bin/activate"
    fi

    if [ "$VERBOSE_MODE" = true ]; then
        log_message "Running coordinator.py in verbose mode (foreground)."
        python3 "$BASE_DIR/coordinator.py"
        # Script will wait here until coordinator.py exits
    else
        python3 "$BASE_DIR/coordinator.py" &> "$BASE_DIR/logs/coordinator.log" &
        coordinator_pid=$!
        log_message "coordinator.py started with PID: $coordinator_pid. Logs: $BASE_DIR/logs/coordinator.log"
    fi
}

# =============================================================================
# Main Script Execution
# =============================================================================

# Parse script arguments
parse_args "$@"

# Trap SIGINT and SIGTERM to execute cleanup
trap 'cleanup' INT TERM

log_message "=============================================="
log_message " Welcome to the SITL Startup Script!"
log_message "=============================================="
log_message ""
log_message "Configuration:"
log_message "  Git Remote: $GIT_REMOTE"
log_message "  Git Branch: $GIT_BRANCH"
log_message "  Use Global Python: $USE_GLOBAL_PYTHON"
log_message "  Base Directory: $BASE_DIR"
case $SIMULATION_MODE in
    g) sim_mode_desc="Graphics Enabled (Gazebo)" ;;
    j) sim_mode_desc="jMAVSim" ;;
    h) sim_mode_desc="Headless (Graphics Disabled)" ;;
    *) sim_mode_desc="Unknown ($SIMULATION_MODE)" ;;
esac
log_message "  Simulation Mode: $sim_mode_desc"
log_message "  Verbose Mode: $VERBOSE_MODE"
log_message ""

# Check for necessary dependencies
check_dependencies

# Wait for the .hwID file
wait_for_hwid

# Update the repository
update_repository

# Run MAVLink2rest in the background
#run_mavlink2rest

# Set up Python environment
setup_python_env

# Set MAV_SYS_ID
set_mav_sys_id

# Read offsets from config.json
read_offsets

# Calculate new geographic coordinates
calculate_new_coordinates

# Export environment variables
export_env_vars

# Determine simulation mode
determine_simulation_command

# Start SITL simulation
start_simulation

# Detect PX4's actual MAVLink output port before routing.
detect_px4_mavlink_port

# Start MAVLink router for external routing (replaces internal MavlinkManager)
# This routes MAVLink from the detected PX4 GCS port to local consumers and remote GCS.
if ! run_mavlink_router; then
    log_message "ERROR: Failed to start MAVLink router."
    exit 1
fi

# Start coordinator.py
run_coordinator

log_message ""
log_message "=============================================="
log_message "All processes have been initialized."
log_message "coordinator.py is running."
log_message "Press Ctrl+C to terminate the simulation."
log_message "=============================================="
log_message ""

# Wait for the simulation process to complete
wait "$simulation_pid"

if [ "$VERBOSE_MODE" = false ]; then
    # Wait for coordinator.py process to complete
    log_message "Waiting for coordinator.py process to complete..."
    wait "$coordinator_pid"
fi

# Wait for mavlink2rest process to complete (if it was started)
if [ -n "$mavlink2rest_pid" ]; then
    log_message "Waiting for mavlink2rest process to complete..."
    wait "$mavlink2rest_pid" 2>/dev/null || true
fi

# Wait for mavlink router process to complete (if it was started)
if [ -n "$mavlink_router_pid" ]; then
    log_message "Waiting for mavlink router process to complete..."
    wait "$mavlink_router_pid" 2>/dev/null || true
fi

# Exit successfully
exit 0
