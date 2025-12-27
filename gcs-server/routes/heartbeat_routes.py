# gcs-server/routes/heartbeat_routes.py
"""
Heartbeat Routes Blueprint
==========================
Flask blueprint for heartbeat and network-related endpoints.

Endpoints:
- POST /drone-heartbeat - Receive heartbeat from drone
- GET /get-heartbeats - Get all drone heartbeats
- GET /get-network-info - Get network info for all drones
"""

from flask import Blueprint, jsonify

from heartbeat import handle_heartbeat_post, get_all_heartbeats, get_network_info_from_heartbeats

# Import logging utilities
try:
    from logging_config import get_logger
    def log_system_error(message, component="system"):
        get_logger().log_system_event(message, "ERROR", component)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    def log_system_error(message, component="system"):
        logger.error(f"[{component}] {message}")

# Create blueprint
heartbeat_bp = Blueprint('heartbeat', __name__)


@heartbeat_bp.route('/drone-heartbeat', methods=['POST'])
def drone_heartbeat():
    """Receive heartbeat from drone"""
    return handle_heartbeat_post()


@heartbeat_bp.route('/get-heartbeats', methods=['GET'])
def get_heartbeats():
    """Get all drone heartbeats"""
    return get_all_heartbeats()


@heartbeat_bp.route('/get-network-info', methods=['GET'])
def get_network_info():
    """
    Endpoint to get network information for all drones.
    Now efficiently sourced from heartbeat data instead of separate polling.
    """
    try:
        network_info_list, status_code = get_network_info_from_heartbeats()
        return jsonify(network_info_list), status_code
    except Exception as e:
        log_system_error(f"Error getting network info from heartbeats: {e}", "network")
        return jsonify([]), 200  # Return empty array to prevent UI errors
