#!/usr/bin/env python3
"""
LED Strip Controller for Drone Show using Raspberry Pi

This script initializes an LED strip and sets all LEDs to a specified color
or state. It is used as a visual indicator during the system startup workflow.

Boot Sequence Color Coding:
    - RED: Boot has started
    - BLUE (pulse): Network initialization / Git sync in progress
    - CYAN (pulse): Git syncing
    - GREEN (flash): Git sync successful
    - YELLOW: Git sync failed, continuing with cached code
    - WHITE (flash): Startup complete

Runtime Color Coding:
    - GREEN: Ready, GCS connected
    - PURPLE: Ready, GCS offline
    - ORANGE: Mission armed
    - CYAN (pulse): Mission active
    - RED (blink): Error state

Usage examples:
    # Set LEDs to the default state (BOOT_STARTED = red):
    python led_indicator.py

    # Set LEDs by color name:
    python led_indicator.py --color blue

    # Set LEDs by state name (preferred):
    python led_indicator.py --state BOOT_STARTED
    python led_indicator.py --state GIT_SYNCING
    python led_indicator.py --state IDLE_CONNECTED

Author: Alireza Ghaderi
Updated: 2025 - Added unified LED color system support
"""

import sys
import argparse

from mds_logging import get_logger

logger = get_logger("led_indicator")

# Try to import LED library (may not be available on non-Pi systems)
try:
    from rpi_ws281x import PixelStrip, Color
    LED_AVAILABLE = True
except ImportError:
    LED_AVAILABLE = False
    print("[LED] Warning: rpi_ws281x not available, running in dry-run mode")

# Import unified color definitions
try:
    from src.led_colors import LEDColors, LEDState, get_color_by_name, COLOR_NAME_MAP
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    print("[LED] Warning: src.led_colors not available, using built-in colors")

# LED strip configuration constants
LED_PIN = 10          # GPIO pin connected to the LED strip
LED_COUNT = 25        # Number of LEDs in the strip
LED_FREQ_HZ = 800000  # LED signal frequency in Hz
LED_DMA = 10          # DMA channel
LED_BRIGHTNESS = 255  # Brightness level (0-255)
LED_INVERT = False    # Invert signal (True or False)
LED_CHANNEL = 0       # PWM channel

# Fallback color definitions (used if src.led_colors not available)
PREDEFINED_COLORS = {
    'red': (255, 0, 0),
    'blue': (0, 0, 255),
    'green': (0, 255, 0),
    'yellow': (255, 255, 0),
    'purple': (128, 0, 128),
    'orange': (255, 165, 0),
    'white': (255, 255, 255),
    'cyan': (0, 255, 255),
    'off': (0, 0, 0),
}

