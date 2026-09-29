"""Geodesy helpers — bounding boxes and haversine distance."""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def bounding_box(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (lamin, lomin, lamax, lomax) around a point.

    OpenSky's /states/all credit cost drops sharply for smaller boxes, so this
    is where the credit budget is actually saved.
    """
    lat_delta = radius_km / 111.0  # 1 deg lat ~= 111 km
    lon_delta = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    return (
        max(lat - lat_delta, -90.0),
        max(lon - lon_delta, -180.0),
        min(lat + lat_delta, 90.0),
        min(lon + lon_delta, 180.0),
    )


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
