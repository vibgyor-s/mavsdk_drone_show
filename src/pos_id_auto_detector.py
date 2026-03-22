import threading
import time
import logging
import math
import navpy

class PosIDAutoDetector:
    """
    Handles the automatic detection of pos_id based on the drone's current position.
    """

    def __init__(self, drone_config, params, api_server):
        """
        Initialize the PosIDAutoDetector.

        :param drone_config: Configuration object for the drone.
        :param params: Parameters object containing settings.
        :param api_server: API server for communication with the Ground Control Station (GCS).
        """
        self.drone_config = drone_config
        self.params = params
        self.api_server = api_server
        self.running_event = threading.Event()
        self.thread = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._repeat_log_interval = max(60.0, float(self.params.auto_detection_interval) * 20.0)
        self._last_issue_key = None
        self._last_issue_logged_at = 0.0
        self._last_mismatch_pos_id = None

    def start(self):
        """
        Start the auto-detection thread.
        """
        if not self.params.auto_detection_enabled:
            self.logger.info("PosIDAutoDetector is disabled via parameters.")
            return

        if self.running_event.is_set():
            self.logger.warning("PosIDAutoDetector is already running.")
            return

        self.running_event.set()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.logger.info("PosIDAutoDetector started.")

    def stop(self):
        """
        Stop the auto-detection thread.
        """
        if not self.running_event.is_set():
            self.logger.warning("PosIDAutoDetector is not running.")
            return

        self.running_event.clear()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        self.logger.info("PosIDAutoDetector stopped.")

    def _run(self):
        """
        Main loop for auto-detection.
        """
        self.logger.debug("PosIDAutoDetector thread running.")
        while self.running_event.is_set():
            try:
                self.detect_pos_id()
            except Exception as e:
                self.logger.error(f"Error in PosIDAutoDetector: {e}", exc_info=True)
            time.sleep(self.params.auto_detection_interval)

    def detect_pos_id(self):
        """
        Perform the pos_id detection logic.
        """
        self.logger.debug("Starting pos_id detection process.")

        # Fetch origin from GCS
        origin = self.api_server._get_origin_from_gcs()
        if not origin:
            self._log_issue("origin_unavailable", logging.WARNING, "Origin data unavailable. Skipping pos_id detection.")
            return

        origin_lat = origin.get('lat')
        origin_lon = origin.get('lon')
        origin_alt = self.drone_config.position.get('alt', 0)

        # Validate origin coordinates
        if not self._validate_coordinates(origin_lat, origin_lon):
            self._log_issue("invalid_origin", logging.WARNING, "Invalid origin coordinates. Skipping pos_id detection.")
            return

        # Get drone's current position
        drone_lat = self.drone_config.position.get('lat', 0)
        drone_lon = self.drone_config.position.get('long', 0)
        drone_alt = self.drone_config.position.get('alt', 0)

        # Validate drone coordinates
        if not self._validate_coordinates(drone_lat, drone_lon):
            self._log_issue("invalid_gps", logging.WARNING, "Invalid drone GPS data. Skipping pos_id detection.")
            return

        # Convert global coordinates to local NED
        try:
            # Using navpy to compute NED coordinates
            n, e, d = navpy.lla2ned(
                drone_lat,
                drone_lon,
                drone_alt,
                origin_lat,
                origin_lon,
                origin_alt,
                latlon_unit='deg',
                alt_unit='m',
                model='wgs84'
            )
            x = n  # North
            y = e  # East
            self.logger.debug(f"Computed local NED offsets: x={x:.2f}, y={y:.2f}")
        except Exception as e:
            self._log_issue("coordinate_conversion_failed", logging.ERROR, f"Error converting coordinates: {e}")
            self.logger.error(f"Error converting coordinates: {e}", exc_info=True)
            return

        # Find the closest (x, y) in all_configs
        min_distance = float('inf')
        best_pos_id = 0  # Default to 0 indicating failure
        for pos_id, coords in self.drone_config.all_configs.items():
            if 'x' not in coords or 'y' not in coords:
                # Skip if coordinates are missing in config for this drone
                self._log_issue(
                    f"missing_coords:{pos_id}",
                    logging.WARNING,
                    f"Missing coordinates for pos_id {pos_id}. Skipping.",
                )
                continue

            dx = x - coords['x']
            dy = y - coords['y']
            distance = math.sqrt(dx**2 + dy**2)
            self.logger.debug(f"Comparing with pos_id={pos_id}: distance={distance:.2f}")
            if distance < min_distance:
                min_distance = distance
                best_pos_id = pos_id

        previous_detected_pos_id = self.drone_config.detected_pos_id

        # Check if the distance is within the maximum allowed deviation
        if min_distance > self.params.max_deviation:
            best_pos_id = 0  # Indicate failure
            if previous_detected_pos_id:
                self.logger.warning(
                    f"Lost confident pos_id detection; minimum distance {min_distance:.2f} "
                    f"exceeds max_deviation {self.params.max_deviation}. "
                    f"Clearing detected_pos_id from {previous_detected_pos_id} to 0."
                )
            else:
                self._log_issue(
                    "waiting_for_stable_position",
                    logging.INFO,
                    f"PosID detection waiting for stable position; minimum distance "
                    f"{min_distance:.2f} exceeds max_deviation {self.params.max_deviation}.",
                )
            self._last_mismatch_pos_id = None
        else:
            self._clear_issue()

        # Update detected_pos_id
        self.drone_config.detected_pos_id = best_pos_id
        self.logger.debug(f"Updated detected_pos_id from {previous_detected_pos_id} to {best_pos_id}.")

        if best_pos_id and best_pos_id != previous_detected_pos_id:
            if previous_detected_pos_id:
                self.logger.warning(
                    f"Confident pos_id detection changed from {previous_detected_pos_id} "
                    f"to {best_pos_id} (distance {min_distance:.2f} meters)."
                )
            else:
                self.logger.info(
                    f"Confident pos_id detection established: {best_pos_id} "
                    f"(distance {min_distance:.2f} meters)."
                )

        # Warn only on confident, non-zero mismatches.
        if best_pos_id and best_pos_id != self.drone_config.pos_id:
            if self._last_mismatch_pos_id != best_pos_id:
                self.logger.warning(
                    f"Detected pos_id ({best_pos_id}) does not match configured pos_id "
                    f"({self.drone_config.pos_id})."
                )
            self._last_mismatch_pos_id = best_pos_id
        elif self._last_mismatch_pos_id is not None and best_pos_id == self.drone_config.pos_id:
            self.logger.info(
                f"Detected pos_id realigned with configured pos_id ({self.drone_config.pos_id})."
            )
            self._last_mismatch_pos_id = None

    def _log_issue(self, issue_key, level, message):
        now = time.monotonic()
        if issue_key != self._last_issue_key or (now - self._last_issue_logged_at) >= self._repeat_log_interval:
            self.logger.log(level, message)
            self._last_issue_key = issue_key
            self._last_issue_logged_at = now

    def _clear_issue(self):
        self._last_issue_key = None
        self._last_issue_logged_at = 0.0

    def _validate_coordinates(self, lat, lon):
        """
        Validate latitude and longitude values.

        :param lat: Latitude value to validate.
        :param lon: Longitude value to validate.
        :return: True if both latitude and longitude are valid, False otherwise.
        """
        if lat is None or lon is None:
            return False
        if not (-90 <= lat <= 90):
            return False
        if not (-180 <= lon <= 180):
            return False
        return True
