import numpy as np
import pytest

from smart_swarm_src.pd_controller import PDController


def test_pd_controller_applies_velocity_feedforward():
    controller = PDController(kp=0.5, kd=0.1, max_velocity=10.0)

    command = controller.compute(
        np.array([0.0, 0.0, 0.0]),
        dt=0.1,
        velocity_feedforward=np.array([1.0, -2.0, 0.5]),
    )

    assert np.allclose(command, np.array([1.0, -2.0, 0.5]))


def test_pd_controller_saturates_combined_pd_and_feedforward():
    controller = PDController(kp=1.0, kd=0.0, max_velocity=3.0)

    command = controller.compute(
        np.array([10.0, 0.0, 0.0]),
        dt=1.0,
        velocity_feedforward=np.array([2.0, 0.0, 0.0]),
    )

    assert np.linalg.norm(command) == pytest.approx(3.0)
    assert command[0] == pytest.approx(3.0)
    assert command[1] == pytest.approx(0.0)
    assert command[2] == pytest.approx(0.0)
