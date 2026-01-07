"""
Unified logging configuration for MDS (MAVSDK Drone Show) components.

Provides standardized logging setup across all Python components with:
- Consistent log format
- Rotating file handlers with configurable retention
- Console and file output
- Environment variable configuration

Usage:
    from src.logging_config import setup_logging
    logger = setup_logging('coordinator')  # or 'git_sync', 'wifi_manager', etc.
    logger.info("Component started")

Environment Variables:
    MDS_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    MDS_LOG_MAX_SIZE_MB: Max log file size in MB before rotation
    MDS_LOG_BACKUP_COUNT: Number of backup files to keep
"""

import logging
import os
import sys
from enum import Enum
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# ============================================================================
# Enums for GCS Server Compatibility
# ============================================================================

class LogLevel(Enum):
    """Log verbosity levels for GCS server."""
    QUIET = 'QUIET'      # Minimal output
    NORMAL = 'NORMAL'    # Standard output
    VERBOSE = 'VERBOSE'  # Detailed output
    DEBUG = 'DEBUG'      # Full debug output


class DisplayMode(Enum):
    """Display modes for GCS server output."""
    DASHBOARD = 'DASHBOARD'  # Compact dashboard view
    STREAM = 'STREAM'        # Streaming log output
    HYBRID = 'HYBRID'        # Combined view


# Default configuration
DEFAULT_LOG_LEVEL = 'INFO'
DEFAULT_MAX_SIZE_MB = 50
DEFAULT_BACKUP_COUNT = 10
DEFAULT_LOG_DIR = 'logs'

# Log format
LOG_FORMAT = '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Console format (shorter for readability)
CONSOLE_FORMAT = '%(levelname)s: %(message)s'


def get_log_config():
    """
    Get logging configuration from environment variables.

    Returns:
        dict: Configuration with level, max_size_bytes, and backup_count
    """
    level_str = os.environ.get('MDS_LOG_LEVEL', DEFAULT_LOG_LEVEL).upper()
    max_size_mb = int(os.environ.get('MDS_LOG_MAX_SIZE_MB', DEFAULT_MAX_SIZE_MB))
    backup_count = int(os.environ.get('MDS_LOG_BACKUP_COUNT', DEFAULT_BACKUP_COUNT))

    # Validate log level
    valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
    if level_str not in valid_levels:
        level_str = DEFAULT_LOG_LEVEL

    return {
        'level': getattr(logging, level_str),
        'level_name': level_str,
        'max_size_bytes': max_size_mb * 1024 * 1024,
        'backup_count': backup_count,
    }


