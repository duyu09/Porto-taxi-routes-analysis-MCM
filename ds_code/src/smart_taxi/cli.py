from __future__ import annotations

import argparse
from pathlib import Path

from smart_taxi.utils.config import load_config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="smart-taxi", description="Smart-city taxi behavior modeling and route optimization")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build-features", help="Build order-level feature table")
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("train-model", help="Train XGBoost behavior classifier")
    p.add_argument("--features", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("shap-analysis", help="Run SHAP explanation for trained model")
    p.add_argument("--features", required=True)
    p.add_argument("--model-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("od-analysis", help="Build OD matrix and hotspot outputs")
    p.add_argument("--features", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("build-network", help="Download/build OSM drive network")
    p.add_argument("--place", default=None)
    p.add_argument("--bbox", nargs=4, type=float, metavar=("NORTH", "SOUTH", "EAST", "WEST"), default=None)
    p.add_argument("--output", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("build-edge-stats", help="Build edge-level statistics from matched trajectories")
    p.add_argument("--features", required=True)
    p.add_argument("--network", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("plan-route", help="Plan passenger or driver route with dynamic costs")
    p.add_argument("--network", required=True)
    p.add_argument("--edge-stats", required=True)
    p.add_argument("--origin-lat", type=float, required=True)
    p.add_argument("--origin-lon", type=float, required=True)
    p.add_argument("--dest-lat", type=float, required=True)
    p.add_argument("--dest-lon", type=float, required=True)
    p.add_argument("--time", required=True)
    p.add_argument("--profile", default="passenger")
    p.add_argument("--output", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("compare-baselines", help="Compare route baselines for one OD query")
    p.add_argument("--network", required=True)
    p.add_argument("--edge-stats", required=True)
    p.add_argument("--origin-lat", type=float, required=True)
    p.add_argument("--origin-lon", type=float, required=True)
    p.add_argument("--dest-lat", type=float, required=True)
    p.add_argument("--dest-lon", type=float, required=True)
    p.add_argument("--time", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--config", default="config/default.yaml")

    p = sub.add_parser("ablation", help="Run passenger cost ablation for one OD query")
    p.add_argument("--network", required=True)
    p.add_argument("--edge-stats", required=True)
    p.add_argument("--origin-lat", type=float, required=True)
    p.add_argument("--origin-lon", type=float, required=True)
    p.add_argument("--dest-lat", type=float, required=True)
    p.add_argument("--dest-lon", type=float, required=True)
    p.add_argument("--time", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--config", default="config/default.yaml")

    args = parser.parse_args(argv)
    cfg = load_config(args.config)

    if args.command == "build-features":
        from smart_taxi.data.features import build_feature_table
        build_feature_table(args.input, args.output, cfg)
    elif args.command == "train-model":
        from smart_taxi.models.train import train_behavior_model
        train_behavior_model(args.features, args.output_dir, cfg)
    elif args.command == "shap-analysis":
        from smart_taxi.models.shap_analysis import run_shap_analysis
        run_shap_analysis(args.features, args.model_dir, args.output_dir, cfg)
    elif args.command == "od-analysis":
        from smart_taxi.od.analysis import run_od_analysis
        run_od_analysis(args.features, args.output_dir, cfg)
    elif args.command == "build-network":
        from smart_taxi.routing.network import build_osm_network
        bbox = tuple(args.bbox) if args.bbox is not None else None
        build_osm_network(args.output, cfg, place=args.place, bbox=bbox)
    elif args.command == "build-edge-stats":
        from smart_taxi.routing.edge_stats import build_edge_statistics
        build_edge_statistics(args.features, args.network, args.output, cfg)
    elif args.command == "plan-route":
        from smart_taxi.routing.planner import plan_route
        plan_route(args.network, args.edge_stats, args.origin_lat, args.origin_lon, args.dest_lat, args.dest_lon, args.time, args.profile, args.output, cfg)
    elif args.command == "compare-baselines":
        from smart_taxi.experiments.baselines import compare_route_baselines
        compare_route_baselines(args.network, args.edge_stats, args.origin_lat, args.origin_lon, args.dest_lat, args.dest_lon, args.time, args.output_dir, cfg)
    elif args.command == "ablation":
        from smart_taxi.experiments.ablation import run_cost_ablation
        run_cost_ablation(args.network, args.edge_stats, args.origin_lat, args.origin_lon, args.dest_lat, args.dest_lon, args.time, args.output_dir, cfg)


if __name__ == "__main__":
    main()
