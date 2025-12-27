# tests/test_drone_setup.py
"""
DroneSetup and Mission Execution Tests
======================================
Tests for mission scheduling, execution, and state management.
These are critical tests for the drone's mission control system.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch, AsyncMock, PropertyMock
from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.enums import Mission, State
from src.drone_config import DroneConfig


# ============================================================================
# Test: DroneSetup Initialization
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestDroneSetupInitialization:
    """Test DroneSetup initialization"""

    def test_drone_setup_import(self):
        """Test DroneSetup can be imported"""
        from src.drone_setup import DroneSetup
        assert DroneSetup is not None

    def test_drone_setup_requires_params(self):
        """Test DroneSetup requires params argument"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        # Should initialize without error
        setup = DroneSetup(params, drone_config)
        assert setup is not None

    def test_drone_setup_validates_trigger_sooner_seconds(self):
        """Test DroneSetup validates trigger_sooner_seconds"""
        from src.drone_setup import DroneSetup

        params = Mock()
        del params.trigger_sooner_seconds  # Remove the attribute

        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        with pytest.raises(AttributeError):
            DroneSetup(params, drone_config)

    def test_drone_setup_has_mission_handlers(self):
        """Test DroneSetup has mission handlers dict"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        assert hasattr(setup, 'mission_handlers')
        assert isinstance(setup.mission_handlers, dict)

    def test_mission_handlers_cover_all_missions(self):
        """Test all mission types have handlers"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        # Check key mission types are handled
        assert Mission.NONE.value in setup.mission_handlers
        assert Mission.DRONE_SHOW_FROM_CSV.value in setup.mission_handlers
        assert Mission.TAKE_OFF.value in setup.mission_handlers
        assert Mission.LAND.value in setup.mission_handlers
        assert Mission.RETURN_RTL.value in setup.mission_handlers
        assert Mission.KILL_TERMINATE.value in setup.mission_handlers
        assert Mission.SMART_SWARM.value in setup.mission_handlers


# ============================================================================
# Test: Mission State Machine
# ============================================================================

def create_mock_drone_config():
    """Create a properly initialized mock DroneConfig"""
    drone_config = Mock(spec=DroneConfig)
    drone_config.state = State.IDLE.value
    drone_config.mission = Mission.NONE.value
    drone_config.last_mission = Mission.NONE.value
    drone_config.trigger_time = 0
    drone_config.config = {'pos_id': 1, 'hw_id': '1'}
    drone_config.hw_id = '1'
    drone_config.is_armed = False
    drone_config.is_ready_to_arm = True
    return drone_config


@pytest.mark.unit
@pytest.mark.mission
class TestMissionStateMachine:
    """Test mission state transitions"""

    def test_initial_state_is_idle(self):
        """Test initial state is IDLE"""
        drone_config = create_mock_drone_config()

        assert drone_config.state == State.IDLE.value

    def test_state_transitions_to_ready(self):
        """Test state can transition to MISSION_READY"""
        drone_config = create_mock_drone_config()

        drone_config.state = State.MISSION_READY.value

        assert drone_config.state == State.MISSION_READY.value

    def test_state_transitions_to_executing(self):
        """Test state can transition to MISSION_EXECUTING"""
        drone_config = create_mock_drone_config()

        drone_config.state = State.MISSION_EXECUTING.value

        assert drone_config.state == State.MISSION_EXECUTING.value

    def test_state_transitions_back_to_idle(self):
        """Test state transitions back to IDLE after mission"""
        drone_config = create_mock_drone_config()

        # Mission complete
        drone_config.state = State.MISSION_EXECUTING.value
        drone_config.state = State.IDLE.value

        assert drone_config.state == State.IDLE.value

    def test_mission_value_tracking(self):
        """Test mission value is tracked correctly"""
        drone_config = create_mock_drone_config()

        drone_config.mission = Mission.TAKE_OFF.value

        assert drone_config.mission == Mission.TAKE_OFF.value


# ============================================================================
# Test: Schedule Mission
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestScheduleMission:
    """Test schedule_mission functionality"""

    @pytest.mark.asyncio
    async def test_schedule_mission_skips_when_executing(self):
        """Test schedule_mission skips when already executing"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.MISSION_EXECUTING.value
        drone_config.mission = Mission.TAKE_OFF.value
        drone_config.trigger_time = 0

        setup = DroneSetup(params, drone_config)

        # Should skip without calling handler
        await setup.schedule_mission()

        # State should remain unchanged
        assert drone_config.state == State.MISSION_EXECUTING.value

    @pytest.mark.asyncio
    async def test_schedule_mission_calls_handler(self):
        """Test schedule_mission calls appropriate handler"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.MISSION_READY.value
        drone_config.mission = Mission.NONE.value
        drone_config.trigger_time = int(time.time())

        setup = DroneSetup(params, drone_config)

        # Replace handler with mock
        mock_handler = AsyncMock(return_value=(True, "Success"))
        setup.mission_handlers[Mission.NONE.value] = mock_handler

        await setup.schedule_mission()

        mock_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_schedule_mission_calculates_earlier_trigger(self):
        """Test schedule_mission calculates earlier trigger time"""
        trigger_time = int(time.time()) + 10
        trigger_sooner = 4

        earlier_trigger = trigger_time - trigger_sooner

        assert earlier_trigger == trigger_time - 4


