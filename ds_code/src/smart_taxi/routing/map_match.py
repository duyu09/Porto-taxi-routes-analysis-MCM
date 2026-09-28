from __future__ import annotations

import ast
from typing import Any, Iterable

import pandas as pd
from tqdm import tqdm

from smart_taxi.data.io import read_table
from smart_taxi.routing.network import load_network
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def _import_osmnx():
    try:
        import osmnx as ox
        return ox
    except Exception as exc:
        raise ImportError("osmnx is required for map matching.") from exc


def parse_points_json(value) -> list[tuple[float, float]]:
    if isinstance(value, list):
        return value
    if value is None or pd.isna(value):
        return []
    try:
        raw = ast.literal_eval(str(value))
    except Exception:
        return []
    points = []
    for item in raw:
        try:
            lon, lat = float(item[0]), float(item[1])
            points.append((lon, lat))
        except Exception:
            continue
    return points


def nearest_node(G, lon: float, lat: float):
    ox = _import_osmnx()
    return ox.distance.nearest_nodes(G, X=lon, Y=lat)


def nearest_edge(G, lon: float, lat: float):
    ox = _import_osmnx()
    return ox.distance.nearest_edges(G, X=lon, Y=lat)


def sample_points(points: list[tuple[float, float]], n: int = 3) -> list[tuple[float, float]]:
    if not points:
        return []
    if len(points) <= n:
        return points
    idx = sorted(set([0, len(points) - 1] + [round(i * (len(points) - 1) / max(n - 1, 1)) for i in range(n)]))
    return [points[i] for i in idx]


def trip_nearest_edges(G, points: list[tuple[float, float]], sample_n: int = 3) -> list[tuple]:
    edges = []
    for lon, lat in sample_points(points, sample_n):
        try:
            edge = nearest_edge(G, lon, lat)
            if isinstance(edge, tuple) and len(edge) >= 3:
                edges.append((str(edge[0]), str(edge[1]), str(edge[2])))
        except Exception:
            continue
    return edges


def attach_edge_sequence(features_path: str, network_path: str, output_path: str, sample_n: int = 3) -> pd.DataFrame:
    df = read_table(features_path)
    G = load_network(network_path)
    seqs = []
    for value in tqdm(df["points_json"], desc="nearest-edge matching"):
        pts = parse_points_json(value)
        seqs.append(trip_nearest_edges(G, pts, sample_n=sample_n))
    out = df.copy()
    out["edge_sequence"] = [str(seq) for seq in seqs]
    out.to_csv(output_path, index=False)
    logger.info("Edge sequences saved to %s", output_path)
    return out
