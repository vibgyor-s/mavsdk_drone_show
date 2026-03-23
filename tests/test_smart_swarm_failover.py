from smart_swarm_src.failover import choose_leader_loss_response


def test_upstream_or_hold_promotes_to_upstream_leader():
    swarm_config = {
        "1": {"follow": 0},
        "2": {"follow": 1},
        "3": {"follow": 2},
    }

    result = choose_leader_loss_response(
        self_hw_id=3,
        current_leader_hw_id=2,
        swarm_config=swarm_config,
        strategy="upstream_or_hold",
    )

    assert result["action"] == "follow"
    assert result["leader_hw_id"] == "1"
    assert "upstream leader" in result["reason"]


def test_upstream_or_hold_self_holds_when_top_leader_is_lost():
    swarm_config = {
        "1": {"follow": 0},
        "2": {"follow": 1},
    }

    result = choose_leader_loss_response(
        self_hw_id=2,
        current_leader_hw_id=1,
        swarm_config=swarm_config,
        strategy="upstream_or_hold",
    )

    assert result["action"] == "self_hold"
    assert result["leader_hw_id"] is None


def test_next_hw_id_strategy_remains_available_for_legacy_behavior():
    swarm_config = {
        "1": {"follow": 0},
        "2": {"follow": 0},
        "3": {"follow": 1},
    }

    result = choose_leader_loss_response(
        self_hw_id=3,
        current_leader_hw_id=1,
        swarm_config=swarm_config,
        strategy="next_hw_id",
    )

    assert result["action"] == "follow"
    assert result["leader_hw_id"] == "2"


def test_hold_strategy_self_holds_immediately():
    swarm_config = {
        "1": {"follow": 0},
        "2": {"follow": 1},
    }

    result = choose_leader_loss_response(
        self_hw_id=2,
        current_leader_hw_id=1,
        swarm_config=swarm_config,
        strategy="hold",
    )

    assert result["action"] == "self_hold"
    assert result["leader_hw_id"] is None


def test_upstream_or_hold_rejects_cycle_candidate_and_self_holds():
    swarm_config = {
        "1": {"follow": 3},
        "2": {"follow": 1},
        "3": {"follow": 2},
    }

    result = choose_leader_loss_response(
        self_hw_id=3,
        current_leader_hw_id=2,
        swarm_config=swarm_config,
        strategy="upstream_or_hold",
    )

    assert result["action"] == "self_hold"
    assert result["leader_hw_id"] is None
