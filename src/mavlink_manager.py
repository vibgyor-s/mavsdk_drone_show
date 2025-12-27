"""
MAVLink Manager
===============
Manages the MAVLink router process for drone communication.

This module handles starting and stopping the mavlink-routerd process
which routes MAVLink messages between the flight controller, MAVSDK,
and the GCS.
"""

import subprocess
import logging

logger = logging.getLogger(__name__)


class MavlinkManager:
    """
    Manages the MAVLink router subprocess.

    The MavlinkManager is responsible for:
    - Starting mavlink-routerd with appropriate endpoints
    - Configuring routes for SITL vs real hardware
    - Terminating the router on shutdown

    Attributes:
        params: System parameters (Params instance)
        drone_config: Drone configuration (DroneConfig instance)
        mavlink_router_process: Subprocess handle for mavlink-routerd
    """

    def __init__(self, params, drone_config):
        """
        Initialize the MAVLink Manager.

        Args:
            params: Params instance with system configuration
            drone_config: DroneConfig instance with drone-specific settings
        """
        self.params = params
        self.drone_config = drone_config
        self.mavlink_router_process = None
        logger.info("Initialized MavlinkManager")

    def initialize(self):
        """
        Start the MAVLink router with configured endpoints.

        Configures mavlink-routerd based on operating mode:
        - SITL mode: Connects to simulator on configured port
        - Real mode (serial): Connects to Pixhawk via serial port
        - Real mode (UDP): Connects to Pixhawk via UDP

        Endpoints are added for MAVSDK and GCS communication.

        Raises:
            Exception: If router fails to start (logged, not raised)
        """
        try:
            if self.params.sim_mode:
                logging.info("Sim mode is enabled. Connecting to SITL...")
                if self.params.default_sitl:
                    mavlink_source = f"0.0.0.0:{self.params.sitl_port}"
                else:
                    mavlink_source = f"0.0.0.0:{self.drone_config.config['mavlink_port']}"
            else:
                if self.params.serial_mavlink:
                    logging.info("Real mode is enabled. Connecting to Pixhawk via serial...")
                    mavlink_source = f"{self.drone_config.get_serial_port()}:{self.drone_config.get_baudrate()}"
                else:
                    logging.info("Real mode is enabled. Connecting to Pixhawk via UDP...")
                    mavlink_source = f"127.0.0.1:{self.params.hw_udp_port}"

            logging.info(f"Using MAVLink source: {mavlink_source}")

            endpoints = [f"-e {device}" for device in self.params.extra_devices]

            if self.params.sim_mode:
                #already sends to 14550 and 14540
                pass
            else:
                endpoints.append(f"-e 127.0.0.1:{self.params.mavsdk_port}")

            if self.params.shared_gcs_port:
                endpoints.append(f"-e {self.params.GCS_IP}:{self.params.gcs_mavlink_port}")
            else:
                endpoints.append(f"-e {self.params.GCS_IP}:{int(self.drone_config.config['mavlink_port'])}")

            mavlink_router_cmd = "mavlink-routerd " + ' '.join(endpoints) + ' ' + mavlink_source
            logging.info(f"Starting MAVLink router with command: {mavlink_router_cmd}")

            self.mavlink_router_process = subprocess.Popen(mavlink_router_cmd, shell=True)
            logging.info("MAVLink router process started")
        except Exception as e:
            logging.error(f"An error occurred in initialize(): {e}")

    def terminate(self):
        """
        Terminate the MAVLink router process.

        Gracefully stops the mavlink-routerd subprocess if running.
        Safe to call even if the process is not running.
        """
        try:
            if self.mavlink_router_process:
                self.mavlink_router_process.terminate()
                logging.info("MAVLink router process terminated")
            else:
                logging.warning("MAVLink router process is not running")
        except Exception as e:
            logging.error(f"An error occurred in terminate(): {e}")
