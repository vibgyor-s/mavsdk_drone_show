# tests/test_constants.py
"""
Constants Module Tests
======================
Tests for the centralized constants in src/constants.py.
"""

import pytest


class TestPacketMarkers:
    """Test packet protocol markers"""

    def test_header_value(self):
        """Test header marker has expected value"""
        from src.constants import PacketMarkers

        assert PacketMarkers.HEADER == 77

    def test_terminator_value(self):
        """Test terminator marker has expected value"""
        from src.constants import PacketMarkers

        assert PacketMarkers.TERMINATOR == 88


class TestTrajectoryState:
    """Test trajectory state enum"""

    def test_state_values(self):
        """Test trajectory states have expected values"""
        from src.constants import TrajectoryState

        assert TrajectoryState.INITIAL_CLIMB == 10
        assert TrajectoryState.MANEUVERING == 70
        assert TrajectoryState.LANDING == 100

    def test_get_description_known_state(self):
        """Test getting description for known state"""
        from src.constants import TrajectoryState

        desc = TrajectoryState.get_description(TrajectoryState.MANEUVERING)
        assert "trajectory" in desc.lower() or "maneuver" in desc.lower()

    def test_get_description_unknown_state(self):
        """Test getting description for unknown state"""
        from src.constants import TrajectoryState

        desc = TrajectoryState.get_description(999)
        assert "Unknown" in desc
        assert "999" in desc

    def test_is_maneuvering_true(self):
        """Test is_maneuvering returns True for maneuvering state"""
        from src.constants import TrajectoryState

        assert TrajectoryState.is_maneuvering(70) == True
        assert TrajectoryState.is_maneuvering(TrajectoryState.MANEUVERING) == True

    def test_is_maneuvering_false(self):
        """Test is_maneuvering returns False for non-maneuvering states"""
        from src.constants import TrajectoryState

        assert TrajectoryState.is_maneuvering(10) == False
        assert TrajectoryState.is_maneuvering(100) == False
        assert TrajectoryState.is_maneuvering(TrajectoryState.LANDING) == False


class TestNetworkDefaults:
    """Test network default constants"""

    def test_mavlink_port(self):
        """Test default MAVLink port"""
        from src.constants import NetworkDefaults

        assert NetworkDefaults.MAVLINK_PORT == 14550

    def test_grpc_base_port(self):
        """Test default gRPC base port"""
        from src.constants import NetworkDefaults

        assert NetworkDefaults.GRPC_BASE_PORT == 50040

    def test_socket_buffer_size(self):
        """Test socket buffer size"""
        from src.constants import NetworkDefaults

        assert NetworkDefaults.SOCKET_BUFFER_SIZE == 1024

    def test_thread_pool_workers(self):
        """Test thread pool workers count"""
        from src.constants import NetworkDefaults

        assert NetworkDefaults.THREAD_POOL_WORKERS == 10


class TestTelemetryIndex:
    """Test telemetry data indices"""

    def test_header_index(self):
        """Test header index is 0"""
        from src.constants import TelemetryIndex

        assert TelemetryIndex.HEADER == 0

    def test_battery_voltage_index(self):
        """Test battery voltage index"""
        from src.constants import TelemetryIndex

        assert TelemetryIndex.BATTERY_VOLTAGE == 13

    def test_terminator_index(self):
        """Test terminator index is last"""
        from src.constants import TelemetryIndex

        assert TelemetryIndex.TERMINATOR == 16


class TestTimeConstants:
    """Test time-related constants"""

    def test_ms_per_second(self):
        """Test milliseconds per second"""
        from src.constants import TimeConstants

        assert TimeConstants.MS_PER_SECOND == 1000

    def test_seconds_per_minute(self):
        """Test seconds per minute"""
        from src.constants import TimeConstants

        assert TimeConstants.SECONDS_PER_MINUTE == 60


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
