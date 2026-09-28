from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib.pyplot as plt

from smart_taxi.data.io import read_table
from smart_taxi.utils.config import ensure_dir
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def run_od_analysis(features_path: str, output_dir: str, cfg: dict[str, Any]) -> dict[str, pd.DataFrame]:
    output = ensure_dir(output_dir)
    df = read_table(features_path)
    required = {"start_grid", "end_grid", "time_slot"}
    if not required.issubset(df.columns):
        raise ValueError(f"Feature table must contain {required}")

    od = (
        df.groupby(["time_slot", "start_grid", "end_grid"])
        .size()
        .rename("trip_count")
        .reset_index()
        .sort_values("trip_count", ascending=False)
    )
    od["od_pair"] = od["start_grid"].astype(str) + "->" + od["end_grid"].astype(str)
    od.to_csv(output / "od_matrix.csv", index=False)

    top_k = int(cfg.get("od", {}).get("top_k_pairs", 50))
    top_pairs = od.groupby("od_pair", as_index=False)["trip_count"].sum().sort_values("trip_count", ascending=False).head(top_k)
    top_pairs.to_csv(output / "top_od_pairs.csv", index=False)

    start_hot = df.groupby(["time_slot", "start_grid"]).size().rename("pickup_count").reset_index()
    end_hot = df.groupby(["time_slot", "end_grid"]).size().rename("dropoff_count").reset_index()
    start_hot.to_csv(output / "pickup_hotspots.csv", index=False)
    end_hot.to_csv(output / "dropoff_hotspots.csv", index=False)

    plt.figure(figsize=(10, max(4, top_k * 0.12)))
    plot_data = top_pairs.iloc[::-1]
    plt.barh(plot_data["od_pair"], plot_data["trip_count"])
    plt.xlabel("Trip count")
    plt.title(f"Top {top_k} OD Pairs")
    plt.tight_layout()
    plt.savefig(output / "top_od_pairs.png", dpi=180)
    plt.close()

    logger.info("OD outputs saved to %s", output)
    return {"od": od, "top_pairs": top_pairs, "pickup_hotspots": start_hot, "dropoff_hotspots": end_hot}
