# gcs-server/routes/git_routes.py
"""
Git Status Routes Blueprint
===========================
Flask blueprint for Git status-related endpoints.

Endpoints:
- GET /git-status - Get consolidated git status of all drones
- GET /get-gcs-git-status - Get GCS git status
- GET /get-drone-git-status/<drone_id> - Get specific drone's git status
"""

from flask import Blueprint, jsonify

from config import load_config, get_gcs_git_report, get_drone_git_status
from git_status import git_status_data_all_drones, data_lock_git_status
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

# Create blueprint
git_bp = Blueprint('git', __name__)


@git_bp.route('/git-status', methods=['GET'])
def get_git_status():
    """Endpoint to retrieve consolidated git status of all drones."""
    with data_lock_git_status:
        git_status_copy = git_status_data_all_drones.copy()
    return jsonify(git_status_copy)


@git_bp.route('/get-gcs-git-status', methods=['GET'])
def get_gcs_git_status():
    """Retrieve the Git status of the GCS."""
    gcs_status = get_gcs_git_report()
    return jsonify(gcs_status)


@git_bp.route('/get-drone-git-status/<int:drone_id>', methods=['GET'])
def fetch_drone_git_status(drone_id):
    """
    Endpoint to retrieve the Git status of a specific drone using its hardware ID (hw_id).

    Args:
        drone_id: Hardware ID (hw_id) of the drone.

    Returns:
        JSON response with Git status or an error message.
    """
    try:
        log_system_event(f"Fetching drone with ID {drone_id} from configuration", "DEBUG", "git")
        drones = load_config()
        drone = next((d for d in drones if int(d['hw_id']) == drone_id), None)

        if not drone:
            log_system_error(f'Drone with ID {drone_id} not found', "git")
            return jsonify({'error': f'Drone with ID {drone_id} not found'}), 404

        drone_uri = f"http://{drone['ip']}:{Params.drone_api_port}"
        log_system_event(f"Constructed drone URI: {drone_uri}", "DEBUG", "git")
        drone_status = get_drone_git_status(drone_uri)

        if 'error' in drone_status:
            log_system_error(f"Error in drone status response: {drone_status['error']}", "git")
            return jsonify({'error': drone_status['error']}), 500

        log_system_event(f"Drone status retrieved successfully: {drone_status}", "DEBUG", "git")
        return jsonify(drone_status), 200

    except Exception as e:
        log_system_error(f"Exception occurred: {str(e)}", "git")
        return jsonify({'error': str(e)}), 500
