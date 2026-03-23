from __future__ import annotations

from typing import Any, Mapping


def normalize_hw_id(hw_id: Any) -> str | None:
    """Normalize a hardware ID to a positive string key."""
    try:
        normalized = int(hw_id)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
        return None
    return str(normalized)


def _would_create_cycle(
    self_hw_id: str | None,
    candidate_leader_hw_id: str | None,
    swarm_config: Mapping[str, Mapping[str, Any]] | None,
) -> bool:
    """Check whether following a candidate leader would create a follow-chain loop."""
    if self_hw_id is None or candidate_leader_hw_id is None:
        return False

    assignments = swarm_config or {}
    current = candidate_leader_hw_id
    visited = {self_hw_id}

    while current is not None:
        if current in visited:
            return True
        visited.add(current)

        leader_assignment = assignments.get(current)
        if leader_assignment is None:
            return False

        current = normalize_hw_id(leader_assignment.get("follow"))

    return False


def choose_leader_loss_response(
    self_hw_id: Any,
    current_leader_hw_id: Any,
    swarm_config: Mapping[str, Mapping[str, Any]] | None,
    strategy: str = "upstream_or_hold",
) -> dict[str, str | None]:
    """
    Resolve follower behavior after its current leader becomes unreachable.

    Supported strategies:
    - upstream_or_hold: follow the failed leader's upstream leader if available,
      otherwise self-promote and hold.
    - next_hw_id: legacy deterministic fallback based on sorted hw_id order.
    - hold: immediately self-promote and hold.
    """
    normalized_self = normalize_hw_id(self_hw_id)
    normalized_leader = normalize_hw_id(current_leader_hw_id)
    normalized_strategy = str(strategy or "upstream_or_hold").strip().lower()

    if normalized_strategy == "hold":
        return {
            "action": "self_hold",
            "leader_hw_id": None,
            "reason": "Configured to stop following and hold when leader data is lost.",
            "strategy": normalized_strategy,
        }

    assignments = swarm_config or {}

    if normalized_strategy == "next_hw_id":
        all_ids = sorted(
            int(drone_id)
            for drone_id in assignments.keys()
            if normalize_hw_id(drone_id) is not None
        )
        current_index = -1
        if normalized_leader is not None and int(normalized_leader) in all_ids:
            current_index = all_ids.index(int(normalized_leader))

        if not all_ids:
            return {
                "action": "self_hold",
                "leader_hw_id": None,
                "reason": "No valid drones are available in the swarm configuration.",
                "strategy": normalized_strategy,
            }

        candidate = str(all_ids[(current_index + 1) % len(all_ids)])
        if candidate == normalized_self or _would_create_cycle(normalized_self, candidate, assignments):
            return {
                "action": "self_hold",
                "leader_hw_id": None,
                "reason": f"Legacy next-hw-id failover resolved to an unsafe candidate ({candidate}); holding instead of creating a loop.",
                "strategy": normalized_strategy,
            }

        return {
            "action": "follow",
            "leader_hw_id": candidate,
            "reason": f"Legacy next-hw-id failover selected Drone {candidate}.",
            "strategy": normalized_strategy,
        }

    leader_assignment = assignments.get(normalized_leader) if normalized_leader else None
    upstream_leader = normalize_hw_id(
        leader_assignment.get("follow") if leader_assignment else None
    )

    if (
        upstream_leader
        and upstream_leader != normalized_self
        and not _would_create_cycle(normalized_self, upstream_leader, assignments)
    ):
        return {
            "action": "follow",
            "leader_hw_id": upstream_leader,
            "reason": f"Following failed leader's upstream leader Drone {upstream_leader}.",
            "strategy": "upstream_or_hold",
        }

    return {
        "action": "self_hold",
        "leader_hw_id": None,
        "reason": "Failed leader has no safe upstream candidate; self-promoting and holding position.",
        "strategy": "upstream_or_hold",
    }
