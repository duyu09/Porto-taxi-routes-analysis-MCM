from __future__ import annotations

from collections import Counter
from typing import Any
import os

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from tqdm import tqdm

from smart_taxi.data.preprocess import clean_trips, config_from_dict, load_raw_dataframe
from smart_taxi.data.io import write_table
from smart_taxi.utils.geo import lonlat_to_grid, mean_bearing_deg, turn_count, sequence_entropy
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def _time_slot(hour: int) -> str:
    if 6 <= hour <= 10:
        return "morning_peak"
    if 11 <= hour <= 15:
        return "midday"
    if 16 <= hour <= 20:
        return "evening_peak"
    if 21 <= hour <= 23:
        return "night"
    return "late_night"


def _rule_label(row: pd.Series, long_threshold: float) -> str:
    call = str(row.get("CALL_TYPE", "unknown"))
    if row.get("distance_m", 0) >= long_threshold:
        return "long_cross_area"
    if call == "B":
        return "stand_pickup"
    if call == "A":
        return "dispatch_call"
    if call == "C":
        return "street_hail"
    return "other"


def _cpu_minus_one() -> int:
    return max((os.cpu_count() or 1) - 1, 1)


def _compute_spatial_behavior_features(
    row: dict[str, Any],
    origin_lon: float,
    origin_lat: float,
    grid_size_m: float,
    turn_threshold: float,
) -> dict[str, Any]:
    points = row.get("points") or []
    start_grid = lonlat_to_grid(row["start_lon"], row["start_lat"], origin_lon, origin_lat, grid_size_m)
    end_grid = lonlat_to_grid(row["end_lon"], row["end_lat"], origin_lon, origin_lat, grid_size_m)
    point_grids = [lonlat_to_grid(lon, lat, origin_lon, origin_lat, grid_size_m) for lon, lat in points]
    return {
        "start_grid": start_grid,
        "end_grid": end_grid,
        "bearing_deg": mean_bearing_deg(points),
        "turn_count": turn_count(points, turn_threshold),
        "path_entropy": sequence_entropy(point_grids),
    }


def build_features_from_cleaned(cleaned: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    feature_cfg = cfg.get("features", {})
    grid_size_m = float(feature_cfg.get("grid_size_m", 500))
    peak_hours = set(int(x) for x in feature_cfg.get("peak_hours", [7, 8, 9, 17, 18, 19]))
    night_hours = set(int(x) for x in feature_cfg.get("night_hours", [0, 1, 2, 3, 4, 5, 22, 23]))
    turn_threshold = float(feature_cfg.get("turn_angle_threshold_deg", 35))

    df = cleaned.copy()
    origin_lon = float(df["start_lon"].quantile(0.01)) if len(df) else -8.75
    origin_lat = float(df["start_lat"].quantile(0.01)) if len(df) else 41.05

    df["hour"] = df["timestamp_dt"].dt.hour.astype(int)
    df["weekday"] = df["timestamp_dt"].dt.weekday.astype(int)
    df["is_weekend"] = df["weekday"].isin([5, 6]).astype(int).astype(str)
    df["peak_hour"] = df["hour"].isin(peak_hours).astype(int).astype(str)
    df["day_night"] = np.where(df["hour"].isin(night_hours), "night", "day")
    df["time_slot"] = df["hour"].apply(_time_slot)

    if len(df) == 0:
        spatial_rows = []
    else:
        result_iter = Parallel(n_jobs=_cpu_minus_one(), backend="loky", batch_size=512, return_as="generator")(
            delayed(_compute_spatial_behavior_features)(row, origin_lon, origin_lat, grid_size_m, turn_threshold)
            for row in df.to_dict("records")
        )
        spatial_rows = list(tqdm(result_iter, total=len(df), desc="building spatial behavior features"))
    spatial = pd.DataFrame(spatial_rows, index=df.index, columns=[
        "start_grid", "end_grid", "bearing_deg", "turn_count", "path_entropy",
    ])
    for col in spatial.columns:
        df[col] = spatial[col]

    df["od_pair"] = df["start_grid"].astype(str) + "->" + df["end_grid"].astype(str)

    od_counts = df["od_pair"].value_counts().to_dict()
    start_counts = df["start_grid"].value_counts().to_dict()
    end_counts = df["end_grid"].value_counts().to_dict()
    n = max(len(df), 1)
    df["od_frequency"] = df["od_pair"].map(od_counts).fillna(0).astype(float) / n
    df["start_hotness"] = df["start_grid"].map(start_counts).fillna(0).astype(float) / n
    df["end_hotness"] = df["end_grid"].map(end_counts).fillna(0).astype(float) / n

    df["detour_ratio"] = np.where(
        df["straight_distance_m"] > 1,
        df["distance_m"] / df["straight_distance_m"].clip(lower=1),
        1.0,
    )
    df["detour_ratio"] = df["detour_ratio"].clip(lower=1.0, upper=20.0)

    long_q = float(feature_cfg.get("long_trip_quantile", 0.8))
    long_threshold = float(df["distance_m"].quantile(long_q)) if len(df) else 3000.0
    label_mode = str(feature_cfg.get("label_mode", "call_type"))
    if label_mode == "rule_based":
        df["target_mode"] = df.apply(lambda r: _rule_label(r, long_threshold), axis=1)
    else:
        df["target_mode"] = df["CALL_TYPE"].astype(str).replace({"nan": "unknown"})

    keep_cols = [
        "TRIP_ID", "CALL_TYPE", "ORIGIN_CALL", "ORIGIN_STAND", "TAXI_ID", "TIMESTAMP", "DAY_TYPE",
        "timestamp_dt", "hour", "weekday", "is_weekend", "peak_hour", "day_night", "time_slot",
        "start_lon", "start_lat", "end_lon", "end_lat", "start_grid", "end_grid", "od_pair",
        "duration_sec", "distance_m", "avg_speed_kmh", "straight_distance_m", "detour_ratio",
        "bearing_deg", "turn_count", "path_entropy", "od_frequency", "start_hotness", "end_hotness",
        "target_mode", "points",
    ]
    available = [c for c in keep_cols if c in df.columns]
    features = df[available].copy()
    features["points_json"] = features["points"].apply(lambda pts: str(pts))
    features = features.drop(columns=["points"])
    return features


def build_feature_table(input_path: str, output_path: str, cfg: dict[str, Any]) -> pd.DataFrame:
    raw = load_raw_dataframe(input_path, cfg)
    cleaned = clean_trips(raw, config_from_dict(cfg))
    features = build_features_from_cleaned(cleaned, cfg)
    final_path = write_table(features, output_path)
    logger.info("Feature table saved to %s with shape %s", final_path, features.shape)
    return features
