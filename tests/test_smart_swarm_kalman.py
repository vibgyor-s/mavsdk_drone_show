import numpy as np
import pytest

pytest.importorskip("filterpy")

from smart_swarm_src.kalman_filter import LeaderKalmanFilter


def _measurement(**overrides):
    measurement = {
        "pos_n": 0.0,
        "pos_e": 0.0,
        "pos_d": 0.0,
        "vel_n": 0.0,
        "vel_e": 0.0,
        "vel_d": 0.0,
    }
    measurement.update(overrides)
    return measurement


def test_predict_advances_only_incremental_elapsed_time():
    kalman = LeaderKalmanFilter()
    kalman.update(_measurement(vel_n=1.0), measurement_time=10.0)

    first = kalman.predict(11.0)
    second = kalman.predict(12.0)

    assert first[0] == pytest.approx(1.0)
    assert second[0] == pytest.approx(2.0)


def test_process_noise_matches_grouped_position_velocity_state_layout():
    kalman = LeaderKalmanFilter()
    kalman.update(_measurement(), measurement_time=5.0)
    kalman.predict(7.0)

    dt = 2.0
    q = kalman.q_variance * np.array([
        [0.25 * dt**4, 0.5 * dt**3],
        [0.5 * dt**3, dt**2],
    ])
    expected = np.block([
        [np.eye(3) * q[0, 0], np.eye(3) * q[0, 1]],
        [np.eye(3) * q[1, 0], np.eye(3) * q[1, 1]],
    ])

    assert np.allclose(kalman.kf.Q, expected)
    assert kalman.kf.Q[0, 1] == pytest.approx(0.0)
    assert kalman.kf.Q[0, 3] == pytest.approx(q[0, 1])
