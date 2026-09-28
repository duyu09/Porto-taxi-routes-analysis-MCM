from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd
from tqdm import tqdm

from smart_taxi.data.io import read_table
from smart_taxi.routing.cost import build_cost_table
from smart_taxi.routing.map_match import nearest_node
from smart_taxi.routing.network import load_network, route_to_geojson
from smart_taxi.utils.config import ensure_dir
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def infer_time_slot(dt: datetime) -> str:
    hour = dt.hour
    if 6 <= hour <= 10:
        return "morning_peak"
    if 11 <= hour <= 15:
        return "midday"
    if 16 <= hour <= 20:
        return "evening_peak"
    if 21 <= hour <= 23:
        return "night"
    return "late_night"


def apply_costs_to_graph(G: nx.MultiDiGraph, edge_costs: pd.DataFrame, default_cost: float = 1.0) -> nx.MultiDiGraph:
    H = G.copy()
    cost_map = {(str(r.u), str(r.v), str(r.key)): float(r.smart_cost) for r in edge_costs.itertuples(index=False)}
    for u, v, k, data in tqdm(H.edges(keys=True, data=True), total=H.number_of_edges(), desc="applying edge costs"):
        key = (str(u), str(v), str(k))
        data["smart_cost"] = cost_map.get(key, float(data.get("length", default_cost) or default_cost))
        if data["smart_cost"] <= 0:
            data["smart_cost"] = default_cost
    return H


def plan_route(
    network_path: str,
    edge_stats_path: str,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    when: str,
    profile: str,
    output_path: str,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    G = load_network(network_path)
    edge_stats = read_table(edge_stats_path)
    dt = pd.to_datetime(when).to_pydatetime()
    slot = infer_time_slot(dt)
    slot_stats = edge_stats[edge_stats["time_slot"].astype(str) == slot].copy()
    if slot_stats.empty:
        slot_stats = edge_stats.copy()
        logger.warning("No edge stats for time_slot=%s; using all time slots.", slot)
    costs = build_cost_table(slot_stats, profile=profile, cfg=cfg)
    H = apply_costs_to_graph(G, costs)

    origin_node = nearest_node(H, origin_lon, origin_lat)
    dest_node = nearest_node(H, dest_lon, dest_lat)
    route = nx.shortest_path(H, source=origin_node, target=dest_node, weight="smart_cost")
    total_cost = 0.0
    total_length = 0.0
    total_time = 0.0
    for a, b in tqdm(zip(route[:-1], route[1:]), total=max(len(route) - 1, 0), desc="summarizing route"):
        edge_datas = H.get_edge_data(a, b)
        if not edge_datas:
            continue
        best = min(edge_datas.values(), key=lambda x: float(x.get("smart_cost", 1)))
        total_cost += float(best.get("smart_cost", 1))
        total_length += float(best.get("length", 0) or 0)
        total_time += float(best.get("travel_time", 0) or 0)

    out = route_to_geojson(H, route, output_path)
    meta = {
        "profile": profile,
        "time_slot": slot,
        "origin_node": str(origin_node),
        "dest_node": str(dest_node),
        "n_nodes": len(route),
        "total_smart_cost": total_cost,
        "total_length_m": total_length,
        "total_freeflow_time_sec": total_time,
        "route_geojson": str(out),
    }
    meta_path = Path(output_path).with_suffix(".meta.json")
    import json
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info("Route saved to %s", out)
    return meta