def setup_logging(
    component_name: str,
    log_dir: str = None,
    console_output: bool = True,
    file_output: bool = True
) -> logging.Logger:
    """
    Configure logging for an MDS component with enterprise-grade settings.

    Creates a logger with:
    - Rotating file handler (prevents disk fill)
    - Console handler (for systemd journal capture)
    - Consistent formatting across all components
    - Environment-configurable log levels and retention

    Args:
        component_name: Identifier for this component (e.g., 'coordinator', 'git_sync')
        log_dir: Directory for log files. Defaults to 'logs' in current directory.
        console_output: Whether to output to console (stdout)
        file_output: Whether to write to rotating log files

    Returns:
        logging.Logger: Configured logger instance

    Example:
        logger = setup_logging('coordinator')
        logger.info("Coordinator starting")
        logger.error("Something went wrong", exc_info=True)
    """
    config = get_log_config()

    # Determine log directory
    if log_dir is None:
        # Try to use repo root, fall back to current directory
        repo_root = Path(__file__).parent.parent
        log_dir = repo_root / DEFAULT_LOG_DIR
    else:
        log_dir = Path(log_dir)

    # Create log directory if needed
    log_dir.mkdir(parents=True, exist_ok=True)

    # Get or create logger
    logger = logging.getLogger(component_name)

    # Avoid duplicate handlers if setup_logging called multiple times
    if logger.handlers:
        return logger

    logger.setLevel(config['level'])
    logger.propagate = False  # Prevent duplicate logs to root logger

    # File handler with rotation
    if file_output:
        log_file = log_dir / f'{component_name}.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=config['max_size_bytes'],
            backupCount=config['backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # File gets everything
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(file_handler)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(config['level'])
        console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
        logger.addHandler(console_handler)

    return logger


def get_logger(component_name: str) -> logging.Logger:
    """
    Get an existing logger by name, or create a basic one if not configured.

    Use setup_logging() for initial configuration. Use get_logger() in
    submodules that need access to an already-configured logger.

    Args:
        component_name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(component_name)


# ============================================================================
# GCS Server Logging Helpers
# ============================================================================
# These functions provide structured logging for drone telemetry and system events

# Logger instance for GCS components (lazy initialization)
_gcs_logger = None


def _get_gcs_logger() -> logging.Logger:
    """Get or create the GCS logger instance."""
    global _gcs_logger
    if _gcs_logger is None:
        _gcs_logger = get_logger('gcs')
        # If not configured, set up basic logging
        if not _gcs_logger.handlers:
            _gcs_logger = setup_logging('gcs')
    return _gcs_logger


def log_drone_telemetry(drone_id: int, success: bool, data: dict = None) -> None:
    """
    Log drone telemetry events with structured data.

    Args:
        drone_id: Hardware ID of the drone
        success: Whether telemetry fetch was successful
        data: Optional dict with telemetry details (position, battery, etc.)
    """
    logger = _get_gcs_logger()
    if data is None:
        data = {}

    if success:
        msg = data.get('message', 'Telemetry received')
        details = []
        if 'position' in data:
            pos = data['position']
            details.append(f"pos=({pos[0]:.6f},{pos[1]:.6f},{pos[2]:.1f})")
        if 'battery' in data:
            details.append(f"bat={data['battery']:.2f}V")
        if 'mission' in data:
            details.append(f"mission={data['mission']}")
        if 'status' in data:
            details.append(f"status={data['status']}")

        detail_str = ' '.join(details) if details else ''
        logger.debug(f"[Drone {drone_id}] {msg} {detail_str}".strip())
    else:
        error_msg = data.get('error', 'Telemetry fetch failed')
        logger.warning(f"[Drone {drone_id}] {error_msg}")


def log_system_error(message: str, component: str = 'system') -> None:
    """
    Log system-level errors.

    Args:
        message: Error message
        component: Component name for context
    """
    logger = _get_gcs_logger()
    logger.error(f"[{component}] {message}")


def log_system_warning(message: str, component: str = 'system') -> None:
    """
    Log system-level warnings.

    Args:
        message: Warning message
        component: Component name for context
    """
    logger = _get_gcs_logger()
    logger.warning(f"[{component}] {message}")


def log_drone_command(drone_id: int, command: str, success: bool, details: str = '') -> None:
    """
    Log drone command events.

    Args:
        drone_id: Hardware ID of the drone
        command: Command name/type
        success: Whether command was successful
        details: Optional details about the result
    """
    logger = _get_gcs_logger()
    status = "OK" if success else "FAILED"
    msg = f"[Drone {drone_id}] CMD {command}: {status}"
    if details:
        msg += f" - {details}"
    if success:
        logger.info(msg)
    else:
        logger.warning(msg)


def log_system_event(message: str, level: str = 'INFO', component: str = 'system') -> None:
    """
    Log general system events.

    Args:
        message: Event message
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        component: Component name for context
    """
    logger = _get_gcs_logger()
    log_msg = f"[{component}] {message}"
    level_upper = level.upper()
    if level_upper == 'DEBUG':
        logger.debug(log_msg)
    elif level_upper == 'WARNING':
        logger.warning(log_msg)
    elif level_upper == 'ERROR':
        logger.error(log_msg)
    else:
        logger.info(log_msg)


def log_system_startup(component: str, version: str = '', details: str = '') -> None:
    """
    Log system startup events.

    Args:
        component: Component name
        version: Optional version string
        details: Optional startup details
    """
    logger = _get_gcs_logger()
    msg = f"[{component}] Starting"
    if version:
        msg += f" v{version}"
    if details:
        msg += f" - {details}"
    logger.info(msg)


def initialize_logging(
    log_level: LogLevel = LogLevel.NORMAL,
    display_mode: DisplayMode = DisplayMode.STREAM,
    component: str = 'gcs'
) -> logging.Logger:
    """
    Initialize the GCS logging system.

    Args:
        log_level: Verbosity level
        display_mode: Output display mode
        component: Component name

    Returns:
        Configured logger instance
    """
    # Map LogLevel to Python logging level
    level_map = {
        LogLevel.QUIET: logging.WARNING,
        LogLevel.NORMAL: logging.INFO,
        LogLevel.VERBOSE: logging.DEBUG,
        LogLevel.DEBUG: logging.DEBUG,
    }
    python_level = level_map.get(log_level, logging.INFO)

    # Set environment for other modules
    os.environ['MDS_LOG_LEVEL'] = logging.getLevelName(python_level)

    # Setup the logger
    logger = setup_logging(component)
    logger.setLevel(python_level)

    # Update handlers
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(python_level)

    return logger


def configure_from_environment() -> tuple:
    """
    Configure logging from environment variables.

    Returns:
        Tuple of (LogLevel, DisplayMode)
    """
    # Get log level from environment
    level_str = os.environ.get('MDS_LOG_LEVEL', 'INFO').upper()
    level_map = {
        'DEBUG': LogLevel.DEBUG,
        'INFO': LogLevel.NORMAL,
        'WARNING': LogLevel.QUIET,
        'ERROR': LogLevel.QUIET,
        'VERBOSE': LogLevel.VERBOSE,
        'NORMAL': LogLevel.NORMAL,
        'QUIET': LogLevel.QUIET,
    }
    log_level = level_map.get(level_str, LogLevel.NORMAL)

    # Get display mode from environment
    display_str = os.environ.get('MDS_DISPLAY_MODE', 'STREAM').upper()
    display_map = {
        'DASHBOARD': DisplayMode.DASHBOARD,
        'STREAM': DisplayMode.STREAM,
        'HYBRID': DisplayMode.HYBRID,
    }
    display_mode = display_map.get(display_str, DisplayMode.STREAM)

    return log_level, display_mode


# ============================================================================
# Script Utilities
# ============================================================================

# Convenience function for scripts
def configure_script_logging(script_name: str) -> logging.Logger:
    """
    Quick logging setup for standalone scripts.

    Simplified version for tools and utilities that don't need
    full enterprise configuration.

    Args:
        script_name: Name of the script

    Returns:
        logging.Logger: Configured logger
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(script_name)
