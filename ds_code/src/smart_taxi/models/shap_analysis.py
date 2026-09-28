from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from smart_taxi.data.io import read_table
from smart_taxi.models.train import select_columns
from smart_taxi.utils.config import ensure_dir
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def _feature_names(preprocessor) -> list[str]:
    try:
        return list(preprocessor.get_feature_names_out())
    except Exception:
        return [f"f{i}" for i in range(getattr(preprocessor, "n_features_in_", 0))]


def run_shap_analysis(features_path: str, model_dir: str, output_dir: str, cfg: dict[str, Any]) -> pd.DataFrame:
    try:
        import shap
    except Exception as exc:
        raise ImportError("shap is required for shap-analysis. Install requirements.txt first.") from exc

    output = ensure_dir(output_dir)
    bundle = joblib.load(Path(model_dir) / "model.joblib")
    pipe = bundle["pipeline"]
    label_encoder = bundle["label_encoder"]

    df = read_table(features_path)
    cat_cols, num_cols, target_col = select_columns(df, cfg)
    X = df[cat_cols + num_cols].copy()
    y = df[target_col].astype(str) if target_col in df.columns else None

    sample_size = int(cfg.get("shap", {}).get("sample_size", 2000))
    if len(X) > sample_size:
        X_sample = X.sample(n=sample_size, random_state=int(cfg.get("project", {}).get("random_state", 42)))
    else:
        X_sample = X

    pre = pipe.named_steps["preprocessor"]
    model = pipe.named_steps["model"]
    Xt = pre.transform(X_sample)
    names = _feature_names(pre)
    Xt_df = pd.DataFrame(Xt, columns=names)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(Xt_df)
    if isinstance(shap_values, list):
        abs_mean = np.mean([np.abs(v).mean(axis=0) for v in shap_values], axis=0)
    else:
        arr = np.asarray(shap_values)
        if arr.ndim == 3:
            abs_mean = np.abs(arr).mean(axis=(0, 2))
        else:
            abs_mean = np.abs(arr).mean(axis=0)
    importance = pd.DataFrame({"feature": names, "mean_abs_shap": abs_mean}).sort_values("mean_abs_shap", ascending=False)
    importance.to_csv(output / "shap_feature_importance.csv", index=False)

    top = importance.head(int(cfg.get("shap", {}).get("max_display", 25))).iloc[::-1]
    plt.figure(figsize=(9, max(5, len(top) * 0.28)))
    plt.barh(top["feature"], top["mean_abs_shap"])
    plt.xlabel("Mean |SHAP value|")
    plt.title("SHAP Feature Importance")
    plt.tight_layout()
    plt.savefig(output / "shap_feature_importance.png", dpi=180)
    plt.close()

    # 保存可供论文附录使用的样本级解释矩阵（只保存前若干列，避免文件过大）
    top_features = importance.head(50)["feature"].tolist()
    shap_matrix = pd.DataFrame(index=range(len(Xt_df)))
    if isinstance(shap_values, list):
        for class_idx, class_name in enumerate(label_encoder.classes_):
            cls_values = pd.DataFrame(shap_values[class_idx], columns=names)[top_features]
            cls_values.columns = [f"{class_name}::{c}" for c in cls_values.columns]
            shap_matrix = pd.concat([shap_matrix, cls_values], axis=1)
    else:
        arr = np.asarray(shap_values)
        if arr.ndim == 2:
            shap_matrix = pd.DataFrame(arr, columns=names)[top_features]
    shap_matrix.to_csv(output / "shap_values_top_features.csv", index=False)

    logger.info("SHAP outputs saved to %s", output)
    return importance
