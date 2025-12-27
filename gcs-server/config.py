#gcs-server/config.py
"""
GCS Configuration Management
=============================
Handles drone configuration, swarm settings, and Git status operations.

Shared utilities:
- CSV operations: functions/file_utils.py
- Git operations: functions/git_manager.py
"""
import os
import logging
from params import Params
from collections import defaultdict

# Import shared utilities (single source of truth)
from functions.file_utils import load_csv, save_csv
from functions.git_manager import get_local_git_report, get_remote_git_status

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE_PATH = os.path.join(BASE_DIR, Params.config_csv_name)
SWARM_FILE_PATH = os.path.join(BASE_DIR, Params.swarm_csv_name)

logger = logging.getLogger(__name__)

# Define the expected column order
# Note: x,y removed - positions are now always fetched from trajectory CSV (single source of truth)
CONFIG_COLUMNS = ['hw_id', 'pos_id', 'ip', 'mavlink_port', 'serial_port', 'baudrate']
SWARM_COLUMNS = ['hw_id' , 'follow' , 'offset_n' , 'offset_e' , 'offset_alt' , 'body_coord']

def load_config(file_path=CONFIG_FILE_PATH):
    return load_csv(file_path)

def save_config(config, file_path=CONFIG_FILE_PATH):
    # Pass the expected column order to ensure consistent column placement
    save_csv(config, file_path, fieldnames=CONFIG_COLUMNS)

def load_swarm(file_path=SWARM_FILE_PATH):
    return load_csv(file_path)

def save_swarm(swarm, file_path=SWARM_FILE_PATH):
    save_csv(swarm, file_path,fieldnames=SWARM_COLUMNS)


def get_gcs_git_report():
    """
    Retrieve the Git status of the GCS.

    Delegates to functions.git_manager.get_local_git_report() for implementation.
    """
    return get_local_git_report()


def get_drone_git_status(drone_uri):
    """
    Retrieve the Git status from a specific drone.

    Delegates to functions.git_manager.get_remote_git_status() for implementation.
    """
    return get_remote_git_status(drone_uri)


