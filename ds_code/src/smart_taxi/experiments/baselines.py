from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from smart_taxi.routing.planner import plan_route
from smart_taxi.utils.config import ensure_dir


def compare_route_baselines(
    network_path: str,
    edge_stats_path: str,
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    when: str,
    output_dir: str,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    out = ensure_dir(output_dir)
    profiles = cfg.get("experiments", {}).get("baselines", [
        "shortest_distance", "shortest_time", "congestion_only", "pickup_only", "composite_passenger", "composite_driver"
    ])
    rows = []
    for profile in tqdm(profiles, desc="comparing route baselines"):
        route_file = out / f"route_{profile}.geojson"
        meta = plan_route(
            network_path, edge_stats_path, origin_lat, origin_lon, dest_lat, dest_lon,
            when, profile, str(route_file), cfg
        )
        rows.append(meta)
    result = pd.DataFrame(rows)
    result.to_csv(out / "baseline_comparison.csv", index=False)
    return result
