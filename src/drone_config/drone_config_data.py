# src/drone_config/drone_config_data.py
"""
Drone Configuration Data
========================
Immutable dataclass holding static drone configuration.

This class stores configuration that is set once at initialization
and should not change during runtime. Use DroneState for mutable data.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class DroneConfigData:
    """
    Immutable drone configuration data.

    Contains static configuration loaded from config files that
    does not change during drone operation.

    Attributes:
        hw_id: Unique hardware identifier for this drone
        config: Full configuration dictionary from config.csv
        swarm: Swarm configuration dictionary from swarm.csv
        pos_id: Position ID for show choreography
        takeoff_altitude: Default takeoff altitude in meters
        all_configs: Dictionary of all drone positions {pos_id: {x, y}}
    """

    hw_id: str
    config: Dict[str, Any]
    swarm: Optional[Dict[str, Any]]
    pos_id: int
    takeoff_altitude: float
    all_configs: Dict[int, Dict[str, float]] = field(default_factory=dict)

    def get_serial_port(self) -> str:
        """
        Get the serial port configuration for this drone's hardware.

        Falls back to Params default if not specified in config.csv.

        Returns:
            Serial port device path (e.g., '/dev/ttyS0', '/dev/ttyAMA0')
        """
        from src.params import Params

        if self.config and 'serial_port' in self.config:
            serial_port = self.config['serial_port']
            # Handle SITL mode or empty values
            if serial_port and serial_port.upper() not in ['N/A', 'NONE', '']:
                return serial_port
        # Fallback to global Params default
        return Params.serial_mavlink_port

    def get_baudrate(self) -> int:
        """
        Get the baudrate configuration for this drone's hardware.

        Falls back to Params default if not specified in config.csv.

        Returns:
            Baudrate for serial connection (e.g., 57600, 115200, 921600)
        """
        import logging
        from src.params import Params

        if self.config and 'baudrate' in self.config:
            baudrate = self.config['baudrate']
            # Handle SITL mode or empty values
            if baudrate and str(baudrate).upper() not in ['N/A', 'NONE', '']:
                try:
                    return int(baudrate)
                except (ValueError, TypeError):
                    logging.warning(
                        f"Invalid baudrate '{baudrate}' in config, "
                        f"using default: {Params.serial_baudrate}"
                    )
        # Fallback to global Params default
        return Params.serial_baudrate
