"""Tests for mds_logging.handlers — session-aware file handler."""
import json
import logging
import os
import pytest
from mds_logging.handlers import SessionFileHandler
from mds_logging.formatter import JSONLFormatter


@pytest.fixture
def tmp_log_file(tmp_path):
    return str(tmp_path / "test_session.jsonl")


class TestSessionFileHandler:
    def test_writes_jsonl_lines(self, tmp_log_file):
        handler = SessionFileHandler(tmp_log_file, flush_every_line=True)
        handler.setFormatter(JSONLFormatter())
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="hello world", args=(), exc_info=None,
        )
        record.mds_component = "test"
        record.mds_source = "gcs"
        record.mds_drone_id = None
        record.mds_session_id = "s_test"
        record.mds_extra = None
        handler.emit(record)
        handler.close()

        with open(tmp_log_file) as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed["msg"] == "hello world"

    def test_flush_on_every_line(self, tmp_log_file):
        handler = SessionFileHandler(tmp_log_file, flush_every_line=True)
        handler.setFormatter(JSONLFormatter())
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="flush test", args=(), exc_info=None,
        )
        record.mds_component = "test"
        record.mds_source = "gcs"
        record.mds_drone_id = None
        record.mds_session_id = "s_test"
        record.mds_extra = None
        handler.emit(record)
        # File should be readable immediately (flushed)
        with open(tmp_log_file) as f:
            assert "flush test" in f.read()

    def test_handler_creates_parent_dirs(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "test.jsonl")
        handler = SessionFileHandler(deep_path)
        handler.close()
        assert os.path.exists(deep_path)
