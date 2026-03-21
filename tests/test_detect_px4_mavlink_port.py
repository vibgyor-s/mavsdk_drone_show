"""
Tests for PX4 SITL MAVLink port detection.
"""

import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "multiple_sitl" / "detect_px4_mavlink_port.py"
SPEC = importlib.util.spec_from_file_location("detect_px4_mavlink_port", MODULE_PATH)
detector = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(detector)

EXCLUDED_PORTS = [12550, 14540, 14569, 24550]


class TestDetectPx4MavlinkPort:
    """Unit tests for the detector parsing logic."""

    def test_extract_ports_from_ss_output(self):
        output = "\n".join([
            'UNCONN 0 0 127.0.0.1:18570 127.0.0.1:14550 users:(("px4",pid=123,fd=42))',
            'UNCONN 0 0 127.0.0.1:18580 127.0.0.1:14540 users:(("px4",pid=123,fd=43))',
            'UNCONN 0 0 127.0.0.1:14569 127.0.0.1:14550 users:(("mavlink-routerd",pid=456,fd=7))',
        ])

        assert detector.extract_ports_from_ss_output(output, EXCLUDED_PORTS) == [14550]

    def test_extract_ports_from_log(self):
        log_text = (
            "INFO [mavlink] mode: Normal, data rate: 4000000 B/s "
            "on udp port 18560 remote port 14560\n"
        )

        assert detector.extract_ports_from_log(log_text, EXCLUDED_PORTS) == [14560]

    def test_extract_ports_from_proc_net_output(self):
        proc_output = "\n".join([
            "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode",
            "  17: 0100007F:488A 0100007F:38D6 01 00000000:00000000 00:00000000 00000000     0        0 0 2 0000000000000000 0",
            "  18: 0100007F:488B 0100007F:38DC 01 00000000:00000000 00:00000000 00000000     0        0 0 2 0000000000000000 0",
        ])

        assert detector.extract_ports_from_proc_net_output(proc_output, EXCLUDED_PORTS) == [14550, 14556]

    def test_choose_port_prefers_modern_port_when_available(self):
        assert detector.choose_port([14560, 14550], 14550) == 14550

    def test_choose_port_uses_legacy_candidate_when_needed(self):
        assert detector.choose_port([14560], 14550) == 14560

    def test_detect_from_runtime_returns_detected_default_port(self):
        ss_output = 'UNCONN 0 0 127.0.0.1:18570 127.0.0.1:14550 users:(("px4",pid=123,fd=42))'

        with patch.object(detector.subprocess, "run", return_value=Mock(stdout=ss_output)):
            port = detector.detect_from_runtime(
                default_port=14550,
                timeout=0.1,
                poll_interval=0.01,
                sitl_log=None,
                excluded_ports=EXCLUDED_PORTS,
            )

        assert port == 14550

    def test_detect_from_runtime_falls_back_to_proc_net_when_ss_missing(self):
        proc_output = "\n".join([
            "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode",
            "  17: 0100007F:488A 0100007F:38D6 01 00000000:00000000 00:00000000 00000000     0        0 0 2 0000000000000000 0",
        ])

        with patch.object(detector.subprocess, "run", side_effect=FileNotFoundError("ss")), patch.object(
            detector,
            "_read_proc_net_candidates",
            return_value=detector.extract_ports_from_proc_net_output(proc_output, EXCLUDED_PORTS),
        ):
            port = detector.detect_from_runtime(
                default_port=14550,
                timeout=0.1,
                poll_interval=0.01,
                sitl_log=None,
                excluded_ports=EXCLUDED_PORTS,
            )

        assert port == 14550
