# gcs-server/routes/telemetry_routes.py
"""
Telemetry Routes Blueprint
==========================
Flask blueprint for telemetry-related endpoints.

Endpoints:
- GET /telemetry - Get current telemetry data for all drones
"""

from flask import Blueprint, jsonify

# Import telemetry data from the main telemetry module
from telemetry import telemetry_data_all_drones

# Create blueprint
telemetry_bp = Blueprint('telemetry', __name__)


@telemetry_bp.route('/telemetry', methods=['GET'])
def get_telemetry():
    """
    Get current telemetry data for all drones.

    This endpoint is called frequently by the dashboard.
    Returns the global telemetry data dictionary.

    Returns:
        JSON object with telemetry data keyed by hw_id
    """
    return jsonify(telemetry_data_all_drones)
