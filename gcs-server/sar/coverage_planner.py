# gcs-server/sar/coverage_planner.py
"""
QuickScout SAR - Coverage Path Planning

Boustrophedon (lawn-mower) coverage planning for multi-drone area survey.
Computes optimal sweep paths, partitions among drones, and assigns sectors
by proximity.

Dependencies: shapely (GCS server only), numpy, pymap3d
"""

import os
import sys
import uuid
import math
from typing import List, Tuple, Optional, Dict

import numpy as np
import pymap3d

# Shapely is only needed on GCS server, not on drones.
# Graceful import so drone-side code that imports enums/schemas won't break.
try:
    from shapely.geometry import Polygon as ShapelyPolygon, LineString, MultiLineString
    from shapely.ops import split
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from sar.schemas import (
    SearchAreaPoint, SurveyConfig, CoverageWaypoint, DroneCoveragePlan
)
from mds_logging import get_logger

logger = get_logger("coverage_planner")


def _require_shapely():
    """Raise clear error if shapely not installed."""
    if not SHAPELY_AVAILABLE:
        raise ImportError(
            "shapely is required for coverage planning but not installed. "
            "Install with: pip install shapely>=2.0. "
            "This is only needed on the GCS server, not on drones."
        )


class BaseCoveragePlanner:
    """Base class for coverage planning algorithms."""

    def plan(
        self,
        polygon_points: List[SearchAreaPoint],
        drone_positions: Dict[str, Tuple[float, float]],
        config: SurveyConfig,
    ) -> Tuple[List[DroneCoveragePlan], float]:
        """
        Compute coverage plans for all drones.

        Args:
            polygon_points: List of polygon vertices (lat/lng)
            drone_positions: Dict of pos_id -> (lat, lng) for available drones
            config: Survey configuration

        Returns:
            Tuple of (list of DroneCoveragePlan, total_area_sq_m)
        """
        raise NotImplementedError


