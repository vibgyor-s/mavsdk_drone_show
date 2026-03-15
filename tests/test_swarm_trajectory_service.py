"""
Swarm trajectory service tests.
"""

from pathlib import Path
from unittest.mock import patch

from functions.swarm_analyzer import fetch_swarm_data
from functions.swarm_trajectory_service import (
    SwarmTrajectoryError,
    clear_individual_drone_payload,
)
from functions.swarm_trajectory_utils import get_project_root, get_swarm_trajectory_folders


def test_get_swarm_trajectory_folders_is_cwd_independent(monkeypatch, tmp_path):
    """Trajectory paths should resolve from the repo root, not the caller cwd."""
    monkeypatch.chdir(tmp_path)

    folders = get_swarm_trajectory_folders()
    expected_root = Path(get_project_root())

    assert Path(folders['base']).is_absolute()
    assert Path(folders['base']).parent == expected_root


def test_fetch_swarm_data_prefers_local_config():
    """Swarm analysis should not need a self-HTTP call when config is local."""
    local_swarm = [{'hw_id': 1, 'follow': 0, 'offset_x': 0, 'offset_y': 0, 'offset_z': 0}]

    with patch('config.load_swarm', return_value=local_swarm):
        with patch('requests.get') as mock_get:
            result = fetch_swarm_data()

    assert result == local_swarm
    mock_get.assert_not_called()


def test_clear_individual_drone_rejects_cluster_leader():
    """Leaders must be cleared at cluster scope to avoid inconsistent outputs."""
    swarm_data = [
        {'hw_id': 1, 'follow': 0, 'offset_x': 0, 'offset_y': 0, 'offset_z': 0},
        {'hw_id': 2, 'follow': 1, 'offset_x': 1, 'offset_y': 0, 'offset_z': 0},
    ]

    with patch('functions.swarm_trajectory_service.fetch_swarm_data', return_value=swarm_data):
        try:
            clear_individual_drone_payload(1)
        except SwarmTrajectoryError as exc:
            assert exc.status_code == 400
            assert 'cluster clear action' in exc.message
        else:
            raise AssertionError('Expected leader clear to be rejected')
