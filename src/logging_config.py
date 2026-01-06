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
from logging.handlers import RotatingFileHandler
from pathlib import Path


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
