"""
Unified LED Color Scheme for MAVSDK Drone Show
Enterprise-grade color definitions for thousands of drones.

Color Philosophy:
- BOOT phases: RED -> BLUE -> GREEN progression
- ERRORS: Always RED (fast blink for critical)
- WARNINGS: YELLOW/ORANGE
- SUCCESS: GREEN
- CONNECTIVITY: GREEN (ok) / PURPLE (offline)
- MISSION: CYAN (active) / WHITE (ready)

Boot Sequence Colors:
1. BOOT_STARTED (RED) - System powering up
2. NETWORK_INIT (BLUE pulse) - WiFi connecting
3. NETWORK_READY (BLUE solid) - Network established
4. GIT_SYNCING (CYAN pulse) - Git sync in progress
5. GIT_SUCCESS (GREEN flash) - Sync successful
6. GIT_FAILED_CONTINUING (YELLOW) - Failed, using cached code
7. STARTUP_COMPLETE (WHITE flash) - Ready for operation

Runtime Colors:
- IDLE_CONNECTED (GREEN) - GCS connected, ready
- IDLE_DISCONNECTED (PURPLE) - GCS offline, ready
- MISSION_ARMED (ORANGE) - Armed for mission
- MISSION_ACTIVE (CYAN pulse) - Mission executing
- ERROR (RED blink) - Error state
"""

from enum import Enum
from typing import Tuple, Optional


class LEDPattern:
    """LED display patterns."""
    SOLID = "solid"
    SLOW_PULSE = "slow_pulse"      # 1 Hz
    FAST_PULSE = "fast_pulse"      # 2 Hz
    SLOW_BLINK = "slow_blink"      # 0.5 Hz on/off
    FAST_BLINK = "fast_blink"      # 2 Hz on/off
    FLASH_1X = "flash_1x"          # Single flash
    FLASH_3X = "flash_3x"          # Triple flash


class LEDState(Enum):
    """
    LED states with RGB values, patterns, and descriptions.

    Each state is a tuple: (rgb_tuple, pattern, description)
    Access via properties: state.rgb, state.pattern, state.description
    """

    # ========== Boot Phase States (sequence: RED -> BLUE -> GREEN) ==========
    BOOT_STARTED = ((255, 0, 0), LEDPattern.SOLID, "System booting")
    NETWORK_INIT = ((0, 0, 255), LEDPattern.SLOW_PULSE, "WiFi connecting")
    NETWORK_READY = ((0, 0, 255), LEDPattern.SOLID, "Network established")
    GIT_SYNCING = ((0, 255, 255), LEDPattern.FAST_PULSE, "Git sync in progress")
    GIT_SUCCESS = ((0, 255, 0), LEDPattern.FLASH_3X, "Git sync successful")
    GIT_FAILED_CONTINUING = ((255, 255, 0), LEDPattern.SOLID, "Git failed, using cached")
    SERVICES_UPDATING = ((255, 165, 0), LEDPattern.SLOW_PULSE, "Updating services/requirements")
    STARTUP_COMPLETE = ((255, 255, 255), LEDPattern.FLASH_1X, "Startup complete")

    # ========== Runtime States ==========
    IDLE_CONNECTED = ((0, 255, 0), LEDPattern.SOLID, "Ready, GCS connected")
    IDLE_DISCONNECTED = ((128, 0, 128), LEDPattern.SOLID, "Ready, GCS offline")
    MISSION_ARMED = ((255, 165, 0), LEDPattern.SOLID, "Mission armed, awaiting start")
    MISSION_ACTIVE = ((0, 255, 255), LEDPattern.SLOW_PULSE, "Mission executing")
    MISSION_COMPLETE = ((0, 255, 0), LEDPattern.SLOW_PULSE, "Mission complete")
    MISSION_PAUSED = ((255, 255, 0), LEDPattern.SLOW_BLINK, "Mission paused")

    # ========== Error States ==========
    ERROR_RECOVERABLE = ((255, 0, 0), LEDPattern.SLOW_BLINK, "Error, will retry")
    ERROR_CRITICAL = ((255, 0, 0), LEDPattern.FAST_BLINK, "Critical error, needs attention")
    ERROR_HARDWARE = ((255, 0, 255), LEDPattern.FAST_BLINK, "Hardware failure")
    ERROR_COMMUNICATION = ((255, 100, 0), LEDPattern.FAST_BLINK, "Communication error")

    # ========== Special States ==========
    CALIBRATING = ((255, 255, 0), LEDPattern.SLOW_PULSE, "Calibrating sensors")
    FIRMWARE_UPDATE = ((0, 0, 255), LEDPattern.FAST_PULSE, "Firmware updating")
    MANUAL_OVERRIDE = ((255, 255, 255), LEDPattern.SOLID, "Manual control active")
    LOW_BATTERY = ((255, 100, 0), LEDPattern.SLOW_BLINK, "Low battery warning")
    LANDING = ((255, 255, 0), LEDPattern.FAST_PULSE, "Landing in progress")

    @property
    def rgb(self) -> Tuple[int, int, int]:
        """Get the RGB color tuple."""
        return self.value[0]

    @property
    def r(self) -> int:
        """Get red component."""
        return self.value[0][0]

    @property
    def g(self) -> int:
        """Get green component."""
        return self.value[0][1]

    @property
    def b(self) -> int:
        """Get blue component."""
        return self.value[0][2]

    @property
    def pattern(self) -> str:
        """Get the display pattern."""
        return self.value[1]

    @property
    def description(self) -> str:
        """Get the human-readable description."""
        return self.value[2]

    @classmethod
    def from_name(cls, name: str) -> Optional['LEDState']:
        """Get LEDState by name (case-insensitive)."""
        name_upper = name.upper().replace('-', '_').replace(' ', '_')
        try:
            return cls[name_upper]
        except KeyError:
            return None


