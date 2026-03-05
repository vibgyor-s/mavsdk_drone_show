# src/drone_config/config_loader.py
"""
Configuration Loader
====================
Static utilities for loading drone configuration from files and network.

This module provides stateless methods for:
- Reading hardware ID from .hwID files
- Loading config.csv and swarm.csv files
- Fetching online configurations
- Loading trajectory-based drone positions
"""

import csv
import glob
import logging
import os
from typing import Dict, Optional, Any

import requests

from src.params import Params

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Static utilities for loading drone configuration data.

    TODO(deferred): Move from CSV to JSON/YAML configuration.
    CSV is fragile (column order dependent, no nesting, no schema validation).
    See docs/TODO_deferred.md #3

    TODO(deferred): Central config service (pull-based).
    Drones pull config from GCS API on boot instead of reading local CSV.
    See docs/TODO_deferred.md #4

    All methods are class methods that don't require instance state,
    making them easy to test and use independently.
    """

    @staticmethod
    def get_hw_id(hw_id: Optional[int] = None) -> Optional[int]:
        """
        Retrieve the hardware ID from provided value or .hwID file.

        Args:
            hw_id: Optional hardware ID (int). If provided, returned as-is.

        Returns:
            Hardware ID as int, or None if not found.
        """
        if hw_id is not None:
            try:
                return int(hw_id)
            except (ValueError, TypeError):
                logger.error(f"Provided hw_id is not a valid integer: {hw_id}")
                return None

        hw_id_files = glob.glob("*.hwID")
        if hw_id_files:
            hw_id_file = hw_id_files[0]
            logger.info(f"Hardware ID file found: {hw_id_file}")
            try:
                hw_id = int(hw_id_file.split(".")[0])
            except ValueError:
                logger.error(f"Hardware ID filename is not a valid integer: {hw_id_file}")
                return None
            logger.info(f"Hardware ID: {hw_id}")
            return hw_id
        else:
            logger.error("Hardware ID file not found. Please check your files.")
            return None

    @staticmethod
    def read_file(filename: str, source: str, hw_id: int) -> Optional[Dict[str, Any]]:
        """
        Read a CSV configuration file and return config for given hardware ID.

        Args:
            filename: Path to CSV file
            source: Description of file source (for logging)
            hw_id: Hardware ID (int) to find in CSV

        Returns:
            Dictionary with configuration data, or None if not found.
        """
        try:
            with open(filename, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row['hw_id'] == str(hw_id):
                        logger.info(f"Configuration for HW_ID {hw_id} found in {source}.")
                        return dict(row)
        except FileNotFoundError:
            logger.error(f"File not found: {filename}")
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
        return None

    @staticmethod
    def fetch_online_config(url: str, local_filename: str, hw_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch configuration from online source and save locally.

        Args:
            url: URL to fetch configuration from
            local_filename: Local file path to save fetched config
            hw_id: Hardware ID (int) to find in fetched config

        Returns:
            Dictionary with configuration data, or None if fetch failed.
        """
        logger.info(f"Loading configuration from {url}...")
        try:
            response = requests.get(url)

            if response.status_code != 200:
                logger.error(f'Error downloading file: {response.status_code} {response.reason}')
                return None

            with open(local_filename, 'w') as f:
                f.write(response.text)

            return ConfigLoader.read_file(local_filename, 'online CSV file', hw_id)

        except Exception as e:
            logger.error(f"Failed to load online configuration: {e}")
            return None

    @staticmethod
    def read_config(hw_id: int) -> Optional[Dict[str, Any]]:
        """
        Read configuration from local CSV file or online source.

        Uses Params.offline_config to determine source.

        Args:
            hw_id: Hardware ID (int) to load config for

        Returns:
            Dictionary with configuration data, or None if not found.
        """
        if Params.offline_config:
            return ConfigLoader.read_file(Params.config_csv_name, 'local CSV file', hw_id)
        else:
            return ConfigLoader.fetch_online_config(Params.config_url, 'online_config.csv', hw_id)

    @staticmethod
    def read_swarm(hw_id: int) -> Optional[Dict[str, Any]]:
        """
        Read swarm configuration from local CSV file or online source.

        Uses Params.offline_swarm to determine source.

        Args:
            hw_id: Hardware ID (int) to load swarm config for

        Returns:
            Dictionary with swarm configuration data, or None if not found.
        """
        if Params.offline_swarm:
            return ConfigLoader.read_file(Params.swarm_csv_name, 'local CSV file', hw_id)
        else:
            return ConfigLoader.fetch_online_config(Params.swarm_url, 'online_swarm.csv', hw_id)

    @staticmethod
    def load_all_configs() -> Dict[int, Dict[str, float]]:
        """
        Load all drone configurations from config.csv and trajectory files.

        Reads pos_ids from config.csv, then loads x,y positions from
        corresponding trajectory CSV files (single source of truth).

        Returns:
            Dictionary mapping pos_id to {x, y} position data.
        """
        all_configs: Dict[int, Dict[str, float]] = {}
        try:
            # Read config.csv to get all pos_ids
            with open(Params.config_csv_name, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    pos_id = int(row['pos_id'])

                    # Get position from trajectory CSV (single source of truth)
                    base_dir = 'shapes_sitl' if Params.sim_mode else 'shapes'

                    # Navigate from src/drone_config/ to project root
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                    trajectory_file = os.path.join(
                        project_root,
                        base_dir,
                        'swarm',
                        'processed',
                        f"Drone {pos_id}.csv"
                    )

                    try:
                        if os.path.exists(trajectory_file):
                            with open(trajectory_file, 'r') as traj_f:
                                traj_reader = csv.DictReader(traj_f)
                                first_waypoint = next(traj_reader, None)
                                if first_waypoint:
                                    x = float(first_waypoint.get('px', 0))  # North
                                    y = float(first_waypoint.get('py', 0))  # East
                                    all_configs[pos_id] = {'x': x, 'y': y}
                                else:
                                    logger.warning(f"Trajectory file empty for pos_id={pos_id}")
                                    all_configs[pos_id] = {'x': 0, 'y': 0}
                        else:
                            logger.warning(f"Trajectory file not found for pos_id={pos_id}: {trajectory_file}")
                            all_configs[pos_id] = {'x': 0, 'y': 0}
                    except Exception as e:
                        logger.error(f"Error reading trajectory for pos_id={pos_id}: {e}")
                        all_configs[pos_id] = {'x': 0, 'y': 0}

            logger.info("All drone configurations loaded successfully from trajectory CSV files.")
        except FileNotFoundError:
            logger.error(f"Config file {Params.config_csv_name} not found.")
        except Exception as e:
            logger.error(f"Error loading all drone configurations: {e}")
        return all_configs
