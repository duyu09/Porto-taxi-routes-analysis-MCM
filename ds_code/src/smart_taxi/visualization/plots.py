from __future__ import annotations

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def barh_from_csv(csv_path: str, x_col: str, y_col: str, output_path: str, title: str = "") -> Path:
    df = pd.read_csv(csv_path)
    data = df.sort_values(x_col).tail(30)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(9, max(4, len(data) * 0.25)))
    plt.barh(data[y_col].astype(str), data[x_col])
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out, dpi=180)
    plt.close()
    return out
