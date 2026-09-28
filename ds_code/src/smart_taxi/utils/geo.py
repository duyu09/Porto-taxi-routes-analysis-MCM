from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Sequence

EARTH_RADIUS_M = 6371008.8


def haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters for WGS84 lon/lat coordinates."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def path_distance_m(points: Sequence[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    return float(sum(haversine_m(a[0], a[1], b[0], b[1]) for a, b in zip(points[:-1], points[1:])))


def bearing_deg(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def mean_bearing_deg(points: Sequence[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    return bearing_deg(points[0][0], points[0][1], points[-1][0], points[-1][1])


def turn_count(points: Sequence[tuple[float, float]], threshold_deg: float = 35.0) -> int:
    if len(points) < 3:
        return 0
    bearings = []
    for a, b in zip(points[:-1], points[1:]):
        if haversine_m(a[0], a[1], b[0], b[1]) > 5:
            bearings.append(bearing_deg(a[0], a[1], b[0], b[1]))
    count = 0
    for prev, cur in zip(bearings[:-1], bearings[1:]):
        diff = abs(cur - prev)
        diff = min(diff, 360.0 - diff)
        if diff >= threshold_deg:
            count += 1
    return count


def lonlat_to_grid(lon: float, lat: float, origin_lon: float, origin_lat: float, grid_size_m: float) -> str:
    """Approximate lon/lat to a stable grid id using local equirectangular scaling."""
    lat_m = 111_320.0
    lon_m = 111_320.0 * math.cos(math.radians(origin_lat))
    x = math.floor((lon - origin_lon) * lon_m / grid_size_m)
    y = math.floor((lat - origin_lat) * lat_m / grid_size_m)
    return f"g{x}_{y}"


def sequence_entropy(items: Iterable[str]) -> float:
    data = [x for x in items if x is not None]
    if not data:
        return 0.0
    n = len(data)
    counts = Counter(data)
    return float(-sum((c / n) * math.log(c / n + 1e-12) for c in counts.values()))


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        x = float(value)
        if math.isnan(x) or math.isinf(x):
            return default
        return x
    except Exception:
        return default
