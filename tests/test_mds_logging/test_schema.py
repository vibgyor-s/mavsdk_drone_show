"""Tests for mds_logging.schema — JSONL log entry schema."""
import json
import pytest
from mds_logging.schema import build_log_entry, REQUIRED_FIELDS, VALID_LEVELS, VALID_SOURCES


class TestBuildLogEntry:
    def test_minimal_entry_has_all_required_fields(self):
        entry = build_log_entry(
            level="INFO",
            component="test",
            source="gcs",
            msg="hello",
            session_id="s_20260319_140000",
        )
        for field in REQUIRED_FIELDS:
            assert field in entry, f"Missing required field: {field}"

    def test_timestamp_is_iso8601_utc(self):
        entry = build_log_entry(
            level="INFO", component="test", source="gcs",
            msg="hello", session_id="s_20260319_140000",
        )
        ts = entry["ts"]
        assert ts.endswith("Z"), f"Timestamp must end with Z: {ts}"
        assert "T" in ts, f"Timestamp must contain T: {ts}"

    def test_entry_serializes_to_valid_json(self):
        entry = build_log_entry(
            level="DEBUG", component="coord", source="drone",
            msg="test msg", session_id="s_20260319_140000",
            drone_id=5, extra={"key": "value"},
        )
        line = json.dumps(entry)
        parsed = json.loads(line)
        assert parsed["level"] == "DEBUG"
        assert parsed["drone_id"] == 5
        assert parsed["extra"]["key"] == "value"

    def test_drone_id_defaults_to_none(self):
        entry = build_log_entry(
            level="INFO", component="api", source="gcs",
            msg="test", session_id="s_20260319_140000",
        )
        assert entry["drone_id"] is None

    def test_extra_defaults_to_none(self):
        entry = build_log_entry(
            level="INFO", component="api", source="gcs",
            msg="test", session_id="s_20260319_140000",
        )
        assert entry["extra"] is None

    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="level"):
            build_log_entry(
                level="TRACE", component="test", source="gcs",
                msg="bad", session_id="s_20260319_140000",
            )

    def test_invalid_source_raises(self):
        with pytest.raises(ValueError, match="source"):
            build_log_entry(
                level="INFO", component="test", source="unknown",
                msg="bad", session_id="s_20260319_140000",
            )

    def test_valid_levels(self):
        assert set(VALID_LEVELS) == {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def test_valid_sources(self):
        assert set(VALID_SOURCES) == {"drone", "gcs", "frontend", "infra"}
