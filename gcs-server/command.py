# gcs-server/command.py
"""
Drone Command Distribution System
================================
Updated with intelligent logging - tracks command success/failure patterns
without overwhelming terminal output during large swarm operations.
"""

import os
import sys
import requests
import time
from requests.exceptions import Timeout, ConnectionError
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple, Iterable

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from params import Params
from enums import CommandResultCategory

# Import the new logging system
from gcs_logging import (
    get_logger, log_drone_command, log_system_error, log_system_warning
)

def normalize_drone_id(drone_id: Any) -> str:
    """Normalize hardware/position identifiers to strings for consistent routing."""
    return str(drone_id)


def normalize_drone_ids(drone_ids: Iterable[Any]) -> List[str]:
    """Normalize a collection of drone identifiers to strings."""
    return [normalize_drone_id(drone_id) for drone_id in drone_ids]


def _summarize_ack_error(payload: Dict[str, Any]) -> str:
    """Build a concise error summary from a drone ACK payload."""
    message = str(payload.get('message') or 'Drone rejected command')
    error_code = payload.get('error_code')
    if error_code:
        return f"{error_code}: {message}"
    return message


def parse_command_ack_response(response: requests.Response) -> Tuple[bool, str, str]:
    """
    Interpret drone command ACKs.

    Drone API returns HTTP 200 for both accepted and rejected commands, with the
    actual ACK status carried in the JSON payload.
    """
    if response.status_code != 200:
        return (
            False,
            f"HTTP {response.status_code}: {response.text[:100]}",
            CommandResultCategory.REJECTED.value,
        )

    try:
        payload = response.json()
    except ValueError:
        # Older/legacy handlers may not return structured JSON. Preserve the
        # historical 200 == accepted behavior for that case.
        return True, "", CommandResultCategory.ACCEPTED.value

    if not isinstance(payload, dict):
        return True, "", CommandResultCategory.ACCEPTED.value

    status = str(payload.get('status', '')).strip().lower()
    if status in {"", "accepted", "success", "submitted"}:
        return True, "", CommandResultCategory.ACCEPTED.value

    if status == CommandResultCategory.REJECTED.value:
        return False, _summarize_ack_error(payload), CommandResultCategory.REJECTED.value

    if status == CommandResultCategory.OFFLINE.value:
        return False, _summarize_ack_error(payload), CommandResultCategory.OFFLINE.value

    return False, _summarize_ack_error(payload), CommandResultCategory.ERROR.value


def send_command_to_drone(drone: Dict[str, str], command_data: Dict[str, Any],
                         timeout: int = 5, retries: int = 3) -> Tuple[bool, str, str]:
    """
    Send a command to a specific drone with retries and intelligent logging.

    Returns:
        Tuple[bool, str, str]: (success, error_message, category)

    Categories:
        - 'accepted': Command accepted by drone
        - 'offline': Drone unreachable (timeout/connection refused) - NOT an error
        - 'rejected': Drone returned non-200 status
        - 'error': Unexpected error occurred
    """
    drone_id = normalize_drone_id(drone['hw_id'])
    drone_ip = drone['ip'] 
    command_type = command_data.get('missionType', 'UNKNOWN')
    
    attempt = 0
    backoff_factor = 1
    last_error = ""
    last_category = CommandResultCategory.ERROR.value  # Default category for failures

    # Ensure missionType is string for drone API compatibility
    command_payload = command_data.copy()
    if 'missionType' in command_payload:
        command_payload['missionType'] = str(command_payload['missionType'])

    while attempt < retries:
        try:
            response = requests.post(
                f"http://{drone_ip}:{Params.drone_api_port}/{Params.send_drone_command_URI}",
                json=command_payload,
                timeout=timeout
            )
            
            success, error_message, response_category = parse_command_ack_response(response)
            if success:
                # Success - log only for important commands or first success after failures
                if attempt > 0:  # Recovery from previous failures
                    log_drone_command(
                        drone_id, 
                        f"{command_type} (recovered after {attempt} failures)", 
                        True
                    )
                elif command_type in ['TAKEOFF', 'LAND', 'RTL', 'ARM', 'DISARM']:  # Critical commands
                    log_drone_command(drone_id, command_type, True)
                # Don't log routine successful commands to reduce noise

                return True, "", CommandResultCategory.ACCEPTED.value
            else:
                last_error = error_message
                last_category = response_category

        except (Timeout, ConnectionError) as e:
            attempt += 1
            last_error = f"{e.__class__.__name__}: Connection issue"
            last_category = CommandResultCategory.OFFLINE.value  # Network issues = drone offline (NOT an error)

            if attempt < retries:
                wait_time = backoff_factor * (2 ** (attempt - 1))
                # Only log retry attempts for critical commands or on last attempt
                if command_type in ['TAKEOFF', 'LAND', 'RTL', 'EMERGENCY'] or attempt == retries:
                    get_logger().log_drone_event(
                        drone_id, "command", 
                        f"Retry {attempt}/{retries} for {command_type} in {wait_time}s due to {e.__class__.__name__}",
                        "WARNING"
                    )
                time.sleep(wait_time)
                continue
                
        except Exception as e:
            last_error = f"Unexpected error: {str(e)[:100]}"
            break  # Don't retry on unexpected errors
            
        attempt += 1
    
    # Command failed after all retries
    # Only log as error for actual errors, not offline drones
    if last_category != CommandResultCategory.OFFLINE.value:
        log_drone_command(drone_id, command_type, False, last_error)
    # Offline drones are logged at DEBUG level (not worth cluttering logs)

    return False, last_error, last_category

