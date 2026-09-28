from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm

from smart_taxi.routing.planner import plan_route
from smart_taxi.utils.config import ensure_dir


def run_cost_ablation(
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
    variants = {
        "full": {},
        "no_pickup_gap": {"lambda_pickup_gap": 0.0},
        "no_congestion_multiplier": {"lambda_congestion": 0.0},
        "no_road_penalty": {"gamma_road_penalty": 0.0},
        "no_risk": {"delta_risk": 0.0},
        "time_only_heavy": {"alpha_distance": 0.1, "beta_time": 0.8, "gamma_road_penalty": 0.05, "delta_risk": 0.05},
    }
    rows = []
    for name, overrides in tqdm(variants.items(), total=len(variants), desc="running cost ablation"):
        local_cfg = deepcopy(cfg)
        local_cfg.setdefault("cost", {}).setdefault("passenger", {}).update(overrides)
        meta = plan_route(
            network_path, edge_stats_path, origin_lat, origin_lon, dest_lat, dest_lon,
            when, "passenger", str(out / f"route_{name}.geojson"), local_cfg
        )
        meta["variant"] = name
        rows.append(meta)
    result = pd.DataFrame(rows)
    result.to_csv(out / "ablation_results.csv", index=False)
    return result
