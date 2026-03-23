from src.swarm_runtime_state import read_runtime_swarm_assignment, write_runtime_swarm_assignment


def test_runtime_swarm_assignment_round_trip(monkeypatch, tmp_path):
    path = tmp_path / "smart_swarm_assignment.json"
    monkeypatch.setenv("MDS_SWARM_RUNTIME_ASSIGNMENT_PATH", str(path))

    assignment = {
        "hw_id": 3,
        "follow": 2,
        "offset_x": 8.0,
        "offset_y": 6.0,
        "offset_z": 0.0,
        "frame": "body",
    }

    write_runtime_swarm_assignment(assignment)

    assert read_runtime_swarm_assignment() == assignment


def test_runtime_swarm_assignment_empty_payload_returns_none(monkeypatch, tmp_path):
    path = tmp_path / "smart_swarm_assignment.json"
    monkeypatch.setenv("MDS_SWARM_RUNTIME_ASSIGNMENT_PATH", str(path))

    write_runtime_swarm_assignment(None)

    assert read_runtime_swarm_assignment() is None
