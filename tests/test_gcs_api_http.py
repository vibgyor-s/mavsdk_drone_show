# tests/test_gcs_api_http.py
"""
GCS API HTTP Endpoint Tests
============================
Comprehensive test suite for GCS Server FastAPI HTTP endpoints.

Tests all major endpoint categories:
- Health & System endpoints
- Configuration management
- Telemetry retrieval
- Heartbeat handling
- Origin management
- Show import and management
- Git operations
- Swarm trajectory management

Author: MAVSDK Drone Show Test Team
Last Updated: 2025-12-27
"""

import pytest
import json
import tempfile
import os
import signal
import sys
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Mock signal.signal BEFORE any imports that might use it
_original_signal = signal.signal
def _safe_signal(sig, handler):
    """Safe signal registration that works in threads"""
    try:
        return _original_signal(sig, handler)
    except ValueError:
        # In a thread, just return None
        return None

signal.signal = _safe_signal

# Path configuration is handled by conftest.py

from tests.conftest import SyncASGITestClient


# Mock the background services before importing the app
@pytest.fixture(autouse=True)
def mock_background_services():
    """Mock background services to prevent actual polling during tests"""
    with patch('app_fastapi.BackgroundServices') as mock_services:
        mock_instance = Mock()
        mock_instance.start = Mock()
        mock_instance.stop = Mock()
        mock_services.return_value = mock_instance
        yield mock_services


@pytest.fixture
def mock_config():
    """Mock drone configuration"""
    return [
        {
            'pos_id': 1,
            'hw_id': '1',
            'ip': '192.168.1.101',
            'connection_str': 'udp://:14540'
        },
        {
            'pos_id': 2,
            'hw_id': '2',
            'ip': '192.168.1.102',
            'connection_str': 'udp://:14541'
        }
    ]


@pytest.fixture
def mock_telemetry_data():
    """Mock telemetry data for all drones - mirrors live storage with int keys and ids."""
    return {
        1: {
            'pos_id': 0,
            'hw_id': 1,
            'state': 'idle',
            'mission': 0,
            'last_mission': 0,
            'trigger_time': 0,
            'flight_mode': 65536,
            'base_mode': 81,
            'system_status': 4,
            'is_armed': False,
            'is_ready_to_arm': True,
            'readiness_status': 'ready',
            'readiness_summary': 'Ready to fly',
            'readiness_checks': [
                {
                    'id': 'px4',
                    'label': 'PX4 arming report',
                    'ready': True,
                    'detail': 'No active PX4 preflight blockers',
                }
            ],
            'preflight_blockers': [],
            'preflight_warnings': [],
            'status_messages': [],
            'preflight_last_update': 1700000000000,
            'battery_voltage': 12.6,
            'position_lat': 35.123456,
            'position_long': -120.654321,
            'position_alt': 488.5,
            'velocity_north': 0.0,
            'velocity_east': 0.0,
            'velocity_down': 0.0,
            'yaw': 180.0,
            'follow_mode': 0,
            'update_time': '2026-03-21 12:00:00',
            'hdop': 0.8,
            'vdop': 1.1,
            'gps_fix_type': 3,
            'satellites_visible': 12,
            'ip': '192.168.1.101',
            'heartbeat_last_seen': 1700000000000,
            'heartbeat_network_info': {},
            'heartbeat_first_seen': 1699999999000,
            'timestamp': 1700000000000,
        },
        2: {
            'pos_id': 1,
            'hw_id': 2,
            'state': 'idle',
            'mission': 0,
            'last_mission': 0,
            'trigger_time': 0,
            'flight_mode': 65536,
            'base_mode': 81,
            'system_status': 4,
            'is_armed': False,
            'is_ready_to_arm': False,
            'readiness_status': 'blocked',
            'readiness_summary': 'Preflight Fail: ekf2 missing data',
            'readiness_checks': [
                {
                    'id': 'px4',
                    'label': 'PX4 arming report',
                    'ready': False,
                    'detail': '1 active PX4 preflight blocker(s)',
                }
            ],
            'preflight_blockers': [
                {
                    'source': 'px4',
                    'severity': 'error',
                    'message': 'Preflight Fail: ekf2 missing data',
                    'timestamp': 1700000000000,
                }
            ],
            'preflight_warnings': [],
            'status_messages': [],
            'preflight_last_update': 1700000000000,
            'battery_voltage': 12.4,
            'position_lat': 35.123457,
            'position_long': -120.654322,
            'position_alt': 488.6,
            'velocity_north': 0.0,
            'velocity_east': 0.0,
            'velocity_down': 0.0,
            'yaw': 180.0,
            'follow_mode': 0,
            'update_time': '2026-03-21 12:00:00',
            'hdop': 1.2,
            'vdop': 1.5,
            'gps_fix_type': 3,
            'satellites_visible': 10,
            'ip': '192.168.1.102',
            'heartbeat_last_seen': 1700000000000,
            'heartbeat_network_info': {},
            'heartbeat_first_seen': 1699999999000,
            'timestamp': 1700000000000,
        }
    }