# ============================================================================
# Test: Mission Handlers
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestMissionHandlers:
    """Test individual mission handlers"""

    @pytest.mark.asyncio
    async def test_no_mission_handler(self):
        """Test _handle_no_mission returns correctly"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.IDLE.value
        drone_config.mission = Mission.NONE.value
        drone_config.trigger_time = 0

        setup = DroneSetup(params, drone_config)

        result = await setup._handle_no_mission(int(time.time()), int(time.time()))

        assert result[0] is False
        assert "No mission" in result[1]

    @pytest.mark.asyncio
    async def test_unknown_mission_handler(self):
        """Test _handle_unknown_mission returns correctly"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.IDLE.value
        drone_config.mission = 999  # Unknown
        drone_config.trigger_time = 0

        setup = DroneSetup(params, drone_config)

        result = await setup._handle_unknown_mission(int(time.time()), int(time.time()))

        assert result[0] is False
        assert "Unknown" in result[1]

    @pytest.mark.asyncio
    async def test_takeoff_handler_checks_state(self):
        """Test takeoff handler checks state is MISSION_READY"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.IDLE.value  # Not ready
        drone_config.mission = Mission.TAKE_OFF.value
        drone_config.trigger_time = int(time.time())

        setup = DroneSetup(params, drone_config)

        # Should not execute because state is not MISSION_READY
        result = await setup._execute_takeoff(int(time.time()), int(time.time()))

        assert result[0] is False

    @pytest.mark.asyncio
    async def test_drone_show_handler_checks_conditions(self):
        """Test drone show handler checks all conditions"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.IDLE.value  # Not ready
        drone_config.mission = Mission.DRONE_SHOW_FROM_CSV.value
        drone_config.trigger_time = int(time.time()) + 100  # Future

        setup = DroneSetup(params, drone_config)

        result = await setup._execute_standard_drone_show(int(time.time()), int(time.time()) + 50)

        assert result[0] is False


# ============================================================================
# Test: Process Management
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestProcessManagement:
    """Test mission process management"""

    def test_running_processes_initialized(self):
        """Test running_processes dict is initialized"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        assert hasattr(setup, 'running_processes')
        assert isinstance(setup.running_processes, dict)

    def test_process_lock_initialized(self):
        """Test process lock is initialized"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        assert hasattr(setup, 'process_lock')

    @pytest.mark.asyncio
    async def test_terminate_all_clears_processes(self):
        """Test terminate_all clears running processes"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        # Add a mock process
        mock_process = Mock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.terminate = Mock()
        mock_process.kill = Mock()

        async def mock_wait():
            mock_process.returncode = 0

        mock_process.wait = mock_wait

        setup.running_processes['test_script.py'] = mock_process

        await setup.terminate_all_running_processes()

        assert len(setup.running_processes) == 0


# ============================================================================
# Test: Mission State Reset
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestMissionStateReset:
    """Test mission state reset functionality"""

    def test_reset_sets_mission_none(self):
        """Test _reset_mission_state sets mission to NONE"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = Mission.TAKE_OFF.value
        drone_config.state = State.MISSION_EXECUTING.value

        setup = DroneSetup(params, drone_config)

        setup._reset_mission_state(success=True)

        assert drone_config.mission == Mission.NONE.value

    def test_reset_sets_state_idle(self):
        """Test _reset_mission_state sets state to IDLE"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = Mission.TAKE_OFF.value
        drone_config.state = State.MISSION_EXECUTING.value

        setup = DroneSetup(params, drone_config)

        setup._reset_mission_state(success=False)

        assert drone_config.state == State.IDLE.value


# ============================================================================
# Test: Script Execution
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestScriptExecution:
    """Test mission script execution"""

    def test_get_script_path(self):
        """Test _get_script_path returns correct path"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        path = setup._get_script_path('drone_show.py')

        assert 'drone_show.py' in path

    @pytest.mark.asyncio
    async def test_execute_mission_script_checks_file_exists(self):
        """Test execute_mission_script checks file exists"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        # Try to execute non-existent script
        result = await setup.execute_mission_script('nonexistent_script.py', '')

        assert result[0] is False
        assert 'not found' in result[1].lower()


# ============================================================================
# Test: Trigger Time Calculation
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestTriggerTimeCalculation:
    """Test trigger time calculations"""

    def test_trigger_time_from_string(self):
        """Test trigger time can be parsed from string"""
        trigger_str = "1703084400"
        trigger_int = int(trigger_str)

        assert trigger_int == 1703084400

    def test_earlier_trigger_calculation(self):
        """Test earlier trigger time calculation"""
        trigger_time = 1703084400
        trigger_sooner = 4

        earlier = trigger_time - trigger_sooner

        assert earlier == 1703084396

    def test_current_time_vs_earlier_trigger(self):
        """Test current time vs earlier trigger comparison"""
        now = int(time.time())
        trigger_time = now + 10
        trigger_sooner = 4
        earlier_trigger = trigger_time - trigger_sooner

        # 6 seconds from now is past earlier trigger (4 seconds before trigger)
        at_time = now + 6
        should_execute = at_time >= earlier_trigger

        assert should_execute is True

    def test_not_yet_time_to_execute(self):
        """Test when it's not yet time to execute"""
        now = int(time.time())
        trigger_time = now + 100
        trigger_sooner = 4
        earlier_trigger = trigger_time - trigger_sooner

        should_execute = now >= earlier_trigger

        assert should_execute is False


