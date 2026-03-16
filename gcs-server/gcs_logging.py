"""Stable access wrapper for the GCS logging implementation.

The project also has ``src/logging_config.py`` for drone-side/runtime logging.
Under the GCS startup path, ``logging_config`` can resolve to the wrong module
depending on ``PYTHONPATH`` ordering. This wrapper loads the GCS-local logging
implementation by file path so GCS modules always get the correct API.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_IMPL_PATH = Path(__file__).with_name("logging_config.py")
_SPEC = spec_from_file_location("_gcs_logging_impl", _IMPL_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load GCS logging implementation from {_IMPL_PATH}")

_IMPL = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_IMPL)

DroneSwarmLogger = _IMPL.DroneSwarmLogger
LogLevel = _IMPL.LogLevel
DisplayMode = _IMPL.DisplayMode


def initialize_logging(*args, **kwargs):
    return _IMPL.initialize_logging(*args, **kwargs)


def get_logger(*args, **kwargs):
    return _IMPL.get_logger(*args, **kwargs)


def log_drone_telemetry(*args, **kwargs):
    return _IMPL.log_drone_telemetry(*args, **kwargs)


def log_drone_command(*args, **kwargs):
    return _IMPL.log_drone_command(*args, **kwargs)


def log_system_startup(*args, **kwargs):
    return _IMPL.log_system_startup(*args, **kwargs)


def log_system_error(*args, **kwargs):
    return _IMPL.log_system_error(*args, **kwargs)


def log_system_warning(*args, **kwargs):
    return _IMPL.log_system_warning(*args, **kwargs)


def log_system_event(*args, **kwargs):
    return _IMPL.log_system_event(*args, **kwargs)
