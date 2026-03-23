from tools.validate_smart_swarm_runtime import _is_idle_baseline_row, _is_idle_reset_row


def test_idle_baseline_requires_ready_disarmed_idle_and_home():
    row = {
        "update_time": 1774290000,
        "is_ready_to_arm": True,
        "readiness_status": "ready",
        "is_armed": False,
        "mission": 0,
        "state": 0,
        "home_position_set": True,
    }

    assert _is_idle_baseline_row(row) is True


def test_idle_baseline_rejects_airborne_or_missing_home():
    assert _is_idle_baseline_row({
        "update_time": 1774290000,
        "is_ready_to_arm": True,
        "readiness_status": "ready",
        "is_armed": True,
        "mission": 0,
        "state": 0,
        "home_position_set": True,
    }) is False

    assert _is_idle_baseline_row({
        "update_time": 1774290000,
        "is_ready_to_arm": True,
        "readiness_status": "ready",
        "is_armed": False,
        "mission": 0,
        "state": 0,
        "home_position_set": False,
    }) is False


def test_idle_reset_requires_disarmed_mission_and_state_clear():
    assert _is_idle_reset_row({
        "is_armed": False,
        "mission": 0,
        "state": 0,
    }) is True

    assert _is_idle_reset_row({
        "is_armed": False,
        "mission": 101,
        "state": 2,
    }) is False
