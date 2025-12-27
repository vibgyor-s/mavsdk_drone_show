# tests/test_schema_validation.py
"""
Schema Validation Tests
=======================
Tests for Pydantic schema validation in gcs-server/schemas.py.
"""

import pytest
from pydantic import ValidationError


class TestDroneConfigValidation:
    """Test DroneConfig schema validation"""

    def test_valid_config(self):
        """Test valid drone configuration"""
        from gcs_server_schemas import DroneConfig

        config = DroneConfig(
            pos_id=1,
            hw_id="drone1",
            ip="192.168.1.100",
            connection_str="udp://:14550"
        )

        assert config.pos_id == 1
        assert config.hw_id == "drone1"
        assert config.ip == "192.168.1.100"

    def test_invalid_ip_format(self):
        """Test rejection of invalid IP format"""
        from gcs_server_schemas import DroneConfig

        with pytest.raises(ValidationError) as exc_info:
            DroneConfig(
                pos_id=1,
                hw_id="drone1",
                ip="not-an-ip",
                connection_str="udp://:14550"
            )

        assert "ip" in str(exc_info.value).lower()

    def test_invalid_ip_octet_range(self):
        """Test rejection of IP with octets > 255"""
        from gcs_server_schemas import DroneConfig

        with pytest.raises(ValidationError):
            DroneConfig(
                pos_id=1,
                hw_id="drone1",
                ip="192.168.1.300",
                connection_str="udp://:14550"
            )

    def test_negative_pos_id(self):
        """Test rejection of negative pos_id"""
        from gcs_server_schemas import DroneConfig

        with pytest.raises(ValidationError) as exc_info:
            DroneConfig(
                pos_id=-1,
                hw_id="drone1",
                ip="192.168.1.100",
                connection_str="udp://:14550"
            )

        assert "pos_id" in str(exc_info.value).lower()

    def test_empty_hw_id(self):
        """Test rejection of empty hw_id"""
        from gcs_server_schemas import DroneConfig

        with pytest.raises(ValidationError) as exc_info:
            DroneConfig(
                pos_id=1,
                hw_id="",
                ip="192.168.1.100",
                connection_str="udp://:14550"
            )

        assert "hw_id" in str(exc_info.value).lower()

    def test_extra_fields_ignored(self):
        """Test that extra fields are silently ignored"""
        from gcs_server_schemas import DroneConfig

        config = DroneConfig(
            pos_id=1,
            hw_id="drone1",
            ip="192.168.1.100",
            connection_str="udp://:14550",
            unknown_field="should be ignored"
        )

        assert not hasattr(config, 'unknown_field')


class TestPositionGPSValidation:
    """Test PositionGPS schema validation"""

    def test_valid_gps_position(self):
        """Test valid GPS coordinates"""
        from gcs_server_schemas import PositionGPS

        pos = PositionGPS(
            latitude=37.7749,
            longitude=-122.4194,
            altitude=100.0
        )

        assert pos.latitude == 37.7749
        assert pos.longitude == -122.4194

    def test_latitude_out_of_range(self):
        """Test rejection of latitude > 90"""
        from gcs_server_schemas import PositionGPS

        with pytest.raises(ValidationError):
            PositionGPS(
                latitude=91.0,
                longitude=-122.4194,
                altitude=100.0
            )

    def test_latitude_negative_out_of_range(self):
        """Test rejection of latitude < -90"""
        from gcs_server_schemas import PositionGPS

        with pytest.raises(ValidationError):
            PositionGPS(
                latitude=-91.0,
                longitude=-122.4194,
                altitude=100.0
            )

    def test_longitude_out_of_range(self):
        """Test rejection of longitude > 180"""
        from gcs_server_schemas import PositionGPS

        with pytest.raises(ValidationError):
            PositionGPS(
                latitude=37.7749,
                longitude=181.0,
                altitude=100.0
            )