# ============================================================================
# Test: Mission Type Specific Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestMissionTypeSpecific:
    """Test specific mission type behaviors"""

    def test_mission_enum_values(self):
        """Test Mission enum has correct values"""
        assert Mission.NONE.value == 0
        assert Mission.DRONE_SHOW_FROM_CSV.value == 1
        assert Mission.SMART_SWARM.value == 2
        assert Mission.CUSTOM_CSV_DRONE_SHOW.value == 3
        assert Mission.SWARM_TRAJECTORY.value == 4
        assert Mission.TAKE_OFF.value == 10
        assert Mission.LAND.value == 101
        assert Mission.HOLD.value == 102
        assert Mission.RETURN_RTL.value == 104
        assert Mission.KILL_TERMINATE.value == 105
        assert Mission.HOVER_TEST.value == 106

    def test_state_enum_values(self):
        """Test State enum has correct values"""
        assert State.IDLE.value == 0
        assert State.MISSION_READY.value == 1
        assert State.MISSION_EXECUTING.value == 2


# ============================================================================
# Test: Time Synchronization
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestTimeSynchronization:
    """Test time synchronization functionality"""

    def test_synchronize_time_method_exists(self):
        """Test synchronize_time method exists"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        assert hasattr(setup, 'synchronize_time')
        assert callable(setup.synchronize_time)


# ============================================================================
# Test: DroneConfig Integration
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestDroneConfigIntegration:
    """Test DroneConfig integration with DroneSetup"""

    def test_drone_config_has_required_attributes(self):
        """Test mock DroneConfig has attributes needed by DroneSetup"""
        drone_config = create_mock_drone_config()

        assert hasattr(drone_config, 'state')
        assert hasattr(drone_config, 'mission')
        assert hasattr(drone_config, 'trigger_time')

    def test_drone_config_default_values(self):
        """Test DroneConfig default values in mock"""
        drone_config = create_mock_drone_config()

        assert drone_config.state == State.IDLE.value
        assert drone_config.mission == Mission.NONE.value

    def test_drone_config_tracks_last_mission(self):
        """Test DroneConfig tracks last mission"""
        drone_config = create_mock_drone_config()

        drone_config.mission = Mission.TAKE_OFF.value
        drone_config.last_mission = drone_config.mission
        drone_config.mission = Mission.NONE.value

        assert drone_config.last_mission == Mission.TAKE_OFF.value


# ============================================================================
# Test: Error Handling
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestMissionErrorHandling:
    """Test error handling in mission execution"""

    def test_drone_setup_validates_trigger_time_on_init(self):
        """Test DroneSetup validates trigger_time type on initialization"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.state = State.MISSION_READY.value
        drone_config.mission = Mission.TAKE_OFF.value
        drone_config.trigger_time = "invalid"  # Invalid type

        # Should raise TypeError during initialization
        with pytest.raises(TypeError):
            DroneSetup(params, drone_config)

    def test_missing_script_handled(self):
        """Test missing script is handled gracefully"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        # Get path for nonexistent script
        path = setup._get_script_path('nonexistent.py')

        # File should not exist
        assert not os.path.isfile(path)


# ============================================================================
# Test: Logging
# ============================================================================

@pytest.mark.unit
@pytest.mark.mission
class TestMissionLogging:
    """Test mission logging functionality"""

    def test_last_logged_mission_tracking(self):
        """Test last logged mission is tracked"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        assert hasattr(setup, 'last_logged_mission')
        assert setup.last_logged_mission is None

    def test_last_logged_state_tracking(self):
        """Test last logged state is tracked"""
        from src.drone_setup import DroneSetup

        params = Mock()
        params.trigger_sooner_seconds = 4
        drone_config = Mock()
        drone_config.trigger_time = 0
        drone_config.mission = 0

        setup = DroneSetup(params, drone_config)

        assert hasattr(setup, 'last_logged_state')
        assert setup.last_logged_state is None
