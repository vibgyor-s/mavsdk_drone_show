# tests/test_command_system.py
"""
Command System Tests - Enterprise-Grade Validation
===================================================
Comprehensive test suite for the command tracking and validation system.

Tests cover:
- CommandErrorCode enum
- Command validation in drone_api_server
- CommandTracker lifecycle management
- GCS command endpoints
- Schemas validation

Author: MAVSDK Drone Show Test Team
Last Updated: 2026-01-05
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Path configuration is handled by conftest.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gcs-server'))


# ============================================================================
# CommandErrorCode Tests
# ============================================================================

class TestCommandErrorCode:
    """Test CommandErrorCode enum and descriptions"""

    def test_error_code_values(self):
        """Test that error codes have expected values"""
        from src.enums import CommandErrorCode

        # Validation errors (E1xx)
        assert CommandErrorCode.MISSING_MISSION_TYPE.value == "E100"
        assert CommandErrorCode.INVALID_MISSION_TYPE.value == "E101"
        assert CommandErrorCode.MISSING_TRIGGER_TIME.value == "E102"
        assert CommandErrorCode.INVALID_TRIGGER_TIME.value == "E103"
        assert CommandErrorCode.INVALID_ALTITUDE.value == "E104"

        # State errors (E2xx)
        assert CommandErrorCode.INVALID_STATE.value == "E200"
        assert CommandErrorCode.ALREADY_EXECUTING.value == "E203"
        assert CommandErrorCode.NOT_READY_TO_ARM.value == "E202"

        # Communication errors (E3xx)
        assert CommandErrorCode.TIMEOUT.value == "E300"
        assert CommandErrorCode.HTTP_ERROR.value == "E303"

        # Execution errors (E4xx)
        assert CommandErrorCode.MAVSDK_ERROR.value == "E400"

        # System errors (E5xx)
        assert CommandErrorCode.INTERNAL_ERROR.value == "E500"

    def test_error_descriptions(self):
        """Test that error codes have human-readable descriptions"""
        from src.enums import CommandErrorCode

        desc = CommandErrorCode.get_description("E100")
        assert "missionType" in desc.lower() or "mission" in desc.lower()

        desc = CommandErrorCode.get_description("E200")
        assert "state" in desc.lower()

        desc = CommandErrorCode.get_description("E300")
        assert "timed out" in desc.lower() or "timeout" in desc.lower()

        # Unknown code
        desc = CommandErrorCode.get_description("UNKNOWN")
        assert "unknown" in desc.lower()


# ============================================================================
# CommandTracker Tests
# ============================================================================

class TestCommandTracker:
    """Test CommandTracker lifecycle management"""

    @pytest.fixture
    def tracker(self):
        """Create a fresh CommandTracker for each test"""
        from command_tracker import CommandTracker
        return CommandTracker(max_commands=100)

    @pytest.mark.asyncio
    async def test_create_command(self, tracker):
        """Test command creation"""
        command_id = await tracker.create_command(
            mission_type=10,
            target_drones=['1', '2', '3'],
            params={'takeoff_altitude': 10}
        )

        assert command_id is not None
        assert len(command_id) == 36  # UUID format

        status = await tracker.get_status(command_id)
        assert status is not None
        assert status['mission_type'] == 10
        assert status['target_drones'] == ['1', '2', '3']
        assert status['status'] == 'created'
        assert status['acks']['expected'] == 3

    @pytest.mark.asyncio
    async def test_record_ack_accepted(self, tracker):
        """Test recording accepted acknowledgments"""
        command_id = await tracker.create_command(
            mission_type=10,
            target_drones=['1', '2']
        )

        # Record ACK from drone 1
        success = await tracker.record_ack(
            command_id, hw_id='1', status='accepted', message='OK'
        )
        assert success

        status = await tracker.get_status(command_id)
        assert status['acks']['received'] == 1
        assert status['acks']['accepted'] == 1
        assert '1' in status['acks']['details']

        # Record ACK from drone 2
        await tracker.record_ack(
            command_id, hw_id='2', status='accepted'
        )

        status = await tracker.get_status(command_id)
        assert status['acks']['received'] == 2
        assert status['acks']['accepted'] == 2
        assert status['status'] == 'executing'  # All ACKs received

    @pytest.mark.asyncio
    async def test_record_ack_rejected(self, tracker):
        """Test recording rejected acknowledgments"""
        command_id = await tracker.create_command(
            mission_type=10,
            target_drones=['1', '2']
        )

        # Both drones reject
        await tracker.record_ack(
            command_id, hw_id='1', status='rejected',
            error_code='E202', message='Not ready to arm'
        )
        await tracker.record_ack(
            command_id, hw_id='2', status='rejected',
            error_code='E202'
        )

        status = await tracker.get_status(command_id)
        assert status['acks']['rejected'] == 2
        assert status['status'] == 'failed'
        assert 'E202' in status['acks']['details']['1']['error_code']

    @pytest.mark.asyncio
    async def test_record_execution(self, tracker):
        """Test recording execution results"""
        command_id = await tracker.create_command(
            mission_type=10,
            target_drones=['1']
        )

        # ACK first
        await tracker.record_ack(command_id, hw_id='1', status='accepted')

        # Record execution
        success = await tracker.record_execution(
            command_id, hw_id='1', success=True,
            duration_ms=5000
        )
        assert success

        status = await tracker.get_status(command_id)
        assert status['executions']['succeeded'] == 1
        assert status['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_partial_success(self, tracker):
        """Test partial success scenario"""
        command_id = await tracker.create_command(
            mission_type=10,
            target_drones=['1', '2', '3']
        )

        # All accept
        for hw_id in ['1', '2', '3']:
            await tracker.record_ack(command_id, hw_id=hw_id, status='accepted')

        # 2 succeed, 1 fails
        await tracker.record_execution(command_id, hw_id='1', success=True)
        await tracker.record_execution(command_id, hw_id='2', success=True)
        await tracker.record_execution(
            command_id, hw_id='3', success=False,
            error_message='Script crashed'
        )

        status = await tracker.get_status(command_id)
        assert status['executions']['succeeded'] == 2
        assert status['executions']['failed'] == 1
        assert status['status'] == 'partial'

    @pytest.mark.asyncio
    async def test_cancel_command(self, tracker):
        """Test command cancellation"""
        command_id = await tracker.create_command(
            mission_type=10,
            target_drones=['1']
        )

        success = await tracker.cancel_command(command_id, "Test cancel")
        assert success

        status = await tracker.get_status(command_id)
        assert status['status'] == 'cancelled'

    @pytest.mark.asyncio
    async def test_get_recent_commands(self, tracker):
        """Test retrieving recent commands"""
        # Create multiple commands with explicit pauses for timestamp ordering
        created_ids = []
        for i in range(5):
            cmd_id = await tracker.create_command(
                mission_type=10 + i,
                target_drones=['1']
            )
            created_ids.append(cmd_id)

        commands = await tracker.get_recent(limit=3)
        assert len(commands) == 3

        # Verify we got 3 commands (order may vary with same timestamps)
        command_ids = [c['command_id'] for c in commands]
        assert len(set(command_ids)) == 3  # All unique

    @pytest.mark.asyncio
    async def test_statistics(self, tracker):
        """Test command statistics"""
        # Create and complete a command
        cmd1 = await tracker.create_command(mission_type=10, target_drones=['1'])
        await tracker.record_ack(cmd1, '1', 'accepted')
        await tracker.record_execution(cmd1, '1', True)

        # Create a failed command
        cmd2 = await tracker.create_command(mission_type=10, target_drones=['2'])
        await tracker.record_ack(cmd2, '2', 'rejected', error_code='E200')

        stats = await tracker.get_statistics()
        assert stats['total_commands'] == 2
        assert stats['successful_commands'] == 1
        assert stats['failed_commands'] == 1

    @pytest.mark.asyncio
    async def test_command_eviction(self):
        """Test that old commands are evicted when limit reached"""
        from command_tracker import CommandTracker
        tracker = CommandTracker(max_commands=3)

        # Create 4 commands
        ids = []
        for i in range(4):
            cmd_id = await tracker.create_command(
                mission_type=10,
                target_drones=['1']
            )
            ids.append(cmd_id)

        # First command should be evicted
        status = await tracker.get_status(ids[0])
        assert status is None

        # Last 3 should still exist
        for cmd_id in ids[1:]:
            status = await tracker.get_status(cmd_id)
            assert status is not None


# ============================================================================
# Command Validation Tests
# ============================================================================

class TestCommandValidation:
    """Test command validation in drone_api_server"""

    @pytest.fixture
    def mock_drone_config(self):
        """Create mock drone config"""
        config = Mock()
        config.hw_id = '1'
        config.pos_id = 0
        config.state = 0  # IDLE
        config.mission = 0  # NONE
        config.is_ready_to_arm = True
        config.current_command_id = None
        return config

    @pytest.fixture
    def mock_params(self):
        """Create mock params"""
        params = Mock()
        params.max_takeoff_alt = 50
        params.drone_api_port = 7070
        return params

    @pytest.fixture
    def api_server(self, mock_params, mock_drone_config):
        """Create DroneAPIServer instance"""
        from src.drone_api_server import DroneAPIServer
        server = DroneAPIServer(mock_params, mock_drone_config)
        return server

    def test_validate_missing_mission_type(self, api_server):
        """Test validation fails for missing missionType"""
        result = api_server._validate_command({
            'triggerTime': '0'
        })
        assert not result['valid']
        assert 'E100' in result['error_code']

    def test_validate_missing_trigger_time(self, api_server):
        """Test validation fails for missing triggerTime"""
        result = api_server._validate_command({
            'missionType': '10'
        })
        assert not result['valid']
        assert 'E102' in result['error_code']

    def test_validate_invalid_mission_type(self, api_server):
        """Test validation fails for unknown mission type"""
        result = api_server._validate_command({
            'missionType': '9999',
            'triggerTime': '0'
        })
        assert not result['valid']
        assert 'E101' in result['error_code']

    def test_validate_invalid_mission_type_format(self, api_server):
        """Test validation fails for non-numeric mission type"""
        result = api_server._validate_command({
            'missionType': 'not_a_number',
            'triggerTime': '0'
        })
        assert not result['valid']
        assert 'E107' in result['error_code']

    def test_validate_negative_trigger_time(self, api_server):
        """Test validation fails for negative trigger time"""
        result = api_server._validate_command({
            'missionType': '10',
            'triggerTime': '-1'
        })
        assert not result['valid']
        assert 'E103' in result['error_code']

    def test_validate_invalid_altitude(self, api_server):
        """Test validation fails for invalid takeoff altitude"""
        result = api_server._validate_command({
            'missionType': '10',
            'triggerTime': '0',
            'takeoff_altitude': '-5'
        })
        assert not result['valid']
        assert 'E104' in result['error_code']

    def test_validate_altitude_exceeds_max(self, api_server):
        """Test validation fails for altitude exceeding maximum"""
        result = api_server._validate_command({
            'missionType': '10',
            'triggerTime': '0',
            'takeoff_altitude': '100'  # Exceeds max of 50
        })
        assert not result['valid']
        assert 'E104' in result['error_code']

    def test_validate_success(self, api_server):
        """Test validation succeeds for valid command"""
        result = api_server._validate_command({
            'missionType': '10',
            'triggerTime': '0',
            'takeoff_altitude': '10'
        })
        assert result['valid']

    def test_check_state_executing(self, api_server):
        """Test state check fails during execution"""
        api_server.drone_config.state = 2  # MISSION_EXECUTING

        result = api_server._check_state_preconditions(mission_type=10)  # TAKE_OFF
        assert not result['valid']
        assert 'E203' in result['error_code']

    def test_check_state_emergency_allowed(self, api_server):
        """Test emergency commands allowed during execution"""
        api_server.drone_config.state = 2  # MISSION_EXECUTING

        result = api_server._check_state_preconditions(mission_type=105)  # KILL_TERMINATE
        assert result['valid']

    def test_check_state_not_ready_to_arm(self, api_server):
        """Test state check fails when not ready to arm"""
        api_server.drone_config.is_ready_to_arm = False

        result = api_server._check_state_preconditions(mission_type=10)  # TAKE_OFF
        assert not result['valid']
        assert 'E202' in result['error_code']


# ============================================================================
# Schema Validation Tests
# ============================================================================

class TestSchemas:
    """Test Pydantic schema validation"""

    def test_submit_command_request(self):
        """Test SubmitCommandRequest schema"""
        from schemas import SubmitCommandRequest

        # Valid request
        request = SubmitCommandRequest(
            missionType=10,
            triggerTime=0,
            takeoff_altitude=10.0
        )
        assert request.missionType == 10

        # Invalid altitude (negative)
        with pytest.raises(Exception):
            SubmitCommandRequest(
                missionType=10,
                takeoff_altitude=-5.0
            )

    def test_submit_command_response(self):
        """Test SubmitCommandResponse schema"""
        from schemas import SubmitCommandResponse

        response = SubmitCommandResponse(
            command_id="abc-123",
            status="submitted",
            mission_type=10,
            mission_name="TAKE_OFF",
            target_drones=["1", "2"],
            submitted_count=2,
            message="Command submitted",
            timestamp=int(time.time() * 1000)
        )
        assert response.command_id == "abc-123"
        assert response.submitted_count == 2

    def test_command_status_response(self):
        """Test CommandStatusResponse schema"""
        from schemas import CommandStatusResponse, AckSummary, ExecutionSummary, CommandStatus

        response = CommandStatusResponse(
            command_id="abc-123",
            mission_type=10,
            mission_name="TAKE_OFF",
            target_drones=["1"],
            status=CommandStatus.COMPLETED,
            created_at=int(time.time() * 1000),
            updated_at=int(time.time() * 1000),
            acks=AckSummary(
                expected=1, received=1, accepted=1, rejected=0
            ),
            executions=ExecutionSummary(
                expected=1, received=1, succeeded=1, failed=0
            )
        )
        assert response.status == CommandStatus.COMPLETED

    def test_execution_report_request(self):
        """Test ExecutionReportRequest schema"""
        from schemas import ExecutionReportRequest

        report = ExecutionReportRequest(
            command_id="abc-123",
            hw_id="1",
            success=False,
            error_message="Script failed",
            exit_code=1,
            duration_ms=5000
        )
        assert report.success == False
        assert report.exit_code == 1


# ============================================================================
# Integration Tests (require mock server)
# ============================================================================

class TestCommandEndpointIntegration:
    """Integration tests for command endpoints"""

    @pytest.fixture
    def mock_config_data(self):
        """Mock drone configuration"""
        return [
            {'pos_id': 0, 'hw_id': '1', 'ip': '192.168.1.101'},
            {'pos_id': 1, 'hw_id': '2', 'ip': '192.168.1.102'},
        ]

    @pytest.mark.skip(reason="Requires full server setup - run manually")
    @pytest.mark.asyncio
    async def test_submit_and_track_command(self, mock_config_data):
        """Test full command submission and tracking flow"""
        # This would test:
        # 1. POST /submit_command
        # 2. GET /command/{id}
        # 3. Wait for ACKs
        # 4. Verify status progression
        pass


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
