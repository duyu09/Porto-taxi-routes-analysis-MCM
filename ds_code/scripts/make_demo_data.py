from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path
from tqdm import tqdm


def make_polyline(start_lon, start_lat, end_lon, end_lat, n):
    pts = []
    for i in range(n):
        t = i / max(n - 1, 1)
        lon = start_lon * (1 - t) + end_lon * t + random.uniform(-0.0006, 0.0006)
        lat = start_lat * (1 - t) + end_lat * t + random.uniform(-0.0006, 0.0006)
        pts.append([round(lon, 6), round(lat, 6)])
    return json.dumps(pts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/raw/demo_no_header.csv")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--header", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    base_ts = 1372636800  # 2013-07-01 UTC
    centers = [(-8.61099, 41.14961), (-8.62195, 41.16214), (-8.62910, 41.15794), (-8.58500, 41.14800)]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if args.header:
            writer.writerow(["TRIP_ID", "CALL_TYPE", "ORIGIN_CALL", "ORIGIN_STAND", "TAXI_ID", "TIMESTAMP", "DAY_TYPE", "MISSING_DATA", "POLYLINE"])
        for i in tqdm(range(args.n), desc="generating demo trips"):
            s = random.choice(centers)
            e = random.choice(centers)
            while e == s:
                e = random.choice(centers)
            npts = random.randint(8, 45)
            call = random.choice(["A", "B", "C"])
            ts = base_ts + random.randint(0, 60 * 60 * 24 * 30)
            writer.writerow([
                f"demo_{i}", call, "" if call != "A" else random.randint(1, 50), "" if call != "B" else random.randint(1, 30),
                random.randint(1000, 1100), ts, "A", "FALSE", make_polyline(s[0], s[1], e[0], e[1], npts)
            ])
    print(out)


if __name__ == "__main__":
    main()
