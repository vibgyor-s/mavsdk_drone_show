"""Integration tests for SSE streaming pipeline.

Tests the full path: Logger → WatcherHandler → LogWatcher → SSE consumer.
SSE endpoint streaming is verified via route registration (TestClient blocks
on infinite async generators), so these tests focus on the pub/sub pipeline.
"""
import json
import logging
import asyncio
import pytest

from mds_logging.watcher import LogWatcher
from mds_logging.handlers import WatcherHandler
from mds_logging.formatter import JSONLFormatter


class TestSSEPipeline:
    def test_logger_to_watcher_pipeline(self):
        """Log record → WatcherHandler → LogWatcher buffer."""
        watcher = LogWatcher(max_buffer=10)
        formatter = JSONLFormatter()
        handler = WatcherHandler(watcher, formatter)
        handler.setLevel(logging.DEBUG)

        test_logger = logging.getLogger("sse_test_pipeline")
        test_logger.handlers.clear()
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("pipeline test message")

        assert len(watcher._buffer) == 1
        assert watcher._buffer[0]["msg"] == "pipeline test message"
        assert watcher._buffer[0]["level"] == "INFO"

    @pytest.mark.asyncio
    async def test_subscribe_receives_buffered_entries(self):
        """New subscriber receives entries already in the buffer."""
        watcher = LogWatcher(max_buffer=5)
        for i in range(3):
            watcher.publish({"level": "INFO", "msg": f"buf_{i}"})

        entries = []
        async for entry in watcher.subscribe():
            entries.append(entry)
            if len(entries) >= 3:
                break
        assert len(entries) == 3
        assert entries[0]["msg"] == "buf_0"
        assert entries[2]["msg"] == "buf_2"

    @pytest.mark.asyncio
    async def test_subscribe_level_filter(self):
        """Subscriber with level filter only receives matching entries."""
        watcher = LogWatcher(max_buffer=10)
        watcher.publish({"level": "DEBUG", "msg": "skip_debug"})
        watcher.publish({"level": "INFO", "msg": "skip_info"})
        watcher.publish({"level": "WARNING", "msg": "keep_warning"})
        watcher.publish({"level": "ERROR", "msg": "keep_error"})

        entries = []
        async for entry in watcher.subscribe(level="WARNING"):
            entries.append(entry)
            if len(entries) >= 2:
                break
        assert len(entries) == 2
        assert entries[0]["msg"] == "keep_warning"
        assert entries[1]["msg"] == "keep_error"

    @pytest.mark.asyncio
    async def test_subscribe_component_filter(self):
        """Subscriber with component filter only receives matching entries."""
        watcher = LogWatcher(max_buffer=10)
        watcher.publish({"level": "INFO", "component": "gcs", "msg": "skip"})
        watcher.publish({"level": "INFO", "component": "coord", "msg": "match"})

        entries = []
        async for entry in watcher.subscribe(component="coord"):
            entries.append(entry)
            if len(entries) >= 1:
                break
        assert entries[0]["msg"] == "match"

    @pytest.mark.asyncio
    async def test_live_publish_reaches_subscriber(self):
        """Entry published after subscribe() is called reaches the subscriber."""
        watcher = LogWatcher(max_buffer=0)  # No buffer — only live

        received = []

        async def consumer():
            async for entry in watcher.subscribe():
                received.append(entry)
                if len(received) >= 1:
                    break

        # Start consumer, then publish
        task = asyncio.create_task(consumer())
        await asyncio.sleep(0.01)  # Let consumer start
        watcher.publish({"level": "INFO", "msg": "live_entry"})
        await asyncio.wait_for(task, timeout=2.0)

        assert len(received) == 1
        assert received[0]["msg"] == "live_entry"

    def test_handler_formats_and_publishes(self):
        """WatcherHandler formats LogRecord as JSON and publishes to watcher."""
        watcher = LogWatcher(max_buffer=10)
        formatter = JSONLFormatter()
        handler = WatcherHandler(watcher, formatter)

        record = logging.LogRecord(
            name="test", level=logging.WARNING,
            pathname="test.py", lineno=1, msg="handler test",
            args=(), exc_info=None,
        )
        record.mds_component = "test_comp"
        record.mds_source = "gcs"
        record.mds_session_id = "s_test"
        record.mds_drone_id = None
        record.mds_extra = None

        handler.emit(record)

        assert len(watcher._buffer) == 1
        entry = watcher._buffer[0]
        assert entry["msg"] == "handler test"
        assert entry["level"] == "WARNING"
        assert entry["component"] == "test_comp"
