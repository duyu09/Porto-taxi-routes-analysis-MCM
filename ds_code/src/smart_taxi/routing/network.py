from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx

from smart_taxi.utils.config import ensure_dir
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def load_bbox_from_porto_json(json_path: str | Path = "porto.json") -> tuple[float, float, float, float]:
    """Load local porto.json and return bbox as (north, south, east, west)."""
    path = Path(json_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    item = data[0] if isinstance(data, list) else data
    south, north, west, east = map(float, item["boundingbox"])
    return north, south, east, west


def _import_osmnx():
    try:
        import osmnx as ox
        return ox
    except Exception as exc:
        raise ImportError("osmnx is required for network and routing commands. Install requirements.txt first.") from exc


def build_osm_network(
    output_path: str,
    cfg: dict[str, Any],
    place: str | None = None,
    bbox: tuple[float, float, float, float] | None = None,
) -> Path:
    """Build a drivable OSM network and save as GraphML.

    bbox order is (north, south, east, west).
    """
    ox = _import_osmnx()
    net_cfg = cfg.get("network", {})
    network_type = str(net_cfg.get("network_type", "drive"))
    simplify = bool(net_cfg.get("simplify", True))
    retain_all = bool(net_cfg.get("retain_all", False))

    if bbox is None:
        json_path = net_cfg.get("nominatim_json", "porto.json")
        bbox = load_bbox_from_porto_json(json_path)
    north, south, east, west = bbox
    G = ox.graph_from_bbox((west, south, east, north), network_type=network_type, simplify=simplify, retain_all=retain_all)
    G = ox.add_edge_speeds(G, fallback=float(net_cfg.get("default_speed_kph", 35)))
    G = ox.add_edge_travel_times(G)
    out = Path(output_path)
    ensure_dir(out.parent)
    ox.save_graphml(G, out)
    logger.info("OSM network saved to %s with %s nodes and %s edges", out, len(G.nodes), len(G.edges))
    return out


def load_network(path: str | Path):
    ox = _import_osmnx()
    return ox.load_graphml(path)


def edge_length_m(data: dict[str, Any]) -> float:
    try:
        return float(data.get("length", 0.0))
    except Exception:
        return 0.0


def route_to_geojson(G: nx.MultiDiGraph, route: list, output_path: str | Path) -> Path:
    """Save a route as GeoJSON LineString using OSMnx route_to_gdf when available."""
    ox = _import_osmnx()
    out = Path(output_path)
    ensure_dir(out.parent)
    try:
        gdf = ox.routing.route_to_gdf(G, route)
    except AttributeError:
        gdf = ox.utils_graph.route_to_gdf(G, route)
    gdf.to_file(out, driver="GeoJSON")
    return out
