# gcs-server/routes/config_routes.py
"""
Configuration Routes Blueprint
==============================
Flask blueprint for configuration-related endpoints.

Endpoints:
- GET /get-config-data - Get drone configuration
- POST /save-config-data - Save drone configuration
- POST /validate-config - Validate configuration without saving
- GET /get-drone-positions - Get positions from trajectory files
- GET /get-trajectory-first-row - Get first waypoint from trajectory
"""

import os
from datetime import datetime
from flask import Blueprint, jsonify, request

from config import load_config, save_config, validate_and_process_config
from origin import _get_expected_position_from_trajectory
from utils import git_operations
from params import Params

# Import logging utilities
try:
    from logging_config import get_logger
    def log_system_event(message, level="INFO", component="system"):
        get_logger().log_system_event(message, level, component)
    def log_system_error(message, component="system"):
        get_logger().log_system_event(message, "ERROR", component)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    def log_system_event(message, level="INFO", component="system"):
        logger.log(getattr(logging, level, logging.INFO), f"[{component}] {message}")
    def log_system_error(message, component="system"):
        logger.error(f"[{component}] {message}")

# Base directory
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

# Create blueprint
config_bp = Blueprint('config', __name__)


def error_response(message, status_code=500):
    """Standard error response format"""
    return jsonify({'status': 'error', 'message': message}), status_code


@config_bp.route('/get-config-data', methods=['GET'])
def get_config():
    """Get drone configuration from config.csv"""
    try:
        config = load_config()
        return jsonify(config)
    except Exception as e:
        return error_response(f"Error loading configuration: {e}")


@config_bp.route('/save-config-data', methods=['POST'])
def save_config_route():
    """
    Save drone configuration to config.csv.

    NOTE: x,y positions are NOT saved in config.csv. They are always fetched
    from trajectory CSV files. Use /get-drone-positions to retrieve positions.
    """
    config_data = request.get_json()
    if not config_data:
        return error_response("No configuration data provided", 400)

    log_system_event("Configuration update received", "INFO", "config")

    try:
        # Validate config_data
        if not isinstance(config_data, list) or not all(isinstance(drone, dict) for drone in config_data):
            raise ValueError("Invalid configuration data format")

        # Validate and process config (removes x,y if present)
        sim_mode = getattr(Params, 'sim_mode', False)
        report = validate_and_process_config(config_data, sim_mode)

        # Save the processed configuration (without x,y fields)
        save_config(report['updated_config'])
        log_system_event("Configuration saved successfully", "INFO", "config")

        git_info = None
        # If auto push to Git is enabled, perform Git operations
        if Params.GIT_AUTO_PUSH:
            log_system_event(
                "Git auto-push enabled. Attempting to push configuration changes.",
                "INFO", "config"
            )
            git_result = git_operations(
                BASE_DIR,
                f"Update configuration: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            if git_result.get('success'):
                log_system_event("Git operations successful.", "INFO", "config")
            else:
                log_system_error(f"Git operations failed: {git_result.get('message')}", "config")
            git_info = git_result

        # Return a success message, including Git info if applicable
        response_data = {'status': 'success', 'message': 'Configuration saved successfully'}
        if git_info:
            response_data['git_info'] = git_info

        return jsonify(response_data)

    except Exception as e:
        log_system_error(f"Error saving configuration: {e}", "config")
        return error_response(f"Error saving configuration: {e}")


@config_bp.route('/validate-config', methods=['POST'])
def validate_config_route():
    """
    Validate configuration (positions come from trajectory CSV only).
    Returns validation report WITHOUT saving to file.
    Used by UI to show review dialog before final save.
    """
    config_data = request.get_json()
    if not config_data:
        return error_response("No configuration data provided", 400)

    log_system_event("Configuration validation requested", "INFO", "config")

    try:
        # Validate config_data format
        if not isinstance(config_data, list) or not all(isinstance(drone, dict) for drone in config_data):
            raise ValueError("Invalid configuration data format")

        # Validate and process config
        sim_mode = getattr(Params, 'sim_mode', False)
        report = validate_and_process_config(config_data, sim_mode)

        log_system_event(
            f"Validation complete: {report['summary']['duplicates_count']} duplicates, "
            f"{report['summary']['missing_trajectories_count']} missing trajectories, "
            f"{report['summary']['role_swaps_count']} role swaps",
            "INFO",
            "config"
        )

        return jsonify(report)

    except Exception as e:
        log_system_error(f"Error validating configuration: {e}", "config")
        return error_response(f"Error validating configuration: {e}")


@config_bp.route('/get-drone-positions', methods=['GET'])
def get_drone_positions():
    """
    Get initial positions for all drones from trajectory CSV files.

    This is the SINGLE SOURCE OF TRUTH for drone positions. Positions are always
    read from the first row of each drone's trajectory CSV file based on pos_id.

    Returns:
        JSON array: [{"hw_id": int, "pos_id": int, "x": float, "y": float}, ...]
    """
    try:
        from config import get_all_drone_positions

        positions = get_all_drone_positions()

        if not positions:
            log_system_event("No drone positions retrieved (config may be empty)", "WARNING", "config")
        else:
            log_system_event(f"Retrieved positions for {len(positions)} drones", "INFO", "config")

        return jsonify(positions)

    except Exception as e:
        log_system_error(f"Error fetching all drone positions: {e}", "config")
        return error_response(f"Error fetching drone positions: {e}")


@config_bp.route('/get-trajectory-first-row', methods=['GET'])
def get_trajectory_first_row():
    """
    Get expected position (first row) from trajectory CSV file.
    Used by auto-accept pos_id feature to fetch correct x,y coordinates.
    """
    try:
        pos_id = request.args.get('pos_id')
        if not pos_id:
            return error_response("pos_id parameter required", 400)

        pos_id = int(pos_id)
        sim_mode = getattr(Params, 'sim_mode', False)

        # Get expected position from trajectory CSV
        north, east = _get_expected_position_from_trajectory(pos_id, sim_mode)

        if north is None or east is None:
            return error_response(
                f"Trajectory file not found for pos_id={pos_id}",
                404
            )

        return jsonify({
            "pos_id": pos_id,
            "north": north,
            "east": east,
            "source": f"Drone {pos_id}.csv (first waypoint)"
        })

    except ValueError as e:
        return error_response(f"Invalid pos_id: {e}", 400)
    except Exception as e:
        log_system_error(f"Error fetching trajectory coordinates: {e}", "config")
        return error_response(f"Error fetching trajectory data: {e}")
