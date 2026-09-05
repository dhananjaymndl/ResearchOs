import json
import time
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    precision_score,
    recall_score,
    roc_auc_score,
)

from researchos.core.config import settings
from researchos.core.logging import get_logger
from researchos.datasets.preprocessing import build_preprocessing_pipeline, encode_target
from researchos.experiments.schemas import ExperimentResult, ExperimentSpec
from researchos.models.registry import build_model, get_model_definition

logger = get_logger(__name__)


def run_experiment(
    spec: ExperimentSpec,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    target_column: str,
    numeric_columns: list[str],
    categorical_columns: list[str],
    artifact_dir: Path,
) -> tuple[ExperimentResult, dict]:
    """Executes one experiment end to end. Returns (result, artifact_paths)."""
    experiment_id = spec.experiment_id or f"exp_{uuid.uuid4().hex[:20]}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    try:
        y_train = encode_target(train_df[target_column])
        y_val = encode_target(val_df[target_column])
        X_train = train_df[numeric_columns + categorical_columns]
        X_val = val_df[numeric_columns + categorical_columns]

        definition = get_model_definition(spec.model)
        scale_numeric = spec.preprocessing.scale_numeric or definition.requires_scaling
        preprocessor = build_preprocessing_pipeline(
            numeric_columns,
            categorical_columns,
            scale_numeric=scale_numeric,
            encode_categorical=spec.preprocessing.encode_categorical,
        )

        X_train_t = preprocessor.fit_transform(X_train)
        X_val_t = preprocessor.transform(X_val)

        model = build_model(spec.model, spec.hyperparameters)

        start = time.perf_counter()
        model.fit(X_train_t, y_train)
        training_time = time.perf_counter() - start

        infer_start = time.perf_counter()
        y_pred = model.predict(X_val_t)
        infer_elapsed_ms = (time.perf_counter() - infer_start) * 1000 / max(len(y_val), 1)

        if hasattr(model, "predict_proba"):
            y_score = model.predict_proba(X_val_t)[:, 1]
        else:
            y_score = y_pred

        metrics = {
            "accuracy": float(accuracy_score(y_val, y_pred)),
            "precision": float(precision_score(y_val, y_pred, zero_division=0)),
            "recall": float(recall_score(y_val, y_pred, zero_division=0)),
            "f1": float(f1_score(y_val, y_pred, zero_division=0)),
        }
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_val, y_score))
        except ValueError:
            metrics["roc_auc"] = 0.0

        cm = confusion_matrix(y_val, y_pred, labels=[0, 1]).tolist()

        class_precision, class_recall, class_f1, class_support = precision_recall_fscore_support(
            y_val, y_pred, labels=[0, 1], zero_division=0
        )
        class_report = {
            "0": {
                "precision": float(class_precision[0]),
                "recall": float(class_recall[0]),
                "f1": float(class_f1[0]),
                "support": int(class_support[0]),
            },
            "1": {
                "precision": float(class_precision[1]),
                "recall": float(class_recall[1]),
                "f1": float(class_f1[1]),
                "support": int(class_support[1]),
            },
        }

        feature_importance = None
        if definition.supports_feature_importance and hasattr(model, "feature_importances_"):
            try:
                feature_names = preprocessor.get_feature_names_out()
                importances = model.feature_importances_
                feature_importance = {
                    str(name): float(score)
                    for name, score in sorted(
                        zip(feature_names, importances), key=lambda x: -x[1]
                    )[:20]
                }
            except Exception:
                feature_importance = None

        artifact_paths = {}
        cm_path = artifact_dir / "confusion_matrix.json"
        cm_path.write_text(json.dumps(cm))
        artifact_paths["confusion_matrix"] = str(cm_path)

        if feature_importance:
            fi_path = artifact_dir / "feature_importance.json"
            fi_path.write_text(json.dumps(feature_importance))
            artifact_paths["feature_importance"] = str(fi_path)

        result = ExperimentResult(
            experiment_id=experiment_id,
            status="completed",
            metrics=metrics,
            training_time_seconds=round(training_time, 4),
            inference_latency_ms=round(infer_elapsed_ms, 4),
            confusion_matrix=cm,
            class_report=class_report,
            feature_importance=feature_importance,
        )
        return result, artifact_paths

    except Exception as exc:  # noqa: BLE001 - experiment failures must not crash the project
        logger.exception("Experiment %s failed", experiment_id)
        result = ExperimentResult(
            experiment_id=experiment_id,
            status="failed",
            failure_reason=str(exc),
        )
        return result, {}
