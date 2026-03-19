# gcs-server/sar/poi_manager.py
"""
QuickScout SAR - POI Manager

Simple in-memory CRUD for Points of Interest, keyed by mission_id.
"""

import uuid
import time
import threading
from typing import List, Optional, Dict

from sar.schemas import POI
from mds_logging import get_logger

logger = get_logger("poi_manager")

_poi_instance = None
_poi_lock = threading.Lock()


def get_poi_manager() -> 'POIManager':
    global _poi_instance
    if _poi_instance is None:
        with _poi_lock:
            if _poi_instance is None:
                _poi_instance = POIManager()
    return _poi_instance


class POIManager:
    def __init__(self):
        self._pois: Dict[str, List[POI]] = {}
        self._poi_index: Dict[str, POI] = {}
        self._lock = threading.Lock()

    def add_poi(self, mission_id: str, poi: POI) -> POI:
        with self._lock:
            if not poi.id:
                poi.id = str(uuid.uuid4())
            if not poi.timestamp:
                poi.timestamp = time.time()
            poi.mission_id = mission_id
            if mission_id not in self._pois:
                self._pois[mission_id] = []
            self._pois[mission_id].append(poi)
            self._poi_index[poi.id] = poi
        logger.info(f"POI {poi.id} added to mission {mission_id}")
        return poi

    def get_pois(self, mission_id: str) -> List[POI]:
        with self._lock:
            return list(self._pois.get(mission_id, []))

    def update_poi(self, poi_id: str, updates: dict) -> Optional[POI]:
        with self._lock:
            poi = self._poi_index.get(poi_id)
            if not poi:
                return None
            for key, value in updates.items():
                if hasattr(poi, key) and key not in ('id', 'mission_id'):
                    setattr(poi, key, value)
            return poi

    def delete_poi(self, poi_id: str) -> bool:
        with self._lock:
            poi = self._poi_index.pop(poi_id, None)
            if not poi:
                return False
            mission_pois = self._pois.get(poi.mission_id, [])
            self._pois[poi.mission_id] = [p for p in mission_pois if p.id != poi_id]
            return True