def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Contains 'color' and/or 'state' arguments.
    """
    parser = argparse.ArgumentParser(
        description="Control LED strip color for visual status indication.",
        epilog="Use --state for semantic states (preferred) or --color for direct colors."
    )
    parser.add_argument(
        '--color',
        type=str,
        default=None,
        help="Color name to set. Supported: " + ", ".join(PREDEFINED_COLORS.keys())
    )
    parser.add_argument(
        '--state',
        type=str,
        default=None,
        help="LED state to set (preferred). Examples: BOOT_STARTED, GIT_SYNCING, "
             "IDLE_CONNECTED, ERROR_CRITICAL. See src/led_colors.py for full list."
    )
    parser.add_argument(
        '--list-states',
        action='store_true',
        help="List all available LED states and exit."
    )
    return parser.parse_args()

def get_rgb_from_name(name: str) -> tuple:
    """
    Gets RGB tuple from a color or state name.

    Args:
        name: Color name ('red', 'blue') or state name ('BOOT_STARTED', 'GIT_SYNCING')

    Returns:
        tuple: (r, g, b) color values

    Raises:
        ValueError: If the name is not recognized
    """
    name_lower = name.lower().strip()

    # First try unified color system if available
    if COLORS_AVAILABLE:
        try:
            return get_color_by_name(name)
        except ValueError:
            pass

    # Fall back to predefined colors
    if name_lower in PREDEFINED_COLORS:
        return PREDEFINED_COLORS[name_lower]

    raise ValueError(
        f"Color/state '{name}' is not supported. "
        f"Supported colors: {', '.join(PREDEFINED_COLORS.keys())}"
    )


def get_color(color_name: str):
    """
    Converts a color name to a Color object (for rpi_ws281x).

    Args:
        color_name (str): Name of the color (e.g., 'red', 'blue').

    Returns:
        Color object or tuple: LED color representation.
    """
    r, g, b = get_rgb_from_name(color_name)
    if LED_AVAILABLE:
        return Color(r, g, b)
    return (r, g, b)

def initialize_strip() -> PixelStrip:
    """
    Initializes and returns the LED strip object.

    Returns:
        PixelStrip: An initialized LED strip.
    """
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        freq_hz=LED_FREQ_HZ,
        dma=LED_DMA,
        invert=LED_INVERT,
        brightness=LED_BRIGHTNESS,
        channel=LED_CHANNEL
    )
    strip.begin()
    return strip

def set_strip_color(strip: PixelStrip, color: Color):
    """
    Sets all LEDs on the strip to the specified color.

    Args:
        strip (PixelStrip): The LED strip object.
        color (Color): The color to set on all LEDs.
    """
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def list_available_states():
    """Prints all available LED states with their colors and descriptions."""
    print("\nAvailable LED States:")
    print("=" * 70)

    if COLORS_AVAILABLE:
        print(f"{'State Name':<25} {'RGB':<18} {'Description'}")
        print("-" * 70)
        for state in LEDState:
            r, g, b = state.rgb
            print(f"{state.name:<25} ({r:3}, {g:3}, {b:3})    {state.description}")
    else:
        print("(Unified color system not available, showing built-in colors)")
        for name, (r, g, b) in PREDEFINED_COLORS.items():
            print(f"{name:<25} ({r:3}, {g:3}, {b:3})")

    print("=" * 70)


def main():
    """
    Main function to parse arguments, initialize the LED strip, and set its color.
    Supports both --color (direct color) and --state (semantic state) arguments.
    """
    # Logging already configured via mds_logging

    # Parse command-line arguments
    args = parse_arguments()

    # Handle --list-states
    if args.list_states:
        list_available_states()
        sys.exit(0)

    # Determine color to set
    color_name = None
    meaning = "No defined meaning."

    if args.state:
        # --state takes priority
        color_name = args.state
        if COLORS_AVAILABLE:
            state = LEDState.from_name(args.state)
            if state:
                meaning = state.description
            else:
                meaning = f"State '{args.state}'"
        else:
            meaning = f"State '{args.state}'"
    elif args.color:
        color_name = args.color
        # Get meaning from LEDState if available
        if COLORS_AVAILABLE:
            state = LEDState.from_name(args.color)
            if state:
                meaning = state.description
            else:
                meaning = f"Color '{args.color}'"
        else:
            meaning = f"Color '{args.color}'"
    else:
        # Default to BOOT_STARTED (red)
        color_name = 'BOOT_STARTED' if COLORS_AVAILABLE else 'red'
        meaning = "Boot has started"

    try:
        # Get the RGB color
        r, g, b = get_rgb_from_name(color_name)
    except ValueError as error:
        logger.error(error)
        sys.exit(1)

    logger.info(f"Setting LED: {color_name} ({r}, {g}, {b}) - {meaning}")

    # Set the LEDs
    if not LED_AVAILABLE:
        logger.info(f"[DRY-RUN] Would set LEDs to RGB({r}, {g}, {b})")
        sys.exit(0)

    try:
        # Initialize the LED strip
        strip = initialize_strip()
        # Set all LEDs to the specified color
        led_color = Color(r, g, b)
        set_strip_color(strip, led_color)
        logger.info(f"LEDs successfully set to {color_name}.")
    except Exception as e:
        logger.error(f"Error initializing or controlling LEDs: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
