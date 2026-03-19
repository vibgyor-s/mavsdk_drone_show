"""Integration test: full init -> log -> verify JSONL file."""
import json
import os
import pytest
from mds_logging.drone import init_drone_logging
from mds_logging import get_logger, reset


@pytest.fixture(autouse=True)
def clean_logging_state():
    """Reset mds_logging global state between tests."""
    reset()
    yield
    reset()


@pytest.fixture
def tmp_log_env(tmp_path):
    log_dir = str(tmp_path / "sessions")
    return log_dir


class TestEndToEnd:
    def test_drone_init_creates_session_and_logs(self, tmp_log_env):
        session_id = init_drone_logging(drone_id=5, log_dir=tmp_log_env)
        logger = get_logger("coordinator")
        logger.info("Armed successfully", extra={"mds_drone_id": 5, "mds_extra": {"mode": "OFFBOARD"}})

        # Verify JSONL file exists and contains valid entry
        session_file = os.path.join(tmp_log_env, f"{session_id}.jsonl")
        assert os.path.exists(session_file)

        with open(session_file) as f:
            lines = f.readlines()
            assert len(lines) >= 1
            entry = json.loads(lines[-1])
            assert entry["component"] == "coordinator"
            assert entry["source"] == "drone"
            assert entry["drone_id"] == 5
            assert entry["msg"] == "Armed successfully"
            assert entry["extra"]["mode"] == "OFFBOARD"
