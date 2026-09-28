from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

PORTO_COLUMNS = [
    "TRIP_ID", "CALL_TYPE", "ORIGIN_CALL", "ORIGIN_STAND", "TAXI_ID",
    "TIMESTAMP", "DAY_TYPE", "MISSING_DATA", "POLYLINE",
]

DAY_TYPE_ALIASES = {"DAYTYPE": "DAY_TYPE", "DAY_TYPE": "DAY_TYPE"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    renamed = {}
    for c in df.columns:
        cu = str(c).strip().upper()
        if cu in DAY_TYPE_ALIASES:
            renamed[c] = DAY_TYPE_ALIASES[cu]
        else:
            renamed[c] = cu
    df = df.rename(columns=renamed)
    return df


def read_porto_csv(
    path: str | Path,
    has_header: bool = False,
    sep: str = ",",
    column_names: list[str] | None = None,
    sample_n: int | None = None,
    auto_drop_header_row: bool = True,
) -> pd.DataFrame:
    """Read Porto trajectory CSV.

    The project convention is headerless CSV by default. If a file actually contains
    the Porto header row, `auto_drop_header_row=True` detects and drops it.
    """
    path = Path(path)
    names = column_names or PORTO_COLUMNS
    if has_header:
        df = pd.read_csv(path, sep=sep, nrows=sample_n)
        df = _normalize_columns(df)
    else:
        df = pd.read_csv(path, sep=sep, header=None, names=names, nrows=sample_n)
        if auto_drop_header_row and len(df) > 0:
            first = [str(x).strip().upper() for x in df.iloc[0].tolist()]
            expected = [x.upper() for x in names]
            overlap = len(set(first) & set(expected))
            if overlap >= min(5, len(expected)):
                df = df.iloc[1:].reset_index(drop=True)
        df = _normalize_columns(df)
    required = {"TRIP_ID", "CALL_TYPE", "TIMESTAMP", "POLYLINE"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}. Available columns: {list(df.columns)}")
    return df


def parse_polyline(value) -> list[tuple[float, float]]:
    """Parse Porto POLYLINE into [(lon, lat), ...]. Invalid values return []."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        raw = value
    else:
        text = str(value).strip()
        if not text or text in {"[]", "nan", "NaN", "None"}:
            return []
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            try:
                raw = ast.literal_eval(text)
            except Exception:
                return []
    points: list[tuple[float, float]] = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            lon, lat = float(item[0]), float(item[1])
            if -180 <= lon <= 180 and -90 <= lat <= 90:
                points.append((lon, lat))
        except Exception:
            continue
    return points


def write_table(df: pd.DataFrame, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        try:
            df.to_parquet(path, index=False)
        except Exception:
            fallback = path.with_suffix(".csv")
            df.to_csv(fallback, index=False)
            return fallback
    else:
        df.to_csv(path, index=False)
    return path


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)
