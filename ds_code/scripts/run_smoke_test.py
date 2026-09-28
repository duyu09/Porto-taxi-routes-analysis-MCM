from __future__ import annotations

import subprocess
from pathlib import Path


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    root = Path(__file__).resolve().parents[1]
    demo = root / "data" / "raw" / "demo_no_header.csv"
    features = root / "outputs" / "smoke" / "features.csv"
    model_dir = root / "outputs" / "smoke" / "model"
    od_dir = root / "outputs" / "smoke" / "od"
    run(["python", str(root / "scripts" / "make_demo_data.py"), "--out", str(demo), "--n", "120"])
    run(["python", "-m", "smart_taxi.cli", "build-features", "--input", str(demo), "--output", str(features), "--config", str(root / "config" / "default.yaml")])
    run(["python", "-m", "smart_taxi.cli", "train-model", "--features", str(features), "--output-dir", str(model_dir), "--config", str(root / "config" / "default.yaml")])
    run(["python", "-m", "smart_taxi.cli", "od-analysis", "--features", str(features), "--output-dir", str(od_dir), "--config", str(root / "config" / "default.yaml")])
    print("Smoke test finished.")


if __name__ == "__main__":
    main()