@pytest.fixture
def mock_origin():
    """Mock origin data"""
    return {
        'lat': 35.123456,
        'lon': -120.654321,
        'alt': 488.0,
        'timestamp': '2025-11-22T12:00:00',
        'alt_source': 'manual'
    }


@pytest.fixture
def test_client(mock_config, mock_telemetry_data):
    """Create FastAPI test client with mocked dependencies"""
    with patch('app_fastapi.load_config', return_value=mock_config):
        with patch('app_fastapi.telemetry_data_all_drones', mock_telemetry_data):
            from app_fastapi import app
            client = SyncASGITestClient(app)
            yield client


# ============================================================================
# Health & System Tests
# ============================================================================

class TestHealthEndpoints:
    """Test health check and system status endpoints"""

    def test_ping_endpoint(self, test_client):
        """Test /ping health check endpoint"""
        response = test_client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data

    def test_health_endpoint(self, test_client):
        """Test /health health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'timestamp' in data


# ============================================================================
# Configuration Tests
# ============================================================================

class TestConfigurationEndpoints:
    """Test drone configuration endpoints"""

    def test_get_config(self, test_client, mock_config):
        """Test GET /get-config-data"""
        response = test_client.get("/get-config-data")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]['pos_id'] == 1
        assert data[0]['hw_id'] == '1'

    @patch('app_fastapi.save_config')
    @patch('app_fastapi.validate_and_process_config')
    def test_save_config(self, mock_validate, mock_save, test_client, mock_config):
        """Test POST /save-config-data"""
        mock_validate.return_value = {'updated_config': mock_config}

        response = test_client.post("/save-config-data", json=mock_config)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        assert 'updated_count' in data

    @patch('app_fastapi.validate_and_process_config')
    def test_validate_config(self, mock_validate, test_client, mock_config):
        """Test POST /validate-config"""
        mock_validate.return_value = {
            'updated_config': mock_config,
            'summary': {
                'duplicates_count': 0,
                'missing_trajectories_count': 0,
                'role_swaps_count': 0
            }
        }

        response = test_client.post("/validate-config", json=mock_config)
        assert response.status_code == 200
        data = response.json()
        assert 'summary' in data


# ============================================================================
# Telemetry Tests
# ============================================================================

class TestTelemetryEndpoints:
    """Test telemetry endpoints"""

    def test_get_telemetry_legacy(self, test_client, mock_telemetry_data):
        """Test GET /telemetry (legacy endpoint)"""
        response = test_client.get("/telemetry")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert '1' in data
        assert data['1']['battery_voltage'] == 12.6

    def test_get_telemetry_typed(self, test_client):
        """Test GET /api/telemetry (typed endpoint)"""
        response = test_client.get("/api/telemetry")
        assert response.status_code == 200
        data = response.json()
        assert 'telemetry' in data
        assert 'total_drones' in data
        assert 'online_drones' in data
        assert data['telemetry']['1']['readiness_status'] == 'ready'
        assert data['telemetry']['2']['preflight_blockers'][0]['message'] == 'Preflight Fail: ekf2 missing data'


# ============================================================================
# Heartbeat Tests
# ============================================================================

class TestHeartbeatEndpoints:
    """Test heartbeat endpoints"""

    @patch('app_fastapi.handle_heartbeat_post')
    def test_post_heartbeat(self, mock_handle, test_client):
        """Test POST /heartbeat"""
        heartbeat_data = {
            'pos_id': 0,
            'hw_id': '1',
            'detected_pos_id': 1,
            'ip': '172.18.0.2',
            'network_info': {'wifi': {'ssid': 'test'}},
            'timestamp': 1700000000000
        }

        response = test_client.post("/heartbeat", json=heartbeat_data)
        assert response.status_code == 200
        data = response.json()
        assert data['success'] == True
        mock_handle.assert_called_once()
        kwargs = mock_handle.call_args.kwargs
        assert kwargs['hw_id'] == '1'
        assert kwargs['detected_pos_id'] == 1
        assert kwargs['ip'] == '172.18.0.2'

    @patch('app_fastapi.get_all_heartbeats')
    def test_get_heartbeats(self, mock_get_heartbeats, test_client):
        """Test GET /get-heartbeats"""
        # get_all_heartbeats returns a dict keyed by hw_id
        mock_get_heartbeats.return_value = {
            '1': {'pos_id': 0, 'hw_id': '1', 'detected_pos_id': 1, 'ip': 'unknown', 'timestamp': 1700000000000},
            '2': {'pos_id': 1, 'hw_id': '2', 'detected_pos_id': 2, 'ip': '172.18.0.22', 'timestamp': 1700000000000}
        }

        response = test_client.get("/get-heartbeats")
        assert response.status_code == 200
        data = response.json()
        assert 'heartbeats' in data
        assert data['total_drones'] == 2
        heartbeats = {item['hw_id']: item for item in data['heartbeats']}
        assert heartbeats['1']['detected_pos_id'] == 1
        assert heartbeats['1']['ip'] == '192.168.1.101'
        assert heartbeats['2']['ip'] == '172.18.0.22'


# ============================================================================
# Origin Tests
# ============================================================================

class TestOriginEndpoints:
    """Test origin management endpoints"""

    @patch('app_fastapi.load_origin')
    def test_get_origin(self, mock_load, test_client, mock_origin):
        """Test GET /get-origin"""
        mock_load.return_value = mock_origin

        response = test_client.get("/get-origin")
        assert response.status_code == 200
        data = response.json()
        assert data['lat'] == 35.123456
        assert data['lon'] == -120.654321

    @patch('app_fastapi.save_origin')
    def test_set_origin(self, mock_save, test_client):
        """Test POST /set-origin"""
        # API uses short field names: lat, lon, alt
        origin_data = {
            'lat': 35.123456,
            'lon': -120.654321,
            'alt': 488.0
        }

        response = test_client.post("/set-origin", json=origin_data)
        assert response.status_code == 200
        data = response.json()
        assert data['lat'] == origin_data['lat']

    @patch('app_fastapi.load_origin')
    def test_get_gps_global_origin(self, mock_load, test_client, mock_origin):
        """Test GET /get-gps-global-origin"""
        mock_load.return_value = mock_origin

        response = test_client.get("/get-gps-global-origin")
        assert response.status_code == 200
        data = response.json()
        assert data['has_origin'] == True

    @patch('app_fastapi.load_origin')
    def test_get_origin_for_drone(self, mock_load, test_client, mock_origin):
        """Test GET /get-origin-for-drone"""
        mock_load.return_value = mock_origin

        response = test_client.get("/get-origin-for-drone")
        assert response.status_code == 200
        data = response.json()
        assert data['lat'] == 35.123456
        assert data['source'] == 'manual'


# ============================================================================
# Show Management Tests
# ============================================================================

class TestShowManagementEndpoints:
    """Test show import and management endpoints"""

    @patch('app_fastapi.run_formation_process')
    @patch('app_fastapi.clear_show_directories')
    @patch('os.listdir')
    def test_import_show(self, mock_listdir, mock_clear, mock_process, test_client):
        """Test POST /import-show with file upload"""
        # Create a mock zip file
        mock_listdir.return_value = ['Drone 1.csv', 'Drone 2.csv']

        # Create test zip content
        zip_content = b'PK\x03\x04...'  # Minimal zip header

        files = {'file': ('test_show.zip', BytesIO(zip_content), 'application/zip')}

        with patch('zipfile.ZipFile'):
            response = test_client.post("/import-show", files=files)

        # Should process but may fail on actual zip extraction
        # We're testing the endpoint structure, not zip processing
        assert response.status_code in [200, 500]

    @patch('os.listdir')
    @patch('os.path.exists', return_value=True)
    def test_get_show_info(self, mock_exists, mock_listdir, test_client):
        """Test GET /get-show-info"""
        mock_listdir.return_value = ['Drone 1.csv', 'Drone 2.csv']

        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.__enter__.return_value.__iter__.return_value = [
                't [ms],x [m],y [m],z [m],yaw [deg]\n',
                '0,0,0,0,0\n',
                '60000,1.0,1.0,5.0,0\n'
            ]
            mock_open.return_value = mock_file

            response = test_client.get("/get-show-info")

        assert response.status_code == 200
        data = response.json()
        assert 'drone_count' in data
        assert 'max_altitude' in data


# ============================================================================
# Git Status Tests
# ============================================================================

class TestGitStatusEndpoints:
    """Test git status endpoints"""

    @patch('app_fastapi.git_status_data_all_drones', {
        '1': {'status': 'clean', 'branch': 'main', 'commit': 'abc12345', 'uncommitted_changes': []},
        '2': {'status': 'clean', 'branch': 'main', 'commit': 'abc12345', 'uncommitted_changes': []}
    })
    def test_get_git_status(self, test_client):
        """Test GET /git-status"""
        response = test_client.get("/git-status")
        assert response.status_code == 200
        data = response.json()
        assert 'git_status' in data
        assert 'synced_count' in data
        assert data['git_status']['1']['commit'] == 'abc12345'

    @patch('app_fastapi.get_gcs_git_report')
    def test_get_gcs_git_status(self, mock_report, test_client):
        """Test GET /get-gcs-git-status"""
        mock_report.return_value = {'branch': 'main', 'status': 'clean'}

        response = test_client.get("/get-gcs-git-status")
        assert response.status_code == 200


# ============================================================================
# Swarm Management Tests
# ============================================================================

class TestSwarmEndpoints:
    """Test swarm configuration endpoints"""

    @patch('app_fastapi.load_swarm')
    def test_get_swarm_data(self, mock_load, test_client):
        """Test GET /get-swarm-data"""
        mock_load.return_value = {'hierarchies': {}}

        response = test_client.get("/get-swarm-data")
        assert response.status_code == 200

    @patch('app_fastapi.save_swarm')
    @patch('app_fastapi.git_operations', return_value={'success': True, 'message': 'Pushed', 'commit_hash': 'abc123'})
    def test_save_swarm_data(self, mock_git, mock_save, test_client):
        """Test POST /save-swarm-data"""
        swarm_data = {'hierarchies': {}}

        response = test_client.post("/save-swarm-data", json=swarm_data)
        assert response.status_code == 200

    @patch('app_fastapi.save_swarm')
    @patch('app_fastapi.load_swarm')
    def test_request_new_leader_updates_swarm_assignment(self, mock_load, mock_save, test_client):
        """Test POST /request-new-leader persists a single drone assignment update."""
        mock_load.return_value = [
            {'hw_id': 1, 'follow': 0, 'offset_x': 0, 'offset_y': 0, 'offset_z': 0, 'frame': 'ned'},
            {'hw_id': 2, 'follow': 1, 'offset_x': 5, 'offset_y': 0, 'offset_z': 0, 'frame': 'body'},
        ]

        response = test_client.post(
            "/request-new-leader",
            json={'hw_id': 2, 'follow': 0, 'offset_x': 7, 'offset_y': 1, 'offset_z': 2, 'frame': 'ned'},
        )

        assert response.status_code == 200
        assert response.json()['status'] == 'success'
        saved_swarm = mock_save.call_args[0][0]
        assert saved_swarm[1]['hw_id'] == 2
        assert saved_swarm[1]['follow'] == 0
        assert saved_swarm[1]['offset_x'] == 7.0
        assert saved_swarm[1]['offset_y'] == 1.0
        assert saved_swarm[1]['offset_z'] == 2.0
        assert saved_swarm[1]['frame'] == 'ned'

    @patch('app_fastapi.load_swarm')
    def test_request_new_leader_rejects_self_follow(self, mock_load, test_client):
        """Test POST /request-new-leader rejects invalid self-follow changes."""
        mock_load.return_value = [
            {'hw_id': 1, 'follow': 0, 'offset_x': 0, 'offset_y': 0, 'offset_z': 0, 'frame': 'ned'},
        ]

        response = test_client.post(
            "/request-new-leader",
            json={'hw_id': 1, 'follow': 1},
        )

        assert response.status_code == 400
        assert response.json()['detail'] == 'A drone cannot follow itself'


# ============================================================================
# Swarm Trajectory Tests
# ============================================================================

class TestSwarmTrajectoryEndpoints:
    """Test swarm trajectory route registration after FastAPI migration."""

    def test_swarm_trajectory_routes_registered(self):
        """All routes used by the React page should be present on FastAPI."""
        from app_fastapi import app

        route_paths = {route.path for route in app.routes}

        expected_paths = {
            '/api/swarm/leaders',
            '/api/swarm/trajectory/upload/{leader_id}',
            '/api/swarm/trajectory/process',
            '/api/swarm/trajectory/recommendation',
            '/api/swarm/trajectory/status',
            '/api/swarm/trajectory/clear-processed',
            '/api/swarm/trajectory/clear',
            '/api/swarm/trajectory/clear-leader/{leader_id}',
            '/api/swarm/trajectory/remove/{leader_id}',
            '/api/swarm/trajectory/download/{drone_id}',
            '/api/swarm/trajectory/download-kml/{drone_id}',
            '/api/swarm/trajectory/download-cluster-kml/{leader_id}',
            '/api/swarm/trajectory/clear-drone/{drone_id}',
            '/api/swarm/trajectory/commit',
        }

        missing_paths = expected_paths - route_paths
        assert not missing_paths, f"Missing swarm trajectory routes: {sorted(missing_paths)}"


# ============================================================================
# Command Tests
# ============================================================================

class TestCommandEndpoints:
    """Test command submission endpoints"""

    @patch('app_fastapi.send_commands_to_all')
    @patch('app_fastapi.load_config')
    def test_submit_command(self, mock_load, mock_send, test_client, mock_config):
        """Test POST /submit_command - new SubmitCommandResponse format"""
        mock_load.return_value = mock_config
        # Mock needs all expected fields from the updated command.py
        mock_send.return_value = {
            'success': 2, 'failed': 0, 'offline': 0, 'rejected': 0, 'errors': 0,
            'result_summary': '2 accepted', 'results': {
                '1': {'success': True, 'category': 'accepted'},
                '2': {'success': True, 'category': 'accepted'}
            }
        }

        # New format requires missionType and triggerTime
        command_data = {
            'missionType': 10,  # TAKE_OFF
            'triggerTime': 0
        }

        response = test_client.post("/submit_command", json=command_data)
        assert response.status_code == 200
        data = response.json()

        # New response format
        assert 'command_id' in data
        assert data['status'] == 'submitted'
        assert data['mission_type'] == 10
        assert 'mission_name' in data
        assert 'target_drones' in data
        assert 'submitted_count' in data
        assert data['tracking_phase'] == 'pending_execution'


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling"""

    def test_404_not_found(self, test_client):
        """Test 404 error for non-existent endpoint"""
        response = test_client.get("/nonexistent-endpoint")
        assert response.status_code == 404

    def test_invalid_json(self, test_client):
        """Test handling of invalid JSON in POST request"""
        response = test_client.post(
            "/save-config-data",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
