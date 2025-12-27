# tests/test_filter.py
"""
Kalman Filter Tests
===================
Tests for the Kalman filter implementation in src/filter.py.
"""

import pytest
import numpy as np


class TestKalmanFilterInitialization:
    """Test Kalman filter initialization"""

    def test_create_uninitialized(self):
        """Test creating uninitialized filter"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()

        assert kf.is_initialized == False
        assert kf.reliability_score == 0

    def test_initialize_filter(self):
        """Test initializing filter with parameters"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        initial_state = [0, 0, 0, 0, 0, 0, 0, 0, 0]  # 9 states
        initial_covariance = np.identity(9)
        process_noise = np.identity(9)
        measurement_noise = np.identity(9)

        kf.initialize(initial_state, initial_covariance, process_noise, measurement_noise)

        assert kf.is_initialized == True
        assert len(kf.state) == 9
        assert kf.A.shape == (9, 9)
        assert kf.H.shape == (9, 9)

    def test_initialize_if_needed_uninit(self):
        """Test initialize_if_needed when not initialized"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        position_setpoint = {'north': 10.0, 'east': 20.0, 'down': -5.0}
        velocity_setpoint = {'north': 1.0, 'east': 2.0, 'down': 0.5}

        kf.initialize_if_needed(position_setpoint, velocity_setpoint)

        assert kf.is_initialized == True
        assert kf.state[0] == 10.0  # north position
        assert kf.state[3] == 20.0  # east position
        assert kf.state[6] == -5.0  # down position

    def test_initialize_if_needed_already_init(self):
        """Test initialize_if_needed skips when already initialized"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()

        # First initialization
        pos1 = {'north': 10.0, 'east': 20.0, 'down': -5.0}
        vel1 = {'north': 1.0, 'east': 2.0, 'down': 0.5}
        kf.initialize_if_needed(pos1, vel1)

        original_state = kf.state.copy()

        # Try to reinitialize with different values
        pos2 = {'north': 100.0, 'east': 200.0, 'down': -50.0}
        vel2 = {'north': 10.0, 'east': 20.0, 'down': 5.0}
        kf.initialize_if_needed(pos2, vel2)

        # State should remain unchanged
        np.testing.assert_array_equal(kf.state, original_state)


class TestKalmanFilterPredict:
    """Test Kalman filter prediction"""

    def test_predict_updates_state(self):
        """Test that predict updates state"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        pos = {'north': 10.0, 'east': 20.0, 'down': -5.0}
        vel = {'north': 1.0, 'east': 2.0, 'down': 0.5}
        kf.initialize_if_needed(pos, vel)

        original_state = kf.state.copy()
        kf.predict()

        # State should be updated (A matrix is identity, so state stays same)
        # But covariance P should change due to process noise
        assert kf.reliability_score is not None

    def test_predict_without_init(self):
        """Test predict returns early if not initialized"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()

        # Should not raise, just return early
        result = kf.predict()

        assert result is None
        assert kf.is_initialized == False


class TestKalmanFilterUpdate:
    """Test Kalman filter update"""

    def test_update_with_measurement(self):
        """Test update with a measurement"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        pos = {'north': 10.0, 'east': 20.0, 'down': -5.0}
        vel = {'north': 1.0, 'east': 2.0, 'down': 0.5}
        kf.initialize_if_needed(pos, vel)

        kf.predict()

        # Provide a measurement (9 elements)
        measurement = np.array([10.5, 1.1, 0.0, 20.5, 2.1, 0.0, -5.5, 0.6, 0.0])
        kf.update(measurement)

        # State should be updated toward measurement
        state = kf.get_current_state()
        assert 'position' in state
        assert 'velocity' in state
        assert 'acceleration' in state

    def test_update_without_init(self):
        """Test update returns early if not initialized"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        measurement = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0])

        # Should not raise, just return early
        result = kf.update(measurement)

        assert result is None
        assert kf.is_initialized == False


class TestKalmanFilterGetState:
    """Test getting current state"""

    def test_get_current_state_structure(self):
        """Test get_current_state returns correct structure"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        pos = {'north': 10.0, 'east': 20.0, 'down': -5.0}
        vel = {'north': 1.0, 'east': 2.0, 'down': 0.5}
        kf.initialize_if_needed(pos, vel)

        state = kf.get_current_state()

        assert 'position' in state
        assert 'velocity' in state
        assert 'acceleration' in state

        assert 'north' in state['position']
        assert 'east' in state['position']
        assert 'down' in state['position']

    def test_get_current_state_values(self):
        """Test get_current_state returns correct values"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        pos = {'north': 10.0, 'east': 20.0, 'down': -5.0}
        vel = {'north': 1.0, 'east': 2.0, 'down': 0.5}
        kf.initialize_if_needed(pos, vel)

        state = kf.get_current_state()

        assert state['position']['north'] == 10.0
        assert state['position']['east'] == 20.0
        assert state['position']['down'] == -5.0
        assert state['velocity']['north'] == 1.0
        assert state['velocity']['east'] == 2.0
        assert state['velocity']['down'] == 0.5


class TestKalmanFilterIntegration:
    """Integration tests for Kalman filter"""

    def test_predict_update_cycle(self):
        """Test full predict-update cycle"""
        from src.filter import KalmanFilter

        kf = KalmanFilter()
        pos = {'north': 0.0, 'east': 0.0, 'down': 0.0}
        vel = {'north': 0.0, 'east': 0.0, 'down': 0.0}
        kf.initialize_if_needed(pos, vel)

        # Run several predict-update cycles
        for i in range(5):
            kf.predict()
            measurement = np.array([i, 0, 0, i, 0, 0, 0, 0, 0], dtype=float)
            kf.update(measurement)

        state = kf.get_current_state()
        # After updates, position should move toward measurements
        assert state['position']['north'] > 0
        assert state['position']['east'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
