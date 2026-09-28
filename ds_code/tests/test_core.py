from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from smart_taxi.data.io import parse_polyline, read_porto_csv
from smart_taxi.utils.geo import haversine_m, path_distance_m, lonlat_to_grid
from smart_taxi.routing.cost import passenger_cost_table, driver_cost_table


def test_parse_polyline():
    pts = parse_polyline('[[-8.61,41.14],[-8.62,41.15]]')
    assert len(pts) == 2
    assert pts[0] == (-8.61, 41.14)


def test_haversine_positive():
    assert haversine_m(-8.61, 41.14, -8.62, 41.15) > 0
    assert path_distance_m([(-8.61, 41.14), (-8.62, 41.15)]) > 0


def test_headerless_read(tmp_path: Path):
    p = tmp_path / "demo.csv"
    p.write_text('id1,A,,,1,1372636800,A,FALSE,"[[-8.61,41.14],[-8.62,41.15]]"\n', encoding="utf-8")
    df = read_porto_csv(p, has_header=False)
    assert list(df.columns)[:3] == ["TRIP_ID", "CALL_TYPE", "ORIGIN_CALL"]
    assert df.iloc[0]["CALL_TYPE"] == "A"


def test_cost_tables():
    edge_stats = pd.DataFrame({
        "length_m": [100, 200],
        "estimated_time_sec": [20, 60],
        "road_penalty": [0.1, 0.4],
        "risk_index": [0.2, 0.7],
        "congestion_index": [1.0, 2.0],
        "pickup_probability": [0.8, 0.1],
    })
    cfg = {"cost": {"passenger": {}, "driver": {}}}
    pc = passenger_cost_table(edge_stats, cfg)
    dc = driver_cost_table(edge_stats, cfg)
    assert (pc["smart_cost"] > 0).all()
    assert (dc["smart_cost"] > 0).all()
