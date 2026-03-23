import math

from multiple_sitl.calculate_spawn_coordinates import calculate_coordinates


def test_calculate_coordinates_handles_scientific_notation_offsets():
    new_lat, new_lon = calculate_coordinates(
        lat=47.3977419,
        lon=8.5455938,
        offset_north=5.437202729504529e-131,
        offset_east=2.5000000000000013,
    )

    assert math.isclose(new_lat, 47.3977419, rel_tol=0.0, abs_tol=1e-12)
    assert new_lon > 8.5455938


def test_calculate_coordinates_preserves_position_for_zero_offsets():
    new_lat, new_lon = calculate_coordinates(
        lat=47.3977419,
        lon=8.5455938,
        offset_north=0.0,
        offset_east=0.0,
    )

    assert math.isclose(new_lat, 47.3977419, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(new_lon, 8.5455938, rel_tol=0.0, abs_tol=1e-12)
