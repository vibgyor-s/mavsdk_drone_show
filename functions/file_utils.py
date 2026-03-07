# functions/file_utils.py
"""
File Utilities Module
=====================
Centralized CSV and file I/O operations for the MAVSDK Drone Show project.

This module provides:
- CSV loading and saving with error handling
- Configuration file management
- Trajectory file parsing

All CSV operations should use these functions to ensure consistent
error handling and logging across the codebase.
"""

import csv
import json
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# CSV Operations
# ============================================================================

def load_csv(file_path: str) -> List[Dict[str, Any]]:
    """
    Load data from a CSV file.

    Args:
        file_path: Path to the CSV file

    Returns:
        List of dictionaries, one per row. Empty list if file not found or empty.

    Example:
        >>> data = load_csv('/path/to/data.csv')
        >>> print(data[0]['hw_id'])
        '1'
    """
    data = []

    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return data

    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                data.append(dict(row))  # Convert OrderedDict to regular dict

        if not data:
            logger.warning(f"File is empty: {file_path}")

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except csv.Error as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
    except UnicodeDecodeError as e:
        logger.error(f"Encoding error reading {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error loading file {file_path}: {e}")

    return data


def save_csv(
    data: List[Dict[str, Any]],
    file_path: str,
    fieldnames: Optional[List[str]] = None
) -> bool:
    """
    Save data to a CSV file with specified column order.

    Args:
        data: List of dictionaries to save
        file_path: Path to the output CSV file
        fieldnames: Optional list of column names in desired order.
                   If not provided, uses keys from first data row.

    Returns:
        True if save successful, False otherwise.

    Example:
        >>> data = [{'hw_id': '1', 'pos_id': '1', 'ip': '192.168.1.100'}]
        >>> save_csv(data, '/path/to/data.csv', fieldnames=['hw_id', 'pos_id', 'ip'])
        True
    """
    if not data:
        logger.warning(f"No data provided to save in {file_path}. Operation aborted.")
        return False

    try:
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            # Use provided fieldnames or keys from first row
            columns = fieldnames if fieldnames else list(data[0].keys())
            writer = csv.DictWriter(file, fieldnames=columns, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(data)

        logger.info(f"Data successfully saved to {file_path}")
        return True

    except FileNotFoundError:
        logger.error(f"Directory not found for: {file_path}")
    except csv.Error as e:
        logger.error(f"Error writing CSV file {file_path}: {e}")
    except IOError as e:
        logger.error(f"IO error saving file {file_path}: {e}")
    except PermissionError as e:
        logger.error(f"Permission denied saving {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving file {file_path}: {e}")

    return False


def validate_csv_schema(
    data: List[Dict[str, Any]],
    required_columns: List[str]
) -> tuple[bool, List[str]]:
    """
    Validate that CSV data contains required columns.

    Args:
        data: List of dictionaries from CSV
        required_columns: List of column names that must be present

    Returns:
        Tuple of (is_valid, missing_columns)

    Example:
        >>> data = [{'hw_id': '1', 'pos_id': '1'}]
        >>> is_valid, missing = validate_csv_schema(data, ['hw_id', 'pos_id', 'ip'])
        >>> print(is_valid, missing)
        False ['ip']
    """
    if not data:
        return False, required_columns

    present_columns = set(data[0].keys())
    missing = [col for col in required_columns if col not in present_columns]

    return len(missing) == 0, missing


# ============================================================================
# JSON Operations
# ============================================================================

def load_json(file_path: str) -> Any:
    """Load and parse a JSON file. Returns parsed data or empty dict on error."""
    if not os.path.exists(file_path):
        logger.warning(f"JSON file not found: {file_path}")
        return {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading JSON from {file_path}: {e}")
        return {}


def save_json(data: Any, file_path: str, indent: int = 2) -> bool:
    """Save data as pretty-printed JSON. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.write('\n')  # Trailing newline for git
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        return False


# ============================================================================
# Trajectory File Operations
# ============================================================================

def load_trajectory_csv(file_path: str) -> List[Dict[str, float]]:
    """
    Load trajectory waypoints from a CSV file.

    Expects columns: t [ms], x [m], y [m], z [m], yaw [deg]
    or: t, px, py, pz, yaw

    Args:
        file_path: Path to trajectory CSV file

    Returns:
        List of waypoint dictionaries with keys: t, x, y, z, yaw
    """
    data = load_csv(file_path)
    if not data:
        return []

    waypoints = []
    for row in data:
        try:
            # Handle both naming conventions
            waypoint = {
                't': float(row.get('t [ms]', row.get('t', 0))),
                'x': float(row.get('x [m]', row.get('px', 0))),
                'y': float(row.get('y [m]', row.get('py', 0))),
                'z': float(row.get('z [m]', row.get('pz', 0))),
                'yaw': float(row.get('yaw [deg]', row.get('yaw', 0)))
            }
            waypoints.append(waypoint)
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping invalid waypoint row in {file_path}: {e}")
            continue

    return waypoints


def get_trajectory_duration(waypoints: List[Dict[str, float]]) -> float:
    """
    Get the total duration of a trajectory in seconds.

    Args:
        waypoints: List of waypoint dictionaries with 't' key (in ms)

    Returns:
        Duration in seconds
    """
    if not waypoints:
        return 0.0

    max_time = max(wp.get('t', 0) for wp in waypoints)
    return max_time / 1000.0  # Convert ms to seconds


def get_trajectory_first_position(file_path: str) -> Optional[Dict[str, float]]:
    """
    Get the first position from a trajectory file.

    Args:
        file_path: Path to trajectory CSV file

    Returns:
        Dictionary with x, y, z coordinates or None if file is empty/invalid
    """
    waypoints = load_trajectory_csv(file_path)
    if not waypoints:
        return None

    first = waypoints[0]
    return {'x': first['x'], 'y': first['y'], 'z': first['z']}
