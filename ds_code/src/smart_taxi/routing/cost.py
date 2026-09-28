from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


def minmax_normalize(series: pd.Series, default: float = 0.0) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)
    lo, hi = s.min(), s.max()
    if pd.isna(lo) or pd.isna(hi) or abs(hi - lo) < 1e-12:
        return pd.Series(default, index=s.index, dtype=float)
    return (s - lo) / (hi - lo)


@dataclass
class CostParams:
    alpha_distance: float = 0.30
    beta_time: float = 0.45
    gamma_road_penalty: float = 0.10
    delta_risk: float = 0.15
    lambda_congestion: float = 0.55
    lambda_pickup_gap: float = 0.05
    smoothness_penalty: float = 0.03


@dataclass
class DriverParams:
    omega_pickup: float = 0.55
    omega_time: float = 0.25
    omega_congestion: float = 0.10
    omega_empty: float = 0.10
    distance_floor: float = 0.05


def passenger_cost_table(edge_stats: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    params = CostParams(**{k: float(v) for k, v in cfg.get("cost", {}).get("passenger", {}).items() if k in CostParams.__annotations__})
    df = edge_stats.copy()
    df["d_norm"] = minmax_normalize(df.get("length_m", 0), default=0.0)
    df["tau_norm"] = minmax_normalize(df.get("estimated_time_sec", 0), default=0.0)
    df["g_norm"] = minmax_normalize(df.get("road_penalty", 0), default=0.0)
    df["r_norm"] = minmax_normalize(df.get("risk_index", 0), default=0.0)
    df["q_norm"] = minmax_normalize(df.get("congestion_index", 1), default=0.0)
    df["p_pickup"] = pd.to_numeric(df.get("pickup_probability", 0), errors="coerce").fillna(0).clip(0, 1)
    base = (
        params.alpha_distance * df["d_norm"]
        + params.beta_time * df["tau_norm"]
        + params.gamma_road_penalty * df["g_norm"]
        + params.delta_risk * df["r_norm"]
    )
    multiplier = 1 + params.lambda_congestion * df["q_norm"] + params.lambda_pickup_gap * (1 - df["p_pickup"])
    df["smart_cost"] = (base * multiplier + 1e-6).astype(float)
    return df


def driver_cost_table(edge_stats: pd.DataFrame, cfg: dict[str, Any]) -> pd.DataFrame:
    params = DriverParams(**{k: float(v) for k, v in cfg.get("cost", {}).get("driver", {}).items() if k in DriverParams.__annotations__})
    df = edge_stats.copy()
    tau = minmax_normalize(df.get("estimated_time_sec", 0), default=0.0)
    q = minmax_normalize(df.get("congestion_index", 1), default=0.0)
    empty = minmax_normalize(df.get("length_m", 0), default=0.0)
    pickup = pd.to_numeric(df.get("pickup_probability", 0), errors="coerce").fillna(0).clip(0, 1)
    utility = params.omega_pickup * pickup - params.omega_time * tau - params.omega_congestion * q - params.omega_empty * empty
    # Dijkstra needs non-negative costs. Transform high utility into low positive cost.
    utility_norm = minmax_normalize(pd.Series(utility), default=0.5)
    df["smart_cost"] = (1.0 - utility_norm + params.distance_floor * empty + 1e-6).astype(float)
    df["driver_utility"] = utility.astype(float)
    return df


def baseline_cost_table(edge_stats: pd.DataFrame, baseline: str) -> pd.DataFrame:
    df = edge_stats.copy()
    if baseline == "shortest_distance":
        df["smart_cost"] = pd.to_numeric(df.get("length_m", 1), errors="coerce").fillna(1).clip(lower=1)
    elif baseline == "shortest_time":
        df["smart_cost"] = pd.to_numeric(df.get("freeflow_time_sec", 1), errors="coerce").fillna(1).clip(lower=1)
    elif baseline == "congestion_only":
        df["smart_cost"] = pd.to_numeric(df.get("estimated_time_sec", 1), errors="coerce").fillna(1).clip(lower=1)
    elif baseline == "pickup_only":
        p = pd.to_numeric(df.get("pickup_probability", 0), errors="coerce").fillna(0).clip(0, 1)
        df["smart_cost"] = 1.0 - p + 1e-6
    else:
        raise ValueError(f"Unknown baseline: {baseline}")
    return df


def build_cost_table(edge_stats: pd.DataFrame, profile: str, cfg: dict[str, Any]) -> pd.DataFrame:
    if profile == "passenger" or profile == "composite_passenger":
        return passenger_cost_table(edge_stats, cfg)
    if profile == "driver" or profile == "composite_driver":
        return driver_cost_table(edge_stats, cfg)
    if profile in {"shortest_distance", "shortest_time", "congestion_only", "pickup_only"}:
        return baseline_cost_table(edge_stats, profile)
    raise ValueError(f"Unknown cost profile: {profile}")
