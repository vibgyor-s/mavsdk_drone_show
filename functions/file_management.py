#functions/file_management.py
import os
import shutil

from mds_logging import get_logger

logger = get_logger("file_management")


def setup_logging():
    """
    Backward-compatible no-op logging initializer.

    Legacy callers and tests still import setup_logging() from this module.
    Logging is now configured centrally through mds_logging, so this shim
    simply returns the module logger without reconfiguring global handlers.
    """
    return logger

def ensure_directory_exists(directory):
    """Ensure directory exists or create it if not."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"Created directory: {directory}")

def clear_directory(directory):
    """Clear all files in a directory."""
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
                logger.info(f"Deleted file: {file_path}")
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                logger.info(f"Deleted directory: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")

def copy_files(source_dir, dest_dir):
    """Copy all files from source to destination directory."""
    for filename in os.listdir(source_dir):
        src_file = os.path.join(source_dir, filename)
        dst_file = os.path.join(dest_dir, filename)
        if os.path.isfile(src_file):
            shutil.copy(src_file, dst_file)
            logger.info(f"Copied {src_file} to {dst_file}")
