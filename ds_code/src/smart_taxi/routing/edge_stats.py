from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

from joblib import Parallel, delayed
import numpy as np
import pandas as pd
from tqdm import tqdm

from smart_taxi.data.io import read_table, write_table
from smart_taxi.routing.map_match import parse_points_json, sample_points
from smart_taxi.routing.network import load_network
from smart_taxi.utils.config import ensure_dir
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def _edge_key(u, v, k) -> str:
    return f"{u}|{v}|{k}"


def _parse_edge_sequence(value) -> list[tuple[str, str, str]]:
    if isinstance(value, list):
        return value
    if value is None or pd.isna(value):
        return []
    try:
        raw = ast.literal_eval(str(value))
    except Exception:
        return []
    out = []
    for x in raw:
        if isinstance(x, (list, tuple)) and len(x) >= 3:
            out.append((str(x[0]), str(x[1]), str(x[2])))
    return out


def _cpu_minus_one() -> int:
    return max((os.cpu_count() or 1) - 1, 1)


def _map_match_parallel_jobs(cfg: dict[str, Any]) -> int:
    value = cfg.get("network", {}).get("map_match_parallel_jobs", None)
    if value is None:
        return _cpu_minus_one()
    try:
        value = int(value)
    except Exception:
        return _cpu_minus_one()
    if value <= 0:
        return _cpu_minus_one()
    return value


def _nearest_edges_batch(G, xs: list[float], ys: list[float]) -> list[tuple]:
    try:
        import osmnx as ox
    except Exception as exc:
        raise ImportError("osmnx is required for map matching.") from exc
    try:
        edges = ox.distance.nearest_edges(G, X=xs, Y=ys)
    except Exception:
        edges = []
        for x, y in zip(xs, ys):
            try:
                edges.append(ox.distance.nearest_edges(G, X=x, Y=y))
            except Exception:
                edges.append(None)
    if isinstance(edges, tuple) and len(edges) >= 3:
        return [edges]
    return list(edges)


def _build_edge_sequences_parallel(
    G,
    points_json_values,
    sample_n: int,
    n_jobs: int,
    query_batch_size: int,
) -> list[list[tuple[str, str, str]]]:
    seqs: list[list[tuple[str, str, str]]] = [[] for _ in range(len(points_json_values))]
    trip_refs: list[int] = []
    xs: list[float] = []
    ys: list[float] = []

    for trip_idx, value in enumerate(tqdm(points_json_values, desc="sampling points for edge sequences")):
        pts = parse_points_json(value)
        for lon, lat in sample_points(pts, sample_n):
            trip_refs.append(trip_idx)
            xs.append(float(lon))
            ys.append(float(lat))

    if not xs:
        return seqs

    batch_size = max(int(query_batch_size), 1)
    chunks = [(i, min(i + batch_size, len(xs))) for i in range(0, len(xs), batch_size)]

    def _query_chunk(start: int, end: int):
        return start, _nearest_edges_batch(G, xs[start:end], ys[start:end])

    parallel = Parallel(n_jobs=n_jobs, backend="threading", return_as="generator")
    results = parallel(delayed(_query_chunk)(start, end) for start, end in chunks)

    for start, edges in tqdm(results, total=len(chunks), desc="batch nearest-edge queries"):
        for offset, edge in enumerate(edges):
            if isinstance(edge, tuple) and len(edge) >= 3:
                trip_idx = trip_refs[start + offset]
                seqs[trip_idx].append((str(edge[0]), str(edge[1]), str(edge[2])))

    return seqs


