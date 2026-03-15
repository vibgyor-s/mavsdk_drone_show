"""
Swarm Trajectory Utilities
Common utilities for swarm trajectory processing
"""

from pathlib import Path

from src.params import Params


def get_project_root(base_dir=None):
    """Return the repository root independent of the current working directory."""
    if base_dir is not None:
        return str(Path(base_dir).resolve())

    return str(Path(__file__).resolve().parents[1])


def get_swarm_trajectory_folders(sim_mode=None, base_dir=None):
    """Get swarm trajectory directories for the requested mode."""
    use_sim_mode = Params.sim_mode if sim_mode is None else sim_mode
    root_dir = get_project_root(base_dir=base_dir)
    base_folder = 'shapes_sitl' if use_sim_mode else 'shapes'
    base_path = Path(root_dir) / base_folder

    return {
        'base': str(base_path),
        'raw': str(base_path / 'swarm_trajectory' / 'raw'),
        'processed': str(base_path / 'swarm_trajectory' / 'processed'),
        'plots': str(base_path / 'swarm_trajectory' / 'plots'),
    }