def send_commands_to_all(drones: List[Dict[str, str]], command_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a command to all drones concurrently with comprehensive result tracking.
    
    Returns:
        Dict with success/failure counts and details
    """
    if not drones:
        log_system_warning("No drones provided for command execution", "command")
        return {
            'success': 0, 'offline': 0, 'rejected': 0, 'errors': 0,
            'failed': 0, 'total': 0, 'result_summary': 'no drones', 'results': {}
        }
    
    command_type = command_data.get('missionType', 'UNKNOWN')
    logger = get_logger()
    
    # Log command initiation for swarm operations
    logger.log_system_event(
        f"Sending '{command_type}' command to {len(drones)} drones",
        "INFO", "command"
    )
    
    start_time = time.time()
    results = {}
    success_count = 0
    offline_count = 0
    rejected_count = 0
    error_count = 0
    
    # Execute commands concurrently
    with ThreadPoolExecutor(max_workers=min(len(drones), 20)) as executor:
        # Submit all commands
        future_to_drone = {
            executor.submit(send_command_to_drone, drone, command_data): drone
            for drone in drones
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_drone):
            drone = future_to_drone[future]
            drone_id = normalize_drone_id(drone['hw_id'])

            try:
                success, error, category = future.result()
                results[drone_id] = {
                    'success': success,
                    'category': category,
                    'error': error if error else None,
                    'drone_ip': drone['ip']
                }

                if success:
                    success_count += 1
                elif category == CommandResultCategory.OFFLINE.value:
                    offline_count += 1
                elif category == CommandResultCategory.REJECTED.value:
                    rejected_count += 1
                else:
                    error_count += 1

            except Exception as e:
                # Thread execution error
                error_msg = f"Thread execution failed: {str(e)}"
                results[drone_id] = {
                    'success': False,
                    'category': CommandResultCategory.ERROR.value,
                    'error': error_msg,
                    'drone_ip': drone['ip']
                }
                error_count += 1
                log_drone_command(drone_id, command_type, False, error_msg)
    
    # Calculate execution time
    execution_time = time.time() - start_time
    # failed_count only includes actual failures (rejected/errors), not offline
    failed_count = rejected_count + error_count
    unavailable_count = offline_count  # Separate tracking for unreachable drones

    # Log comprehensive summary with categorization
    success_rate = (success_count / len(drones)) * 100 if drones else 0
    reachable_count = success_count + rejected_count + error_count  # Drones that responded

    # Build result summary string
    parts = []
    if success_count > 0:
        parts.append(f"{success_count} accepted")
    if offline_count > 0:
        parts.append(f"{offline_count} offline")
    if rejected_count > 0:
        parts.append(f"{rejected_count} rejected")
    if error_count > 0:
        parts.append(f"{error_count} errors")
    result_summary = ", ".join(parts) if parts else "no results"

    if success_count == len(drones):
        # Perfect success
        logger.log_system_event(
            f"Command '{command_type}' completed: {result_summary} in {execution_time:.2f}s",
            "INFO", "command"
        )
    elif offline_count == len(drones):
        # All drones offline - informational, not an error
        logger.log_system_event(
            f"Command '{command_type}': {result_summary} (no reachable drones) in {execution_time:.2f}s",
            "INFO", "command"
        )
    elif success_count > 0 and error_count == 0 and rejected_count == 0:
        # Some accepted, rest offline - informational
        logger.log_system_event(
            f"Command '{command_type}' completed: {result_summary} in {execution_time:.2f}s",
            "INFO", "command"
        )
    elif error_count > 0 or rejected_count > 0:
        # Actual errors or rejections - warning/error level
        log_level = "ERROR" if success_count == 0 else "WARNING"
        logger.log_system_event(
            f"Command '{command_type}' completed: {result_summary} in {execution_time:.2f}s",
            log_level, "command"
        )
    else:
        # Fallback
        logger.log_system_event(
            f"Command '{command_type}' completed: {result_summary} in {execution_time:.2f}s",
            "INFO", "command"
        )
    
    # Log details of failures by category
    if rejected_count > 0 or error_count > 0:
        # Only log rejected/error drones (not offline - that's expected)
        problem_categories = (CommandResultCategory.REJECTED.value, CommandResultCategory.ERROR.value)
        problem_drones = [
            normalize_drone_id(drone_id) for drone_id, result in results.items()
            if result.get('category') in problem_categories
        ]

        # Group by category and error type for cleaner reporting
        category_groups = {}
        for drone_id in problem_drones:
            result = results[drone_id]
            category = result.get('category', CommandResultCategory.ERROR.value)
            error = result['error'] or "Unknown error"
            key = f"{category}:{error.split(':')[0]}"
            if key not in category_groups:
                category_groups[key] = []
            category_groups[key].append(drone_id)

        for key, drone_list in category_groups.items():
            category, error_type = key.split(':', 1)
            log_level = "ERROR" if category == CommandResultCategory.ERROR.value else "WARNING"
            logger.log_system_event(
                f"Command '{command_type}' {category} ({error_type}) on drones: {', '.join(drone_list[:10])}{'...' if len(drone_list) > 10 else ''}",
                log_level, "command"
            )
    
    return {
        'success': success_count,
        'offline': offline_count,
        'rejected': rejected_count,
        'errors': error_count,
        'failed': failed_count,  # Only rejected + errors (actual failures)
        'unavailable': unavailable_count,  # Offline drones (not a failure)
        'total': len(drones),
        'success_rate': success_rate,
        'execution_time': execution_time,
        'result_summary': result_summary,  # Human-readable summary
        'results': results
    }

def send_commands_to_selected(drones: List[Dict[str, str]], command_data: Dict[str, Any], 
                            target_drone_ids: List[str]) -> Dict[str, Any]:
    """
    Send commands to specific drones only.
    
    Args:
        drones: All available drones
        command_data: Command to send
        target_drone_ids: List of specific drone IDs to target
        
    Returns:
        Dict with execution results
    """
    # Normalize drone IDs to strings (frontend may send integers)
    target_drone_ids = normalize_drone_ids(target_drone_ids) if target_drone_ids else []

    if not target_drone_ids:
        log_system_warning("No target drones specified for selective command", "command")
        return {
            'success': 0, 'offline': 0, 'rejected': 0, 'errors': 0,
            'failed': 0, 'total': 0, 'result_summary': 'no targets', 'results': {}
        }
    
    # Filter drones to only target ones
    target_drones = [
        drone for drone in drones 
        if normalize_drone_id(drone.get('hw_id')) in target_drone_ids
    ]
    
    if len(target_drones) != len(target_drone_ids):
        found_ids = normalize_drone_ids(drone.get('hw_id') for drone in target_drones)
        missing_ids = set(target_drone_ids) - set(found_ids)
        
        log_system_warning(
            f"Some target drones not found in configuration: {', '.join(missing_ids)}",
            "command"
        )
    
    if not target_drones:
        log_system_error("No valid target drones found for selective command", "command")
        return {
            'success': 0, 'offline': 0, 'rejected': 0, 'errors': 0,
            'failed': 0, 'total': 0, 'result_summary': 'no valid targets', 'results': {}
        }
    
    # Use the same logic as send_commands_to_all but with filtered drones
    return send_commands_to_all(target_drones, command_data)

def validate_command_data(command_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate command data structure and content.
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not isinstance(command_data, dict):
        return False, "Command data must be a dictionary"
    
    # Check required fields
    required_fields = ['missionType']
    missing_fields = [field for field in required_fields if field not in command_data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    # Validate mission type
    mission_type = command_data.get('missionType')
    if not isinstance(mission_type, (int, str)):
        return False, "missionType must be an integer or string"
    
    # Additional validation can be added here for specific command types
    
    return True, ""

def execute_drone_command(drones: List[Dict[str, str]], command_data: Dict[str, Any], 
                         target_drone_ids: List[str] = None) -> Dict[str, Any]:
    """
    Main entry point for drone command execution with validation and logging.
    
    Args:
        drones: Available drones
        command_data: Command to execute
        target_drone_ids: Optional list of specific drones to target
        
    Returns:
        Dict with execution results and status
    """
    logger = get_logger()
    
    # Validate command data
    is_valid, error_msg = validate_command_data(command_data)
    if not is_valid:
        log_system_error(f"Invalid command data: {error_msg}", "command")
        return {
            'status': 'error',
            'message': f"Invalid command data: {error_msg}",
            'results': {}
        }
    
    # Validate drone list
    if not drones:
        log_system_error("No drones available for command execution", "command")
        return {
            'status': 'error', 
            'message': "No drones available",
            'results': {}
        }
    
    try:
        # Execute command
        if target_drone_ids:
            results = send_commands_to_selected(drones, command_data, target_drone_ids)
        else:
            results = send_commands_to_all(drones, command_data)
        
        # Determine overall status
        if results['failed'] == 0:
            status = 'success'
            message = f"Command executed successfully on all {results['total']} drones"
        elif results['success'] > 0:
            status = 'partial'
            message = f"Command partially successful: {results['success']}/{results['total']} drones"
        else:
            status = 'failed'
            message = f"Command failed on all {results['total']} drones"
        
        return {
            'status': status,
            'message': message,
            'results': results
        }
        
    except Exception as e:
        error_msg = f"Unexpected error during command execution: {str(e)}"
        log_system_error(error_msg, "command")
        return {
            'status': 'error',
            'message': error_msg,
            'results': {}
        }

# Standalone test mode
if __name__ == "__main__":
    import argparse
    from gcs_logging import initialize_logging, LogLevel, DisplayMode
    from config import load_config
    
    parser = argparse.ArgumentParser(description='Test drone command system')
    parser.add_argument('--log-level', choices=['QUIET', 'NORMAL', 'VERBOSE', 'DEBUG'],
                       default='VERBOSE', help='Log level')
    parser.add_argument('--command', required=True, help='Command to send (e.g., ARM, TAKEOFF, LAND)')
    parser.add_argument('--drones', nargs='*', help='Specific drone IDs to target')
    args = parser.parse_args()
    
    # Initialize logging
    initialize_logging(LogLevel[args.log_level], DisplayMode.STREAM)
    
    # Load drones
    drones = load_config()
    if not drones:
        print("No drones found in configuration!")
        sys.exit(1)
    
    # Prepare command data
    command_data = {
        'missionType': args.command.upper(),
        'triggerTime': '0',
        'target_drones': args.drones or []
    }
    
    print(f"Sending {args.command.upper()} command to {'specific' if args.drones else 'all'} drones...")
    
    # Execute command
    result = execute_drone_command(drones, command_data, args.drones)
    
    print(f"Command execution result: {result['status']}")
    print(f"Message: {result['message']}")
    
    if 'results' in result and result['results']:
        stats = result['results']
        print(f"Success rate: {stats.get('success_rate', 0):.1f}%")
        print(f"Execution time: {stats.get('execution_time', 0):.2f}s")