class BoustrophedonPlanner(BaseCoveragePlanner):
    """
    Boustrophedon (lawn-mower) coverage planner.

    Algorithm:
    1. Convert lat/lng to local ENU frame
    2. Compute optimal sweep angle (aligned with longest polygon edge)
    3. Generate parallel sweep lines with configured spacing
    4. Clip lines to polygon boundary
    5. Connect into boustrophedon path (alternating direction)
    6. Partition sweep lines among N drones (equal path length)
    7. Assign sectors to drones by GPS proximity
    8. Convert back to lat/lng
    9. Add transit waypoints (takeoff -> sector entry, sector exit -> return)
    """

    def plan(
        self,
        polygon_points: List[SearchAreaPoint],
        drone_positions: Dict[str, Tuple[float, float]],
        config: SurveyConfig,
    ) -> Tuple[List[DroneCoveragePlan], float]:
        _require_shapely()

        if len(polygon_points) < 3:
            raise ValueError("Polygon must have at least 3 points")
        if not drone_positions:
            raise ValueError("At least one drone position required")

        # Step 1: Compute centroid as ENU origin
        origin_lat = np.mean([p.lat for p in polygon_points])
        origin_lng = np.mean([p.lng for p in polygon_points])
        origin_alt = 0.0

        # Step 2: Convert polygon to ENU
        enu_points = []
        for p in polygon_points:
            e, n, u = pymap3d.geodetic2enu(p.lat, p.lng, 0, origin_lat, origin_lng, origin_alt)
            enu_points.append((e, n))

        polygon = ShapelyPolygon(enu_points)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)  # Fix self-intersections
        total_area_sq_m = polygon.area

        # Step 3: Compute optimal sweep angle (align with longest edge)
        sweep_angle = self._compute_sweep_angle(enu_points)

        # Step 4: Generate sweep lines
        spacing = config.sweep_width_m * (1.0 - config.overlap_percent / 100.0)
        sweep_lines = self._generate_sweep_lines(polygon, sweep_angle, spacing)

        if not sweep_lines:
            raise ValueError("No sweep lines generated - polygon may be too small for sweep width")

        # Step 5: Build boustrophedon path (alternate direction per line)
        boustrophedon_lines = self._build_boustrophedon(sweep_lines)

        # Step 6: Partition among drones
        n_drones = len(drone_positions)
        partitions = self._partition_lines(boustrophedon_lines, n_drones)

        # Step 7: Convert drone positions to ENU
        drone_enu = {}
        for pos_id, (lat, lng) in drone_positions.items():
            e, n, u = pymap3d.geodetic2enu(lat, lng, 0, origin_lat, origin_lng, origin_alt)
            drone_enu[pos_id] = (e, n)

        # Step 8: Assign sectors to drones by proximity (greedy nearest-match)
        assignments = self._assign_sectors(partitions, drone_enu)

        # Step 9: Build per-drone plans
        plans = []
        for pos_id, hw_id_str in drone_positions.items():
            if pos_id not in assignments:
                continue
            sector_lines = assignments[pos_id]
            drone_lat, drone_lng = drone_positions[pos_id]

            waypoints = self._build_waypoints(
                sector_lines, origin_lat, origin_lng, origin_alt,
                config, drone_lat, drone_lng
            )

            if not waypoints:
                continue

            total_distance = self._compute_total_distance(waypoints)
            survey_distance = sum(
                self._haversine_m(waypoints[i].lat, waypoints[i].lng, waypoints[i+1].lat, waypoints[i+1].lng)
                for i in range(len(waypoints)-1) if waypoints[i].is_survey_leg
            )
            assigned_area = total_area_sq_m * (len(sector_lines) / max(len(boustrophedon_lines), 1))
            est_duration = total_distance / config.survey_speed_ms if config.survey_speed_ms > 0 else 0

            plan = DroneCoveragePlan(
                hw_id=str(pos_id),  # Will be updated with real hw_id in routes
                pos_id=int(pos_id),
                waypoints=waypoints,
                assigned_area_sq_m=assigned_area,
                estimated_duration_s=est_duration,
                total_distance_m=total_distance,
            )
            plans.append(plan)

        return plans, total_area_sq_m

    def _compute_sweep_angle(self, enu_points: List[Tuple[float, float]]) -> float:
        """Compute optimal sweep angle aligned with the longest polygon edge."""
        max_length = 0
        best_angle = 0
        n = len(enu_points)
        for i in range(n):
            j = (i + 1) % n
            dx = enu_points[j][0] - enu_points[i][0]
            dy = enu_points[j][1] - enu_points[i][1]
            length = math.hypot(dx, dy)
            if length > max_length:
                max_length = length
                best_angle = math.atan2(dy, dx)
        return best_angle

    def _generate_sweep_lines(
        self, polygon: 'ShapelyPolygon', angle: float, spacing: float
    ) -> List[LineString]:
        """Generate parallel sweep lines across the polygon at the given angle."""
        # Rotate polygon to align sweep direction with x-axis
        cos_a, sin_a = math.cos(-angle), math.sin(-angle)

        # Get polygon bounds in rotated frame
        coords = list(polygon.exterior.coords)
        rotated = [(x * cos_a - y * sin_a, x * sin_a + y * cos_a) for x, y in coords]

        min_y = min(p[1] for p in rotated)
        max_y = max(p[1] for p in rotated)
        min_x = min(p[0] for p in rotated) - 10  # Extend beyond bounds
        max_x = max(p[0] for p in rotated) + 10

        # Generate lines in rotated frame, then rotate back
        lines = []
        y = min_y + spacing / 2
        cos_a_inv, sin_a_inv = math.cos(angle), math.sin(angle)

        while y <= max_y:
            # Line endpoints in rotated frame
            x1, y1 = min_x, y
            x2, y2 = max_x, y

            # Rotate back to original frame
            rx1 = x1 * cos_a_inv - y1 * sin_a_inv
            ry1 = x1 * sin_a_inv + y1 * cos_a_inv
            rx2 = x2 * cos_a_inv - y2 * sin_a_inv
            ry2 = x2 * sin_a_inv + y2 * cos_a_inv

            line = LineString([(rx1, ry1), (rx2, ry2)])
            clipped = polygon.intersection(line)

            if clipped.is_empty:
                y += spacing
                continue

            if isinstance(clipped, LineString):
                lines.append(clipped)
            elif isinstance(clipped, MultiLineString):
                lines.extend(list(clipped.geoms))

            y += spacing

        return lines

    def _build_boustrophedon(self, lines: List[LineString]) -> List[LineString]:
        """Alternate direction of sweep lines for efficient coverage."""
        result = []
        for i, line in enumerate(lines):
            coords = list(line.coords)
            if i % 2 == 1:
                coords.reverse()
            result.append(LineString(coords))
        return result

    def _partition_lines(self, lines: List[LineString], n: int) -> List[List[LineString]]:
        """Partition sweep lines into n groups with roughly equal total path length."""
        if n <= 0:
            return []
        if n == 1:
            return [lines]

        # Compute cumulative lengths
        lengths = [line.length for line in lines]
        total_length = sum(lengths)
        target_per_group = total_length / n

        partitions = []
        current_group = []
        current_length = 0

        for i, line in enumerate(lines):
            current_group.append(line)
            current_length += lengths[i]

            # Start new group if we've reached the target (but not for last group)
            if current_length >= target_per_group and len(partitions) < n - 1:
                partitions.append(current_group)
                current_group = []
                current_length = 0

        # Last group gets remaining lines
        if current_group:
            partitions.append(current_group)

        # If we have fewer partitions than drones, pad with empty
        while len(partitions) < n:
            partitions.append([])

        return partitions

    def _assign_sectors(
        self, partitions: List[List[LineString]], drone_enu: Dict[str, Tuple[float, float]]
    ) -> Dict[str, List[LineString]]:
        """Assign sectors to drones by proximity (greedy nearest-match)."""
        # Compute entry point of each partition
        entry_points = []
        for part in partitions:
            if part:
                first_line = part[0]
                entry_points.append(first_line.coords[0])
            else:
                entry_points.append((0, 0))

        assignments = {}
        used_partitions = set()
        drone_ids = list(drone_enu.keys())

        for drone_id in drone_ids:
            de, dn = drone_enu[drone_id]
            best_dist = float('inf')
            best_idx = -1

            for idx in range(len(partitions)):
                if idx in used_partitions:
                    continue
                pe, pn = entry_points[idx]
                dist = math.hypot(de - pe, dn - pn)
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx

            if best_idx >= 0:
                used_partitions.add(best_idx)
                assignments[drone_id] = partitions[best_idx]

        return assignments

    def _build_waypoints(
        self,
        sector_lines: List[LineString],
        origin_lat: float, origin_lng: float, origin_alt: float,
        config: SurveyConfig,
        drone_lat: float, drone_lng: float,
    ) -> List[CoverageWaypoint]:
        """Convert ENU sector lines to lat/lng waypoints with transit legs."""
        waypoints = []
        seq = 0

        # Transit: drone position -> first survey point (at cruise alt)
        if sector_lines:
            first_coord = sector_lines[0].coords[0]
            first_lat, first_lng, _ = pymap3d.enu2geodetic(
                first_coord[0], first_coord[1], 0, origin_lat, origin_lng, origin_alt
            )

            # Transit to sector entry
            waypoints.append(CoverageWaypoint(
                lat=first_lat, lng=first_lng,
                alt_msl=config.cruise_altitude_msl,
                is_survey_leg=False,
                speed_ms=config.cruise_speed_ms,
                sequence=seq,
            ))
            seq += 1

        # Survey waypoints
        for line in sector_lines:
            for coord in line.coords:
                lat, lng, _ = pymap3d.enu2geodetic(
                    coord[0], coord[1], 0, origin_lat, origin_lng, origin_alt
                )
                waypoints.append(CoverageWaypoint(
                    lat=lat, lng=lng,
                    alt_msl=config.cruise_altitude_msl,  # Will be adjusted by terrain module
                    is_survey_leg=True,
                    speed_ms=config.survey_speed_ms,
                    sequence=seq,
                ))
                seq += 1

        # Transit: last survey point -> (handled by return behavior)

        return waypoints

    def _compute_total_distance(self, waypoints: List[CoverageWaypoint]) -> float:
        """Compute total path distance in meters."""
        total = 0
        for i in range(len(waypoints) - 1):
            total += self._haversine_m(
                waypoints[i].lat, waypoints[i].lng,
                waypoints[i+1].lat, waypoints[i+1].lng
            )
        return total

    @staticmethod
    def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Compute haversine distance between two points in meters."""
        R = 6371000  # Earth radius in meters
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
