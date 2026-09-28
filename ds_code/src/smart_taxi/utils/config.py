from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import yaml


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load a YAML configuration file.

    Parameters
    ----------
    path:
        YAML path. If None, load config/default.yaml relative to project root when possible.
    """
    if path is None:
        candidate = Path.cwd() / "config" / "default.yaml"
        path = candidate if candidate.exists() else Path(__file__).resolve().parents[3] / "config" / "default.yaml"
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_get(cfg: Mapping[str, Any], key_path: str, default: Any = None) -> Any:
    cur: Any = cfg
    for part in key_path.split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return default
        cur = cur[part]
    return cur


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
