"""Tests for mds_logging.formatter — JSONL and console formatters."""
import json
import logging
import pytest
from mds_logging.formatter import JSONLFormatter, ConsoleFormatter
from mds_logging import reset, set_drone_id, set_session, set_source


@pytest.fixture(autouse=True)
def clean_logging_context():
    reset()
    yield
    reset()


class TestJSONLFormatter:
    def _make_record(self, msg="test message", level=logging.INFO):
        record = logging.LogRecord(
            name="test.component", level=level, pathname="",
            lineno=0, msg=msg, args=(), exc_info=None,
        )
        record.mds_component = "coordinator"
        record.mds_source = "drone"
        record.mds_drone_id = 3
        record.mds_session_id = "s_20260319_140000"
        record.mds_extra = {"key": "value"}
        return record

    def test_output_is_valid_jsonl(self):
        fmt = JSONLFormatter()
        record = self._make_record()
        line = fmt.format(record)
        parsed = json.loads(line)
        assert parsed["msg"] == "test message"
        assert parsed["component"] == "coordinator"

    def test_output_ends_without_newline(self):
        """Handler adds newline, not formatter."""
        fmt = JSONLFormatter()
        record = self._make_record()
        line = fmt.format(record)
        assert not line.endswith("\n")

    def test_level_name_is_string(self):
        fmt = JSONLFormatter()
        record = self._make_record(level=logging.WARNING)
        parsed = json.loads(fmt.format(record))
        assert parsed["level"] == "WARNING"

    def test_missing_mds_fields_use_defaults(self):
        fmt = JSONLFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="",
            lineno=0, msg="bare log", args=(), exc_info=None,
        )
        parsed = json.loads(fmt.format(record))
        assert parsed["component"] == "test"
        assert parsed["source"] == "gcs"
        assert parsed["drone_id"] is None

    def test_missing_mds_fields_fall_back_to_process_context(self):
        set_source("drone")
        set_session("s_20260322_080000")
        set_drone_id("7")

        fmt = JSONLFormatter()
        record = logging.LogRecord(
            name="urllib3.connectionpool", level=logging.WARNING, pathname="",
            lineno=0, msg="connection retry", args=(), exc_info=None,
        )

        parsed = json.loads(fmt.format(record))
        assert parsed["component"] == "urllib3.connectionpool"
        assert parsed["source"] == "drone"
        assert parsed["session_id"] == "s_20260322_080000"
        assert parsed["drone_id"] == 7


class TestConsoleFormatter:
    def _make_record(self, msg="hello", level=logging.INFO):
        record = logging.LogRecord(
            name="test", level=level, pathname="",
            lineno=0, msg=msg, args=(), exc_info=None,
        )
        record.mds_component = "coordinator"
        record.mds_extra = None
        return record

    def test_output_contains_component_in_brackets(self):
        fmt = ConsoleFormatter()
        record = self._make_record()
        line = fmt.format(record)
        assert "[coordinator]" in line

    def test_output_contains_level(self):
        fmt = ConsoleFormatter()
        record = self._make_record(level=logging.ERROR)
        line = fmt.format(record)
        assert "ERROR" in line

    def test_output_contains_message(self):
        fmt = ConsoleFormatter()
        record = self._make_record(msg="drone armed")
        line = fmt.format(record)
        assert "drone armed" in line

    def test_extra_fields_appended(self):
        fmt = ConsoleFormatter()
        record = self._make_record()
        record.mds_extra = {"battery": 12.4}
        line = fmt.format(record)
        assert "battery=12.4" in line
