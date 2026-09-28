from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler, LabelEncoder

from smart_taxi.data.io import read_table
from smart_taxi.utils.config import ensure_dir
from smart_taxi.utils.logging import get_logger

logger = get_logger(__name__)


def _import_xgboost():
    try:
        from xgboost import XGBClassifier
        return XGBClassifier
    except Exception as exc:
        raise ImportError("xgboost is required for train-model. Install requirements.txt first.") from exc


def select_columns(df: pd.DataFrame, cfg: dict[str, Any]) -> tuple[list[str], list[str], str]:
    feature_cfg = cfg.get("features", {})
    target = str(feature_cfg.get("target_column", "target_mode"))
    cat_cols = [c for c in feature_cfg.get("categorical_columns", []) if c in df.columns]
    num_cols = [c for c in feature_cfg.get("numeric_columns", []) if c in df.columns]
    if target not in df.columns:
        raise ValueError(f"Target column {target!r} not found in feature table.")
    return cat_cols, num_cols, target


def make_preprocessor(cat_cols: list[str], num_cols: list[str]) -> ColumnTransformer:
    try:
        ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # scikit-learn < 1.2
        ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", ohe),
    ])
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    return ColumnTransformer([
        ("cat", categorical, cat_cols),
        ("num", numeric, num_cols),
    ], remainder="drop")


def train_behavior_model(features_path: str, output_dir: str, cfg: dict[str, Any]) -> dict[str, Any]:
    XGBClassifier = _import_xgboost()
    output = ensure_dir(output_dir)
    df = read_table(features_path)
    cat_cols, num_cols, target_col = select_columns(df, cfg)
    data = df[cat_cols + num_cols + [target_col]].dropna(subset=[target_col]).copy()
    if data[target_col].nunique() < 2:
        raise ValueError("At least two target classes are required.")

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(data[target_col].astype(str))
    X = data[cat_cols + num_cols]

    model_cfg = cfg.get("model", {})
    test_size = float(model_cfg.get("test_size", 0.2))
    random_state = int(cfg.get("project", {}).get("random_state", 42))
    stratify = y if min(np.bincount(y)) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )

    pre = make_preprocessor(cat_cols, num_cols)
    clf = XGBClassifier(
        n_estimators=int(model_cfg.get("n_estimators", 350)),
        max_depth=int(model_cfg.get("max_depth", 6)),
        learning_rate=float(model_cfg.get("learning_rate", 0.05)),
        subsample=float(model_cfg.get("subsample", 0.85)),
        colsample_bytree=float(model_cfg.get("colsample_bytree", 0.85)),
        objective=str(model_cfg.get("objective", "multi:softprob")),
        eval_metric=str(model_cfg.get("eval_metric", "mlogloss")),
        n_jobs=int(model_cfg.get("n_jobs", -1)),
        random_state=random_state,
        tree_method="hist",
    )
    pipe = Pipeline([("preprocessor", pre), ("model", clf)])
    pipe.fit(X_train, y_train)

    pred = pipe.predict(X_test)
    metrics: dict[str, Any] = {
        "n_samples": int(len(data)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "classes": label_encoder.classes_.tolist(),
        "categorical_columns": cat_cols,
        "numeric_columns": num_cols,
        "target_column": target_col,
        "accuracy": float(accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, average="macro", zero_division=0)),
        "macro_precision": float(precision_score(y_test, pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_test, pred, average="macro", zero_division=0)),
        "classification_report": classification_report(y_test, pred, target_names=label_encoder.classes_, zero_division=0, output_dict=True),
    }
    if hasattr(pipe, "predict_proba"):
        try:
            proba = pipe.predict_proba(X_test)
            if proba.shape[1] == 2:
                metrics["auc_ovr"] = float(roc_auc_score(y_test, proba[:, 1]))
            else:
                metrics["auc_ovr"] = float(roc_auc_score(y_test, proba, multi_class="ovr", average="macro"))
        except Exception as exc:
            metrics["auc_ovr_error"] = str(exc)

    joblib.dump({"pipeline": pipe, "label_encoder": label_encoder, "config": cfg}, output / "model.joblib")
    with (output / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    pd.DataFrame({"y_true": label_encoder.inverse_transform(y_test), "y_pred": label_encoder.inverse_transform(pred)}).to_csv(
        output / "predictions.csv", index=False
    )
    logger.info("Model saved to %s", output)
    return metrics
