from __future__ import annotations

import argparse
from pathlib import Path

from smart_taxi.data.features import build_feature_table
from smart_taxi.models.train import train_behavior_model
from smart_taxi.models.shap_analysis import run_shap_analysis
from smart_taxi.od.analysis import run_od_analysis
from smart_taxi.routing.network import build_osm_network
from smart_taxi.routing.edge_stats import build_edge_statistics
from smart_taxi.utils.config import load_config, ensure_dir


def main():
    ap = argparse.ArgumentParser(description="Run the main end-to-end smart taxi pipeline")
    ap.add_argument("--input", required=True)
    ap.add_argument("--network-place", default=None)
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--output-root", default="outputs/full_run")
    ap.add_argument("--skip-network", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    root = ensure_dir(args.output_root)
    features = root / "features.parquet"
    model_dir = root / "model"
    shap_dir = root / "shap"
    od_dir = root / "od"
    network = root / "network.graphml"
    edge_stats = root / "edge_stats.csv"

    build_feature_table(args.input, str(features), cfg)
    train_behavior_model(str(features), str(model_dir), cfg)
    run_shap_analysis(str(features), str(model_dir), str(shap_dir), cfg)
    run_od_analysis(str(features), str(od_dir), cfg)
    if not args.skip_network:
        build_osm_network(str(network), cfg, place=args.network_place)
        build_edge_statistics(str(features), str(network), str(edge_stats), cfg)


if __name__ == "__main__":
    main()