def validate_and_process_config(config_data, sim_mode=None):
    """
    Validate drone configuration (positions now come from trajectory CSV only).

    This function:
    1. Validates trajectory CSV exists for each pos_id
    2. Detects duplicate pos_id values (collision risk)
    3. Identifies missing trajectory files
    4. Tracks role swaps (hw_id ≠ pos_id)
    5. Removes x,y fields from config (no longer stored in config.csv)
    6. Returns comprehensive validation report

    NOTE: x,y positions are NOT stored in config.csv. They are always fetched
    from trajectory CSV files (single source of truth). Use get_all_drone_positions()
    or /get-drone-positions API to retrieve positions.

    Args:
        config_data (list): List of drone config dictionaries
        sim_mode (bool): Whether in simulation mode (affects trajectory path)

    Returns:
        dict: Validation report with updated_config, warnings, and changes
    """
    from coordinate_utils import get_expected_position_from_trajectory

    # Detect sim_mode if not provided
    if sim_mode is None:
        sim_mode = getattr(Params, 'sim_mode', False)

    # Initialize tracking structures
    updated_config = []
    warnings = {
        "duplicates": [],
        "missing_trajectories": [],
        "role_swaps": []
    }
    changes = {
        "pos_id_changes": []
    }

    # Track pos_id usage for duplicate detection
    pos_id_usage = defaultdict(list)

    # Load original config for comparison
    original_config_list = load_config()
    original_config = {int(d.get('hw_id')): d for d in original_config_list if d.get('hw_id')}

    # Process each drone in new config
    for drone in config_data:
        try:
            hw_id = int(drone.get('hw_id'))
            pos_id = drone.get('pos_id')

            if not pos_id:
                # Fallback: if no pos_id, assume pos_id == hw_id
                pos_id = hw_id
                drone['pos_id'] = pos_id
            else:
                pos_id = int(pos_id)

            # Track pos_id usage for duplicate detection
            pos_id_usage[pos_id].append(hw_id)

            # Track pos_id changes
            if hw_id in original_config:
                orig_pos_id = int(original_config[hw_id].get('pos_id', hw_id))
                if orig_pos_id != pos_id:
                    changes["pos_id_changes"].append({
                        "hw_id": hw_id,
                        "old_pos_id": orig_pos_id,
                        "new_pos_id": pos_id
                    })

            # Track role swaps
            if hw_id != pos_id:
                warnings["role_swaps"].append({
                    "hw_id": hw_id,
                    "pos_id": pos_id
                })

            # Check if trajectory file exists for this pos_id
            expected_north, expected_east = get_expected_position_from_trajectory(pos_id, sim_mode)

            if expected_north is None or expected_east is None:
                # Missing trajectory file
                warnings["missing_trajectories"].append({
                    "hw_id": hw_id,
                    "pos_id": pos_id,
                    "message": f"Trajectory file 'Drone {pos_id}.csv' not found"
                })

            # Note: x,y removed from config.csv - positions always come from trajectory CSV
            # Just copy the drone config without x,y fields
            updated_drone = dict(drone)
            # Remove x,y if they exist in input (for backward compatibility during migration)
            updated_drone.pop('x', None)
            updated_drone.pop('y', None)

            updated_config.append(updated_drone)

        except Exception as e:
            logger.error(f"Error processing drone config: {e}")
            # Keep original drone config on error
            updated_config.append(dict(drone))

    # Detect duplicate pos_id values
    for pos_id, hw_ids in pos_id_usage.items():
        if len(hw_ids) > 1:
            warnings["duplicates"].append({
                "pos_id": pos_id,
                "hw_ids": hw_ids,
                "message": f"COLLISION RISK: pos_id {pos_id} assigned to drones {hw_ids}"
            })

    # Build comprehensive report
    report = {
        "success": True,
        "updated_config": updated_config,
        "warnings": warnings,
        "changes": changes,
        "summary": {
            "total_drones": len(updated_config),
            "pos_id_changes_count": len(changes["pos_id_changes"]),
            "duplicates_count": len(warnings["duplicates"]),
            "missing_trajectories_count": len(warnings["missing_trajectories"]),
            "role_swaps_count": len(warnings["role_swaps"])
        }
    }

    # Log summary
    logger.info(f"Config validation complete: {report['summary']}")

    return report


def get_all_drone_positions(sim_mode=None):
    """
    Get initial positions for all drones from their trajectory CSV files.

    This is the SINGLE SOURCE OF TRUTH for drone positions. Positions are always
    read from the first row of each drone's trajectory CSV file based on pos_id.

    Args:
        sim_mode (bool): Whether in simulation mode (affects trajectory path)

    Returns:
        list: List of dictionaries with structure:
              [{"hw_id": int, "pos_id": int, "x": float, "y": float}, ...]
              Returns empty list on error.
    """
    from coordinate_utils import get_expected_position_from_trajectory

    # Detect sim_mode if not provided
    if sim_mode is None:
        sim_mode = getattr(Params, 'sim_mode', False)

    positions = []

    try:
        # Load current configuration
        config_data = load_config()

        for drone in config_data:
            try:
                hw_id = int(drone.get('hw_id'))
                pos_id = int(drone.get('pos_id', hw_id))  # Fallback to hw_id if no pos_id

                # Get position from trajectory CSV (single source of truth)
                x, y = get_expected_position_from_trajectory(pos_id, sim_mode)

                if x is not None and y is not None:
                    positions.append({
                        "hw_id": hw_id,
                        "pos_id": pos_id,
                        "x": x,
                        "y": y
                    })
                else:
                    logger.warning(f"Could not get position for hw_id={hw_id}, pos_id={pos_id}")

            except Exception as e:
                logger.error(f"Error getting position for drone {drone}: {e}")
                continue

        logger.info(f"Retrieved positions for {len(positions)} drones")
        return positions

    except Exception as e:
        logger.error(f"Error getting all drone positions: {e}")
        return []