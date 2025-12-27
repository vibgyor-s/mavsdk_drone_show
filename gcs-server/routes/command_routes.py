# gcs-server/routes/command_routes.py
"""
Command Routes Blueprint
========================
Flask blueprint for command-related endpoints.

Endpoints:
- POST /submit_command - Submit command to drones
"""

import threading
import time
from flask import Blueprint, jsonify, request

from config import load_config
from command import send_commands_to_all, send_commands_to_selected
from origin import load_origin

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
command_bp = Blueprint('command', __name__)


def error_response(message, status_code=500):
    """Standard error response format"""
    return jsonify({'status': 'error', 'message': message}), status_code


@command_bp.route('/submit_command', methods=['POST'])
def submit_command():
    """
    Endpoint to receive commands from the frontend and process them asynchronously.

    Phase 2 Enhancement: If auto_global_origin is True, include origin data in command payload.
    """
    command_data = request.get_json()
    if not command_data:
        return error_response("No command data provided", 400)

    # Extract target_drones from command_data if provided
    target_drones = command_data.pop('target_drones', None)

    # Phase 2: Include origin data if auto_global_origin is enabled
    auto_global_origin = command_data.get('auto_global_origin', False)
    if auto_global_origin:
        try:
            origin = load_origin()
            if origin and origin.get('lat') and origin.get('lon'):
                command_data['origin'] = {
                    'lat': float(origin['lat']),
                    'lon': float(origin['lon']),
                    'alt': float(origin.get('alt', 0)),
                    'timestamp': origin.get('timestamp', ''),
                    'source': origin.get('alt_source', 'gcs')
                }
                log_system_event(
                    f"Phase 2: Including origin in command (lat={origin['lat']:.6f}, lon={origin['lon']:.6f})",
                    "INFO", "command"
                )
            else:
                log_system_event(
                    "Phase 2: auto_global_origin=True but origin not set! Drones will fetch from GCS.",
                    "WARNING", "command"
                )
        except Exception as e:
            log_system_error(f"Phase 2: Failed to load origin for command: {e}", "command")

    # Professional command logging
    if target_drones:
        log_system_event(
            f"Command '{command_data.get('action', 'unknown')}' received for {len(target_drones)} selected drones",
            "INFO", "command"
        )
    else:
        log_system_event(
            f"Command '{command_data.get('action', 'unknown')}' received for all drones",
            "INFO", "command"
        )

    try:
        drones = load_config()
        if not drones:
            return error_response("No drones found in the configuration", 500)

        # Start processing the command in a new thread
        if target_drones:
            thread = threading.Thread(
                target=process_command_async,
                args=(drones, command_data, target_drones)
            )
        else:
            thread = threading.Thread(
                target=process_command_async,
                args=(drones, command_data)
            )

        thread.daemon = True
        thread.start()

        response_data = {
            'status': 'success',
            'message': "Command received and is being processed."
        }
        return jsonify(response_data), 200

    except Exception as e:
        log_system_error(f"Error initiating command processing: {e}", "command")
        return error_response(f"Error initiating command processing: {e}")


def process_command_async(drones, command_data, target_drones=None):
    """
    Function to process the command asynchronously.
    """
    try:
        start_time = time.time()

        # Choose appropriate sending function based on target_drones
        if target_drones:
            results = send_commands_to_selected(drones, command_data, target_drones)
            total_count = len(target_drones)
        else:
            results = send_commands_to_all(drones, command_data)
            total_count = len(drones)

        elapsed_time = time.time() - start_time
        success_count = sum(results.values())

        # Professional command completion logging
        if success_count == total_count:
            log_system_event(
                f"Command completed successfully on all {total_count} drones ({elapsed_time:.2f}s)",
                "INFO", "command"
            )
        else:
            log_system_event(
                f"Command partially completed: {success_count}/{total_count} drones succeeded ({elapsed_time:.2f}s)",
                "WARNING", "command"
            )
    except Exception as e:
        log_system_error(f"Error processing command asynchronously: {e}", "command")