class TestBatteryStatusValidation:
    """Test BatteryStatus schema validation"""

    def test_valid_battery(self):
        """Test valid battery status"""
        from gcs_server_schemas import BatteryStatus

        battery = BatteryStatus(
            voltage=12.6,
            current=5.0,
            remaining=75.0
        )

        assert battery.voltage == 12.6
        assert battery.remaining == 75.0

    def test_negative_voltage(self):
        """Test rejection of negative voltage"""
        from gcs_server_schemas import BatteryStatus

        with pytest.raises(ValidationError):
            BatteryStatus(
                voltage=-1.0,
                remaining=50.0
            )

    def test_remaining_over_100(self):
        """Test rejection of remaining > 100%"""
        from gcs_server_schemas import BatteryStatus

        with pytest.raises(ValidationError):
            BatteryStatus(
                voltage=12.6,
                remaining=150.0
            )

    def test_remaining_negative(self):
        """Test rejection of negative remaining"""
        from gcs_server_schemas import BatteryStatus

        with pytest.raises(ValidationError):
            BatteryStatus(
                voltage=12.6,
                remaining=-10.0
            )


class TestHeartbeatValidation:
    """Test heartbeat schema validation"""

    def test_valid_heartbeat_request(self):
        """Test valid heartbeat request"""
        from gcs_server_schemas import HeartbeatRequest

        heartbeat = HeartbeatRequest(
            pos_id=1,
            hw_id="drone1"
        )

        assert heartbeat.pos_id == 1
        assert heartbeat.hw_id == "drone1"

    def test_negative_pos_id_heartbeat(self):
        """Test rejection of negative pos_id in heartbeat"""
        from gcs_server_schemas import HeartbeatRequest

        with pytest.raises(ValidationError):
            HeartbeatRequest(
                pos_id=-1,
                hw_id="drone1"
            )


class TestTrajectoryPointValidation:
    """Test TrajectoryPoint schema validation"""

    def test_valid_trajectory_point(self):
        """Test valid trajectory point"""
        from gcs_server_schemas import TrajectoryPoint

        point = TrajectoryPoint(
            t=0.0,
            x=10.0,
            y=20.0,
            z=5.0,
            yaw=45.0
        )

        assert point.t == 0.0
        assert point.z == 5.0

    def test_negative_time(self):
        """Test rejection of negative time"""
        from gcs_server_schemas import TrajectoryPoint

        with pytest.raises(ValidationError):
            TrajectoryPoint(
                t=-1.0,
                x=10.0,
                y=20.0,
                z=5.0
            )

    def test_negative_altitude(self):
        """Test rejection of negative altitude"""
        from gcs_server_schemas import TrajectoryPoint

        with pytest.raises(ValidationError):
            TrajectoryPoint(
                t=0.0,
                x=10.0,
                y=20.0,
                z=-5.0
            )


class TestGPSFixValidation:
    """Test GPS fix type validation"""

    def test_valid_gps_fix_range(self):
        """Test valid GPS fix types (0-6)"""
        from gcs_server_schemas import DroneTelemetry, DroneState, FlightMode

        # GPS fix type 3 is typical 3D fix
        telemetry = DroneTelemetry(
            pos_id=1,
            hw_id="drone1",
            state=DroneState.IDLE,
            flight_mode=FlightMode.MANUAL,
            armed=False,
            in_air=False,
            health_ok=True,
            gps_fix=3,
            timestamp=1234567890
        )

        assert telemetry.gps_fix == 3

    def test_invalid_gps_fix_high(self):
        """Test rejection of GPS fix > 6"""
        from gcs_server_schemas import DroneTelemetry, DroneState, FlightMode

        with pytest.raises(ValidationError):
            DroneTelemetry(
                pos_id=1,
                hw_id="drone1",
                state=DroneState.IDLE,
                flight_mode=FlightMode.MANUAL,
                armed=False,
                in_air=False,
                health_ok=True,
                gps_fix=7,  # Invalid: max is 6
                timestamp=1234567890
            )


# Import helper to make schemas accessible
# Path configuration is handled by conftest.py
@pytest.fixture(scope="module", autouse=True)
def setup_imports():
    """Setup imports for schema tests"""
    import sys
    # Create module alias for cleaner imports in tests
    import schemas as gcs_server_schemas
    sys.modules['gcs_server_schemas'] = gcs_server_schemas


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
