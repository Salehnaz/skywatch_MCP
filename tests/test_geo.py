import math

from skywatch.geo import bounding_box, distance_km


def test_bounding_box_around_dubai_is_small():
    # DXB at 25.25, 55.36 with 50 km radius should give a well-under-1-degree box.
    lamin, lomin, lamax, lomax = bounding_box(25.25, 55.36, 50)
    assert lamax - lamin < 1.0
    assert lomax - lomin < 1.5
    assert lamin < 25.25 < lamax
    assert lomin < 55.36 < lomax


def test_distance_km_dxb_to_auh_matches_reference():
    # DXB → AUH is ~120 km great-circle.
    d = distance_km(25.2532, 55.3657, 24.4330, 54.6511)
    assert 110 < d < 135


def test_distance_zero_when_same_point():
    assert distance_km(0, 0, 0, 0) == 0


def test_bounding_box_clamps_at_poles():
    lamin, _, lamax, _ = bounding_box(89.5, 0, 500)
    assert lamax <= 90.0
    assert lamin >= -90.0
    assert not math.isnan(lamin)