def build_edge_statistics(features_path: str, network_path: str, output_path: str, cfg: dict[str, Any]) -> pd.DataFrame:
    """Build edge-level historical statistics from feature table.

    The default implementation approximates map matching by sampling points from each trajectory
    and assigning them to nearest OSM edges. It then aggregates speed, congestion, risk, and pickup
    opportunity by edge and time slot.
    """
    df = read_table(features_path)
    G = load_network(network_path)
    sample_n = int(cfg.get("network", {}).get("map_match_sample_points", 3))
    n_jobs = _map_match_parallel_jobs(cfg)
    query_batch_size = int(cfg.get("network", {}).get("map_match_query_batch_size", 20000))

    if "edge_sequence" not in df.columns:
        seqs = _build_edge_sequences_parallel(
            G,
            list(df["points_json"]),
            sample_n=sample_n,
            n_jobs=n_jobs,
            query_batch_size=query_batch_size,
        )
        df = df.copy()
        df["edge_sequence"] = [str(seq) for seq in seqs]

    rows = []
    for _, r in tqdm(df.iterrows(), total=len(df), desc="aggregating edge stats"):
        seq = _parse_edge_sequence(r.get("edge_sequence"))
        if not seq:
            continue
        unique_seq = list(dict.fromkeys(seq))
        speed = float(r.get("avg_speed_kmh", np.nan))
        duration = float(r.get("duration_sec", np.nan))
        dist = float(r.get("distance_m", np.nan))
        time_slot = str(r.get("time_slot", "unknown"))
        for i, (u, v, k) in enumerate(unique_seq):
            rows.append({
                "u": u, "v": v, "key": k, "edge_id": _edge_key(u, v, k), "time_slot": time_slot,
                "trip_count": 1,
                "mean_trip_speed_kmh": speed,
                "mean_trip_duration_sec": duration,
                "mean_trip_distance_m": dist,
                "pickup_count": 1 if i == 0 else 0,
            })
    if not rows:
        raise ValueError("No edge statistics could be built. Check network coverage and feature points_json.")

    stats = pd.DataFrame(rows)
    agg = stats.groupby(["u", "v", "key", "edge_id", "time_slot"], as_index=False).agg(
        trip_count=("trip_count", "sum"),
        pickup_count=("pickup_count", "sum"),
        mean_speed_kmh=("mean_trip_speed_kmh", "mean"),
        mean_trip_duration_sec=("mean_trip_duration_sec", "mean"),
        mean_trip_distance_m=("mean_trip_distance_m", "mean"),
    )
    agg["pickup_probability"] = agg["pickup_count"] / agg["trip_count"].clip(lower=1)

    # Attach static OSM attributes.
    attr_rows = []
    for u, v, k, data in tqdm(G.edges(keys=True, data=True), total=G.number_of_edges(), desc="collecting edge attributes"):
        edge_id = _edge_key(u, v, k)
        length = float(data.get("length", 0.0) or 0.0)
        speed = float(data.get("speed_kph", cfg.get("network", {}).get("default_speed_kph", 35)) or 35)
        travel_time = float(data.get("travel_time", length / max(speed, 1) * 3.6))
        highway = data.get("highway", "unknown")
        if isinstance(highway, list):
            highway = highway[0]
        attr_rows.append({
            "u": str(u), "v": str(v), "key": str(k), "edge_id": edge_id,
            "length_m": length, "osm_speed_kph": speed, "freeflow_time_sec": travel_time,
            "highway": str(highway),
        })
    attrs = pd.DataFrame(attr_rows)
    result = agg.merge(attrs, on=["u", "v", "key", "edge_id"], how="left")
    fallback_speed = float(cfg.get("network", {}).get("default_speed_kph", 35))
    result["mean_speed_kmh"] = result["mean_speed_kmh"].fillna(fallback_speed).clip(lower=3, upper=130)
    result["estimated_time_sec"] = result["length_m"].fillna(0) / result["mean_speed_kmh"].clip(lower=1) * 3.6
    result["congestion_index"] = (result["estimated_time_sec"] / result["freeflow_time_sec"].replace(0, np.nan)).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    result["congestion_index"] = result["congestion_index"].clip(lower=0.3, upper=5.0)

    main_road = {"motorway", "trunk", "primary", "secondary"}
    result["road_penalty"] = np.where(result["highway"].isin(main_road), 0.1, 0.4)
    result["risk_index"] = (result["congestion_index"] - 1.0).clip(lower=0) + result["road_penalty"]

    out = write_table(result, output_path)
    logger.info("Edge stats saved to %s with shape %s", out, result.shape)
    return result