class LEDColors:
    """
    Simple RGB tuple access for backward compatibility.

    Use this class when you just need the color values without
    pattern information. For full state management, use LEDState enum.

    Example:
        led_controller.set_color(*LEDColors.BOOT_STARTED)
        # or
        r, g, b = LEDColors.BOOT_STARTED
    """

    # Boot Phase
    BOOT_STARTED = (255, 0, 0)          # Red
    NETWORK_INIT = (0, 0, 255)          # Blue
    NETWORK_READY = (0, 0, 255)         # Blue
    GIT_SYNCING = (0, 255, 255)         # Cyan
    GIT_SUCCESS = (0, 255, 0)           # Green
    GIT_FAILED_CONTINUING = (255, 255, 0)  # Yellow (matches LEDState enum)
    GIT_FAILED = GIT_FAILED_CONTINUING  # Alias for backward compatibility
    SERVICES_UPDATING = (255, 165, 0)   # Orange
    STARTUP_COMPLETE = (255, 255, 255)  # White
    READY = (255, 255, 255)             # White (alias)

    # Runtime
    IDLE_CONNECTED = (0, 255, 0)        # Green
    IDLE_DISCONNECTED = (128, 0, 128)   # Purple
    MISSION_ARMED = (255, 165, 0)       # Orange
    MISSION_ACTIVE = (0, 255, 255)      # Cyan
    MISSION_COMPLETE = (0, 255, 0)      # Green
    MISSION_PAUSED = (255, 255, 0)      # Yellow

    # Errors
    ERROR = (255, 0, 0)                 # Red
    ERROR_CRITICAL = (255, 0, 0)        # Red
    ERROR_HARDWARE = (255, 0, 255)      # Magenta
    ERROR_COMMUNICATION = (255, 100, 0) # Orange-Red

    # Special
    CALIBRATING = (255, 255, 0)         # Yellow
    FIRMWARE_UPDATE = (0, 0, 255)       # Blue
    MANUAL_OVERRIDE = (255, 255, 255)   # White
    LOW_BATTERY = (255, 100, 0)         # Orange
    LANDING = (255, 255, 0)             # Yellow

    # Common aliases for legacy code
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 165, 0)
    PURPLE = (128, 0, 128)
    CYAN = (0, 255, 255)
    WHITE = (255, 255, 255)
    OFF = (0, 0, 0)


# Color name to RGB mapping for CLI tools
COLOR_NAME_MAP = {
    'red': LEDColors.RED,
    'green': LEDColors.GREEN,
    'blue': LEDColors.BLUE,
    'yellow': LEDColors.YELLOW,
    'orange': LEDColors.ORANGE,
    'purple': LEDColors.PURPLE,
    'cyan': LEDColors.CYAN,
    'white': LEDColors.WHITE,
    'off': LEDColors.OFF,
    # State names
    'boot': LEDColors.BOOT_STARTED,
    'network': LEDColors.NETWORK_INIT,
    'syncing': LEDColors.GIT_SYNCING,
    'success': LEDColors.GIT_SUCCESS,
    'failed': LEDColors.GIT_FAILED,
    'ready': LEDColors.READY,
    'connected': LEDColors.IDLE_CONNECTED,
    'disconnected': LEDColors.IDLE_DISCONNECTED,
    'armed': LEDColors.MISSION_ARMED,
    'active': LEDColors.MISSION_ACTIVE,
    'error': LEDColors.ERROR,
}


def get_color_by_name(name: str) -> Tuple[int, int, int]:
    """
    Get RGB tuple by color name (case-insensitive).

    Args:
        name: Color name ('red', 'green', 'boot', 'error', etc.)

    Returns:
        RGB tuple (r, g, b)

    Raises:
        ValueError: If color name not recognized
    """
    name_lower = name.lower().strip()
    if name_lower in COLOR_NAME_MAP:
        return COLOR_NAME_MAP[name_lower]

    # Try LEDState lookup
    state = LEDState.from_name(name)
    if state:
        return state.rgb

    raise ValueError(f"Unknown color name: {name}")


def get_state_by_name(name: str) -> Optional[LEDState]:
    """
    Get LEDState by name (case-insensitive, flexible matching).

    Args:
        name: State name like 'BOOT_STARTED', 'boot-started', 'boot started'

    Returns:
        LEDState or None if not found
    """
    return LEDState.from_name(name)
