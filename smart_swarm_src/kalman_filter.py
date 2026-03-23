# smart_swarm_src/kalman_filter.py

import numpy as np
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise


class LeaderKalmanFilter:
    def __init__(self):
        """
        Initializes the Kalman filter for estimating the leader's state.
        """
        # State vector: [pos_n, pos_e, pos_d, vel_n, vel_e, vel_d]
        self.kf = KalmanFilter(dim_x=6, dim_z=6)
        self._initialize_filter()
        self.last_update_time = None

    def _initialize_filter(self):
        """
        Sets up the Kalman filter matrices.
        """
        # State transition matrix (will be updated with dt)
        self.kf.F = np.eye(6)

        # Measurement function: direct measurement of positions and velocities
        self.kf.H = np.eye(6)

        # Initial state covariance
        self.kf.P *= 10.0

        # Measurement noise covariance
        position_variance = 5.0  # Variance in position measurements (meters^2)
        velocity_variance = 1.0  # Variance in velocity measurements ((m/s)^2)
        self.kf.R = np.diag([position_variance]*3 + [velocity_variance]*3)

        # Process noise covariance (will be updated with dt)
        self.q_variance = 0.1  # Process noise variance
        self.kf.Q = np.eye(6)

        # Initial state
        self.kf.x = np.zeros((6, 1))

    def _set_dynamics(self, dt):
        """Update transition and process-noise matrices for grouped [pos, vel] state ordering."""
        self.kf.F = np.array([
            [1, 0, 0, dt, 0,  0],
            [0, 1, 0, 0,  dt, 0],
            [0, 0, 1, 0,  0,  dt],
            [0, 0, 0, 1,  0,  0],
            [0, 0, 0, 0,  1,  0],
            [0, 0, 0, 0,  0,  1],
        ])

        q = Q_discrete_white_noise(dim=2, dt=dt, var=self.q_variance)
        self.kf.Q = np.block([
            [np.eye(3) * q[0, 0], np.eye(3) * q[0, 1]],
            [np.eye(3) * q[1, 0], np.eye(3) * q[1, 1]],
        ])

    def reset(self):
        """
        Resets the Kalman filter to its initial state.
        """
        self._initialize_filter()
        self.last_update_time = None

    def predict(self, current_time):
        """
        Predicts the current state of the leader based on elapsed time since last update.

        Args:
            current_time (float): Current timestamp in seconds since epoch.

        Returns:
            np.ndarray: Predicted state vector [pos_n, pos_e, pos_d, vel_n, vel_e, vel_d].
        """
        if self.last_update_time is None:
            return self.kf.x.flatten()

        dt = max(0.0, current_time - self.last_update_time)
        self._set_dynamics(dt)
        if dt > 0.0:
            self.kf.predict()
            self.last_update_time = current_time
        return self.kf.x.flatten()

    def update(self, measurement, measurement_time):
        """
        Updates the Kalman filter with a new measurement if the timestamp has advanced.

        Args:
            measurement (dict): Measurement containing position and velocity.
                Expected keys: 'pos_n', 'pos_e', 'pos_d', 'vel_n', 'vel_e', 'vel_d'
            measurement_time (float): Timestamp of the measurement.

        Returns:
            None
        """
        if self.last_update_time is not None and measurement_time <= self.last_update_time:
            return

        z = np.array([
            measurement['pos_n'],
            measurement['pos_e'],
            measurement['pos_d'],
            measurement['vel_n'],
            measurement['vel_e'],
            measurement['vel_d']
        ]).reshape(6, 1)

        if self.last_update_time is None:
            self.kf.x = z
            self.last_update_time = measurement_time
            return

        dt = max(0.0, measurement_time - self.last_update_time)
        self._set_dynamics(dt)
        if dt > 0.0:
            self.kf.predict()
        self.kf.update(z)
        self.last_update_time = measurement_time

    def get_state(self):
        """
        Returns the current estimated state.

        Returns:
            dict: Estimated state with keys 'pos_n', 'pos_e', 'pos_d', 'vel_n', 'vel_e', 'vel_d'
        """
        state = self.kf.x.flatten()
        return {
            'pos_n': state[0],
            'pos_e': state[1],
            'pos_d': state[2],
            'vel_n': state[3],
            'vel_e': state[4],
            'vel_d': state[5]
        }
