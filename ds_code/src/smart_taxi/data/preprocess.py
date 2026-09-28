from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import os

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from tqdm import tqdm

from smart_taxi.data.io import parse_polyline, read_porto_csv
from smart_taxi.utils.geo import path_distance_m, haversine_m
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CleanConfig:
    gps_interval_seconds: int = 15
    min_points: int = 2
    max_duration_seconds: int = 10800
    min_distance_m: float = 50.0
    max_speed_kmh: float = 160.0
    timezone: str = "Europe/Lisbon"


def config_from_dict(cfg: dict[str, Any]) -> CleanConfig:
    data = cfg.get("data", {})
    return CleanConfig(
        gps_interval_seconds=int(data.get("gps_interval_seconds", 15)),
        min_points=int(data.get("min_points", 2)),
        max_duration_seconds=int(data.get("max_duration_seconds", 10800)),
        min_distance_m=float(data.get("min_distance_m", 50)),
        max_speed_kmh=float(data.get("max_speed_kmh", 160)),
        timezone=str(data.get("timezone", "Europe/Lisbon")),
    )


def load_raw_dataframe(path: str, cfg: dict[str, Any]) -> pd.DataFrame:
    data_cfg = cfg.get("data", {})
    return read_porto_csv(
        path,
        has_header=bool(data_cfg.get("has_header", False)),
        sep=str(data_cfg.get("sep", ",")),
        column_names=list(data_cfg.get("column_names", [])) or None,
        sample_n=data_cfg.get("sample_n"),
        auto_drop_header_row=bool(data_cfg.get("auto_drop_header_row", True)),
    )


def _cpu_minus_one() -> int:
    return max((os.cpu_count() or 1) - 1, 1)


def _compute_basic_trip_features(polyline_value: Any, gps_interval_seconds: int) -> dict[str, Any]:
    points = parse_polyline(polyline_value)
    n_points = len(points)
    duration_sec = max(n_points - 1, 0) * gps_interval_seconds
    distance_m = path_distance_m(points)

    start_lon = points[0][0] if points else np.nan
    start_lat = points[0][1] if points else np.nan
    end_lon = points[-1][0] if points else np.nan
    end_lat = points[-1][1] if points else np.nan

    straight_distance_m = (
        haversine_m(start_lon, start_lat, end_lon, end_lat)
        if pd.notna(start_lon) and pd.notna(end_lon)
        else np.nan
    )

    return {
        "points": points,
        "n_points": n_points,
        "duration_sec": duration_sec,
        "distance_m": distance_m,
        "start_lon": start_lon,
        "start_lat": start_lat,
        "end_lon": end_lon,
        "end_lat": end_lat,
        "straight_distance_m": straight_distance_m,
    }


def enrich_raw_trips(df: pd.DataFrame, clean_cfg: CleanConfig) -> pd.DataFrame:
    """Parse polylines and compute basic physical trip quantities."""
    out = df.copy()
    if len(out) == 0:
        rows = []
    else:
        result_iter = Parallel(n_jobs=_cpu_minus_one(), backend="loky", batch_size=512, return_as="generator")(
            delayed(_compute_basic_trip_features)(value, clean_cfg.gps_interval_seconds)
            for value in out["POLYLINE"]
        )
        rows = list(tqdm(result_iter, total=len(out), desc="preprocessing trips"))
    basic = pd.DataFrame(rows, index=out.index, columns=[
        "points", "n_points", "duration_sec", "distance_m",
        "start_lon", "start_lat", "end_lon", "end_lat", "straight_distance_m",
    ])
    for col in basic.columns:
        out[col] = basic[col]

    out["avg_speed_kmh"] = np.where(out["duration_sec"] > 0, out["distance_m"] / out["duration_sec"] * 3.6, 0.0)

    # Timestamp parsing: Porto timestamps are Unix seconds.
    out["timestamp_dt_utc"] = pd.to_datetime(pd.to_numeric(out["TIMESTAMP"], errors="coerce"), unit="s", utc=True)
    try:
        out["timestamp_dt"] = out["timestamp_dt_utc"].dt.tz_convert(clean_cfg.timezone)
    except Exception:
        out["timestamp_dt"] = out["timestamp_dt_utc"]
    return out


def clean_trips(df: pd.DataFrame, clean_cfg: CleanConfig) -> pd.DataFrame:
    """Remove impossible or low-quality trajectories while preserving enough rows for modeling."""
    out = enrich_raw_trips(df, clean_cfg)
    if "MISSING_DATA" in out.columns:
        missing_text = out["MISSING_DATA"].astype(str).str.upper()
        out = out[~missing_text.isin(["TRUE", "1", "YES"])]
    mask = (
        (out["n_points"] >= clean_cfg.min_points)
        & (out["duration_sec"] <= clean_cfg.max_duration_seconds)
        & (out["distance_m"] >= clean_cfg.min_distance_m)
        & (out["avg_speed_kmh"] <= clean_cfg.max_speed_kmh)
        & out["start_lon"].between(-9.5, -7.0)
        & out["end_lon"].between(-9.5, -7.0)
        & out["start_lat"].between(40.0, 42.5)
        & out["end_lat"].between(40.0, 42.5)
    )
    cleaned = out.loc[mask].reset_index(drop=True)
    logger.info("Cleaned trips: %s -> %s", len(df), len(cleaned))
    return cleaned
