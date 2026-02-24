"""
Tests for QuickScout SAR coverage planning algorithm.
Tests boustrophedon planner with various polygon shapes and drone configurations.
"""

import os
import sys
import math
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'gcs-server'))

from sar.schemas import SearchAreaPoint, SurveyConfig
from sar.coverage_planner import BoustrophedonPlanner, SHAPELY_AVAILABLE

# Skip all tests if shapely not installed
pytestmark = pytest.mark.skipif(not SHAPELY_AVAILABLE, reason="shapely not installed")


@pytest.fixture
def planner():
    return BoustrophedonPlanner()


@pytest.fixture
def default_config():
    return SurveyConfig(
        sweep_width_m=30,
        overlap_percent=10,
        cruise_altitude_msl=50,
        survey_altitude_agl=40,
        cruise_speed_ms=10,
        survey_speed_ms=5,
    )


def make_rectangle(lat, lng, width_m, height_m):
    """Create a rectangular polygon given center and dimensions in meters."""
    # Approximate degrees per meter
    dlat = height_m / 111320.0  # ~111km per degree latitude
    dlng = width_m / (111320.0 * math.cos(math.radians(lat)))

    return [
        SearchAreaPoint(lat=lat - dlat/2, lng=lng - dlng/2),
        SearchAreaPoint(lat=lat - dlat/2, lng=lng + dlng/2),
        SearchAreaPoint(lat=lat + dlat/2, lng=lng + dlng/2),
        SearchAreaPoint(lat=lat + dlat/2, lng=lng - dlng/2),
    ]


class TestBoustrophedonPlanner:
    def test_simple_rectangle_single_drone(self, planner, default_config):
        """Single drone should get the full coverage."""
        polygon = make_rectangle(47.0, 8.0, 200, 200)
        drones = {"0": (47.0, 8.0)}

        plans, area = planner.plan(polygon, drones, default_config)

        assert len(plans) == 1
        assert area > 0
        assert len(plans[0].waypoints) > 0
        assert plans[0].total_distance_m > 0

    def test_rectangle_four_drones(self, planner, default_config):
        """4 drones should get roughly equal partitions."""
        polygon = make_rectangle(47.0, 8.0, 400, 400)
        drones = {
            "0": (47.001, 8.001),
            "1": (47.001, 8.003),
            "2": (47.003, 8.001),
            "3": (47.003, 8.003),
        }

        plans, area = planner.plan(polygon, drones, default_config)

        assert len(plans) == 4
        assert area > 0
        # All drones should have waypoints
        for plan in plans:
            assert len(plan.waypoints) > 0

    def test_triangle(self, planner, default_config):
        """Triangle polygon should work."""
        polygon = [
            SearchAreaPoint(lat=47.0, lng=8.0),
            SearchAreaPoint(lat=47.002, lng=8.0),
            SearchAreaPoint(lat=47.001, lng=8.003),
        ]
        drones = {"0": (47.001, 8.001)}

        plans, area = planner.plan(polygon, drones, default_config)

        assert len(plans) == 1
        assert area > 0

    def test_minimum_polygon(self, planner, default_config):
        """Minimum 3-point polygon should work."""
        polygon = [
            SearchAreaPoint(lat=0, lng=0),
            SearchAreaPoint(lat=0.001, lng=0),
            SearchAreaPoint(lat=0.0005, lng=0.001),
        ]
        drones = {"0": (0.0005, 0.0005)}

        plans, area = planner.plan(polygon, drones, default_config)

        assert len(plans) == 1
        assert area > 0

    def test_too_few_points_raises(self, planner, default_config):
        """Less than 3 points should raise ValueError."""
        polygon = [
            SearchAreaPoint(lat=0, lng=0),
            SearchAreaPoint(lat=1, lng=0),
        ]
        with pytest.raises(ValueError, match="at least 3"):
            planner.plan(polygon, {"0": (0, 0)}, default_config)

    def test_no_drones_raises(self, planner, default_config):
        """No drones should raise ValueError."""
        polygon = make_rectangle(47.0, 8.0, 200, 200)
        with pytest.raises(ValueError, match="[Aa]t least one"):
            planner.plan(polygon, {}, default_config)

    def test_waypoints_have_coordinates(self, planner, default_config):
        """All waypoints should have valid lat/lng."""
        polygon = make_rectangle(47.0, 8.0, 200, 200)
        drones = {"0": (47.0, 8.0)}

        plans, _ = planner.plan(polygon, drones, default_config)

        for wp in plans[0].waypoints:
            assert -90 <= wp.lat <= 90
            assert -180 <= wp.lng <= 180
            assert wp.alt_msl > 0
            assert wp.speed_ms > 0
            assert wp.sequence >= 0

    def test_coordinate_conversion_roundtrip(self):
        """Verify lat/lng -> ENU -> lat/lng roundtrip accuracy."""
        import pymap3d

        origin_lat, origin_lng = 47.0, 8.0
        test_lat, test_lng = 47.001, 8.002

        e, n, u = pymap3d.geodetic2enu(test_lat, test_lng, 0, origin_lat, origin_lng, 0)
        back_lat, back_lng, _ = pymap3d.enu2geodetic(e, n, u, origin_lat, origin_lng, 0)

        assert abs(back_lat - test_lat) < 1e-8
        assert abs(back_lng - test_lng) < 1e-8

    def test_sweep_angle_optimization(self, planner):
        """Sweep angle should align with longest edge."""
        # Long horizontal rectangle
        points = [
            (0, 0), (100, 0), (100, 20), (0, 20)
        ]
        angle = planner._compute_sweep_angle(points)
        # Should be close to 0 (horizontal)
        assert abs(angle) < 0.3 or abs(angle - math.pi) < 0.3

    def test_more_drones_than_lines(self, planner):
        """Should handle case where we have more drones than sweep lines."""
        # Larger area with wide sweep that produces few sweep lines
        polygon = make_rectangle(47.0, 8.0, 200, 200)
        drones = {
            "0": (47.0, 8.0),
            "1": (47.0001, 8.0),
            "2": (47.0, 8.0001),
            "3": (47.0001, 8.0001),
        }
        config = SurveyConfig(sweep_width_m=100)  # Wide sweep = few lines

        plans, area = planner.plan(polygon, drones, config)

        # Some drones may get fewer waypoints, but should not crash
        assert area > 0
