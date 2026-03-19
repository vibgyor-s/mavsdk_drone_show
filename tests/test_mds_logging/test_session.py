"""Tests for mds_logging.session — session lifecycle management."""
import os
import time
import pytest
from mds_logging.session import (
    create_session, get_session_id, get_session_filepath,
    list_sessions, cleanup_sessions,
)


@pytest.fixture
def tmp_log_dir(tmp_path):
    log_dir = tmp_path / "sessions"
    log_dir.mkdir()
    return str(log_dir)


class TestCreateSession:
    def test_returns_session_id_with_correct_format(self, tmp_log_dir):
        sid = create_session(tmp_log_dir)
        assert sid.startswith("s_")
        assert len(sid) == 17  # s_YYYYMMDD_HHMMSS = 2+8+1+6

    def test_creates_jsonl_file(self, tmp_log_dir):
        sid = create_session(tmp_log_dir)
        filepath = os.path.join(tmp_log_dir, f"{sid}.jsonl")
        assert os.path.exists(filepath)

    def test_duplicate_second_gets_suffix(self, tmp_log_dir):
        sid1 = create_session(tmp_log_dir)
        # Create a file with the same name to force collision
        sid2_expected = sid1 + "_2"
        sid2 = create_session(tmp_log_dir)
        assert sid2 == sid2_expected


class TestListSessions:
    def test_lists_sessions_newest_first(self, tmp_log_dir):
        # Create two session files with different timestamps
        open(os.path.join(tmp_log_dir, "s_20260318_100000.jsonl"), "w").close()
        time.sleep(0.01)
        open(os.path.join(tmp_log_dir, "s_20260319_100000.jsonl"), "w").close()
        sessions = list_sessions(tmp_log_dir)
        assert len(sessions) == 2
        assert sessions[0]["session_id"] == "s_20260319_100000"

    def test_empty_dir_returns_empty_list(self, tmp_log_dir):
        assert list_sessions(tmp_log_dir) == []


class TestCleanupSessions:
    def test_cleanup_by_count(self, tmp_log_dir):
        # Create 12 session files
        for i in range(12):
            fname = f"s_20260301_{i:06d}.jsonl"
            with open(os.path.join(tmp_log_dir, fname), "w") as f:
                f.write('{"test": true}\n')
        cleanup_sessions(tmp_log_dir, max_sessions=10, max_size_mb=1000)
        remaining = os.listdir(tmp_log_dir)
        assert len(remaining) == 10

    def test_cleanup_by_size(self, tmp_log_dir):
        # Create files that exceed size limit
        for i in range(5):
            fname = f"s_20260301_{i:06d}.jsonl"
            with open(os.path.join(tmp_log_dir, fname), "w") as f:
                f.write("x" * (1024 * 1024))  # 1MB each = 5MB total
        # Limit to 3MB — should remove oldest 2
        cleanup_sessions(tmp_log_dir, max_sessions=100, max_size_mb=3)
        remaining = os.listdir(tmp_log_dir)
        assert len(remaining) == 3

    def test_keeps_newest_files(self, tmp_log_dir):
        for i in range(5):
            fname = f"s_20260301_{i:06d}.jsonl"
            with open(os.path.join(tmp_log_dir, fname), "w") as f:
                f.write("data\n")
        cleanup_sessions(tmp_log_dir, max_sessions=3, max_size_mb=1000)
        remaining = sorted(os.listdir(tmp_log_dir))
        assert remaining[0] == "s_20260301_000002.jsonl"  # oldest surviving
