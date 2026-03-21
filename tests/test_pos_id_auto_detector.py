import logging
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.pos_id_auto_detector import PosIDAutoDetector


def _build_detector(*, detected_pos_id=0, pos_id=1, max_deviation=1.5):
    drone_config = SimpleNamespace(
        position={"lat": 35.0, "long": 51.0, "alt": 100.0},
        all_configs={
            1: {"x": 0.0, "y": 0.0},
            2: {"x": 5.0, "y": 0.0},
        },
        detected_pos_id=detected_pos_id,
        pos_id=pos_id,
    )
    params = SimpleNamespace(
        auto_detection_enabled=True,
        auto_detection_interval=1.0,
        max_deviation=max_deviation,
    )
    api_server = Mock()
    api_server._get_origin_from_gcs.return_value = {"lat": 35.0, "lon": 51.0}
    detector = PosIDAutoDetector(drone_config, params, api_server)
    return detector, drone_config


def test_detect_pos_id_suppresses_startup_warning_until_detection_stabilizes(caplog):
    detector, drone_config = _build_detector(detected_pos_id=0)

    with patch("src.pos_id_auto_detector.navpy.lla2ned", return_value=(50.0, 0.0, 0.0)):
        with caplog.at_level(logging.INFO, logger="PosIDAutoDetector"):
            detector.detect_pos_id()

    assert drone_config.detected_pos_id == 0
    assert "waiting for stable position" in caplog.text
    assert "does not match configured pos_id" not in caplog.text
    assert "Lost confident pos_id detection" not in caplog.text


def test_detect_pos_id_warns_when_confident_detection_is_lost(caplog):
    detector, drone_config = _build_detector(detected_pos_id=2)

    with patch("src.pos_id_auto_detector.navpy.lla2ned", return_value=(50.0, 0.0, 0.0)):
        with caplog.at_level(logging.INFO, logger="PosIDAutoDetector"):
            detector.detect_pos_id()

    assert drone_config.detected_pos_id == 0
    assert "Lost confident pos_id detection" in caplog.text


def test_detect_pos_id_warns_on_confident_mismatch(caplog):
    detector, drone_config = _build_detector(detected_pos_id=0, pos_id=1)

    with patch("src.pos_id_auto_detector.navpy.lla2ned", return_value=(5.0, 0.0, 0.0)):
        with caplog.at_level(logging.INFO, logger="PosIDAutoDetector"):
            detector.detect_pos_id()

    assert drone_config.detected_pos_id == 2
    assert "Detected pos_id (2) does not match configured pos_id (1)." in caplog.text
