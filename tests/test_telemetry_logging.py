import logging
import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gcs-server'))

import telemetry


@pytest.mark.unit
@pytest.mark.telemetry
class TestTelemetryLoggingCompatibility:
    """Telemetry should use the standard logger interface instead of legacy logger methods."""

    def test_initialize_telemetry_tracking_uses_standard_logger_interface(self):
        mock_logger = Mock()

        with patch('telemetry.get_logger', return_value=mock_logger):
            telemetry.initialize_telemetry_tracking([{'hw_id': '1'}, {'hw_id': '2'}])

        mock_logger.log.assert_called_once()
        level, message = mock_logger.log.call_args.args[:2]
        assert level == logging.INFO
        assert "Initialized telemetry tracking for 2 drones" in message

    def test_log_drone_telemetry_event_adds_drone_id_metadata(self):
        with patch.object(telemetry, 'logger') as mock_logger:
            telemetry._log_drone_telemetry_event(
                '7',
                False,
                {'error': 'Connection timeout after 5s', 'consecutive_errors': 3},
            )

        level, message = mock_logger.log.call_args.args[:2]
        assert level == logging.WARNING
        assert "Connection timeout after 5s" in message
        assert mock_logger.log.call_args.kwargs['extra']['mds_drone_id'] == '7'
