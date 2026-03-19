# gcs-server/sar/mission_manager.py
"""
QuickScout SAR - Mission Manager

In-memory mission lifecycle management with singleton pattern.
"""

import time
import threading
from typing import Dict, Optional, List

from sar.schemas import (
    MissionStatus, DroneSurveyState, SurveyState, DroneCoveragePlan, SurveyConfig
)
from mds_logging import get_logger

logger = get_logger("mission_manager")

_manager_instance = None
_manager_lock = threading.Lock()


def get_mission_manager() -> 'MissionManager':
    """Get or create the singleton MissionManager instance."""
    global _manager_instance
    if _manager_instance is None:
        with _manager_lock:
            if _manager_instance is None:
                _manager_instance = MissionManager()
    return _manager_instance


class MissionManager:
    """In-memory mission state store and lifecycle manager."""

    MAX_MISSIONS = 50  # Evict oldest missions beyond this limit

    def __init__(self):
        self._missions: Dict[str, MissionStatus] = {}
        self._plans: Dict[str, List[DroneCoveragePlan]] = {}
        self._configs: Dict[str, SurveyConfig] = {}
        self._mission_order: List[str] = []  # Track insertion order for LRU eviction
        self._lock = threading.Lock()

    def _evict_oldest(self):
        """Remove oldest missions if over limit. Must be called under lock."""
        while len(self._mission_order) > self.MAX_MISSIONS:
            oldest_id = self._mission_order.pop(0)
            self._missions.pop(oldest_id, None)
            self._plans.pop(oldest_id, None)
            self._configs.pop(oldest_id, None)
            logger.info(f"Evicted old mission {oldest_id} (limit: {self.MAX_MISSIONS})")

    def create_mission(
        self, mission_id: str, plans: List[DroneCoveragePlan], config: SurveyConfig
    ) -> MissionStatus:
        drone_states = {}
        for plan in plans:
            drone_states[plan.hw_id] = DroneSurveyState(
                hw_id=plan.hw_id,
                state=SurveyState.READY,
                total_waypoints=len(plan.waypoints),
            )
        status = MissionStatus(
            mission_id=mission_id,
            state=SurveyState.READY,
            drone_states=drone_states,
        )
        with self._lock:
            self._missions[mission_id] = status
            self._plans[mission_id] = plans
            self._configs[mission_id] = config
            self._mission_order.append(mission_id)
            self._evict_oldest()
        logger.info(f"Mission {mission_id} created with {len(plans)} drones")
        return status

    def get_status(self, mission_id: str) -> Optional[MissionStatus]:
        with self._lock:
            status = self._missions.get(mission_id)
            if status:
                if status.started_at:
                    status.elapsed_time_s = time.time() - status.started_at
                if status.drone_states:
                    total_pct = sum(
                        ds.coverage_percent for ds in status.drone_states.values()
                    ) / len(status.drone_states)
                    status.total_coverage_percent = total_pct
            return status

    def get_plans(self, mission_id: str) -> Optional[List[DroneCoveragePlan]]:
        with self._lock:
            return self._plans.get(mission_id)

    def get_config(self, mission_id: str) -> Optional[SurveyConfig]:
        with self._lock:
            return self._configs.get(mission_id)

    def start_mission(self, mission_id: str) -> Optional[MissionStatus]:
        with self._lock:
            status = self._missions.get(mission_id)
            if not status:
                return None
            status.state = SurveyState.EXECUTING
            status.started_at = time.time()
            for ds in status.drone_states.values():
                ds.state = SurveyState.EXECUTING
            return status

    def update_drone_progress(
        self, mission_id: str, hw_id: str,
        current_waypoint_index: int, total_waypoints: int,
        distance_covered_m: float = 0, state: Optional[SurveyState] = None,
    ) -> bool:
        with self._lock:
            status = self._missions.get(mission_id)
            if not status or hw_id not in status.drone_states:
                return False
            ds = status.drone_states[hw_id]
            ds.current_waypoint_index = current_waypoint_index
            ds.total_waypoints = total_waypoints
            ds.distance_covered_m = distance_covered_m
            if total_waypoints > 0:
                ds.coverage_percent = (current_waypoint_index / total_waypoints) * 100.0
            if state:
                ds.state = state
            elif current_waypoint_index >= total_waypoints and total_waypoints > 0:
                ds.state = SurveyState.COMPLETED
            if all(d.state == SurveyState.COMPLETED for d in status.drone_states.values()):
                status.state = SurveyState.COMPLETED
            return True

    def pause_mission(self, mission_id: str, hw_ids: Optional[List[str]] = None) -> bool:
        with self._lock:
            status = self._missions.get(mission_id)
            if not status:
                return False
            for hw_id, ds in status.drone_states.items():
                if hw_ids is None or hw_id in hw_ids:
                    if ds.state == SurveyState.EXECUTING:
                        ds.state = SurveyState.PAUSED
            if all(ds.state == SurveyState.PAUSED for ds in status.drone_states.values()):
                status.state = SurveyState.PAUSED
            return True

    def resume_mission(self, mission_id: str, hw_ids: Optional[List[str]] = None) -> bool:
        with self._lock:
            status = self._missions.get(mission_id)
            if not status:
                return False
            for hw_id, ds in status.drone_states.items():
                if hw_ids is None or hw_id in hw_ids:
                    if ds.state == SurveyState.PAUSED:
                        ds.state = SurveyState.EXECUTING
            if any(ds.state == SurveyState.EXECUTING for ds in status.drone_states.values()):
                status.state = SurveyState.EXECUTING
            return True

    def abort_mission(self, mission_id: str, hw_ids: Optional[List[str]] = None, return_behavior: str = "return_home") -> bool:
        with self._lock:
            status = self._missions.get(mission_id)
            if not status:
                return False
            for hw_id, ds in status.drone_states.items():
                if hw_ids is None or hw_id in hw_ids:
                    ds.state = SurveyState.ABORTED
            if all(ds.state == SurveyState.ABORTED for ds in status.drone_states.values()):
                status.state = SurveyState.ABORTED
            return True
