from dataclasses import dataclass, field
from typing import Any, Callable

from lightgbm import LGBMClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from xgboost import XGBClassifier


@dataclass
class HyperparamSpec:
    type: str  # "int" | "float" | "bool" | "categorical"
    min: float | int | None = None
    max: float | int | None = None
    choices: list[Any] | None = None
    default: Any = None


@dataclass
class ModelDefinition:
    name: str
    build_fn: Callable[[dict], Any]
    hyperparameters: dict[str, HyperparamSpec] = field(default_factory=dict)
    requires_scaling: bool = False
    supports_feature_importance: bool = True


def _logistic_regression(params: dict) -> LogisticRegression:
    return LogisticRegression(
        C=params.get("C", 1.0),
        max_iter=params.get("max_iter", 1000),
        class_weight=params.get("class_weight"),
        random_state=42,
    )


def _random_forest(params: dict) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=params.get("n_estimators", 300),
        max_depth=params.get("max_depth"),
        min_samples_leaf=params.get("min_samples_leaf", 1),
        class_weight=params.get("class_weight"),
        random_state=42,
        n_jobs=-1,
    )


def _xgboost(params: dict) -> XGBClassifier:
    return XGBClassifier(
        max_depth=params.get("max_depth", 6),
        learning_rate=params.get("learning_rate", 0.1),
        n_estimators=params.get("n_estimators", 300),
        scale_pos_weight=params.get("scale_pos_weight", 1),
        subsample=params.get("subsample", 1.0),
        colsample_bytree=params.get("colsample_bytree", 1.0),
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )


def _lightgbm(params: dict) -> LGBMClassifier:
    return LGBMClassifier(
        max_depth=params.get("max_depth", -1),
        learning_rate=params.get("learning_rate", 0.1),
        n_estimators=params.get("n_estimators", 300),
        class_weight=params.get("class_weight"),
        num_leaves=params.get("num_leaves", 31),
        random_state=42,
        n_jobs=-1,
        verbosity=-1,
    )


def _hist_gradient_boosting(params: dict) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_depth=params.get("max_depth"),
        learning_rate=params.get("learning_rate", 0.1),
        max_iter=params.get("max_iter", 200),
        random_state=42,
    )


def _mlp(params: dict) -> MLPClassifier:
    hidden = params.get("hidden_layer_size", 64)
    return MLPClassifier(
        hidden_layer_sizes=(hidden,),
        alpha=params.get("alpha", 0.0001),
        max_iter=params.get("max_iter", 300),
        random_state=42,
    )


MODEL_REGISTRY: dict[str, ModelDefinition] = {
    "logistic_regression": ModelDefinition(
        name="logistic_regression",
        build_fn=_logistic_regression,
        requires_scaling=True,
        supports_feature_importance=False,
        hyperparameters={
            "C": HyperparamSpec("float", 0.001, 100.0, default=1.0),
            "max_iter": HyperparamSpec("int", 100, 5000, default=1000),
            "class_weight": HyperparamSpec("categorical", choices=[None, "balanced"], default=None),
        },
    ),
    "random_forest": ModelDefinition(
        name="random_forest",
        build_fn=_random_forest,
        hyperparameters={
            "n_estimators": HyperparamSpec("int", 50, 2000, default=300),
            "max_depth": HyperparamSpec("int", 1, 100, default=None),
            "min_samples_leaf": HyperparamSpec("int", 1, 50, default=1),
            "class_weight": HyperparamSpec("categorical", choices=[None, "balanced"], default=None),
        },
    ),
    "xgboost": ModelDefinition(
        name="xgboost",
        build_fn=_xgboost,
        hyperparameters={
            "max_depth": HyperparamSpec("int", 1, 20, default=6),
            "learning_rate": HyperparamSpec("float", 0.001, 1.0, default=0.1),
            "n_estimators": HyperparamSpec("int", 50, 2000, default=300),
            "scale_pos_weight": HyperparamSpec("float", 0.1, 1000.0, default=1),
            "subsample": HyperparamSpec("float", 0.1, 1.0, default=1.0),
            "colsample_bytree": HyperparamSpec("float", 0.1, 1.0, default=1.0),
        },
    ),
    "lightgbm": ModelDefinition(
        name="lightgbm",
        build_fn=_lightgbm,
        hyperparameters={
            "max_depth": HyperparamSpec("int", -1, 30, default=-1),
            "learning_rate": HyperparamSpec("float", 0.001, 1.0, default=0.1),
            "n_estimators": HyperparamSpec("int", 50, 2000, default=300),
            "num_leaves": HyperparamSpec("int", 2, 256, default=31),
            "class_weight": HyperparamSpec("categorical", choices=[None, "balanced"], default=None),
        },
    ),
    "hist_gradient_boosting": ModelDefinition(
        name="hist_gradient_boosting",
        build_fn=_hist_gradient_boosting,
        hyperparameters={
            "max_depth": HyperparamSpec("int", 1, 50, default=None),
            "learning_rate": HyperparamSpec("float", 0.001, 1.0, default=0.1),
            "max_iter": HyperparamSpec("int", 50, 2000, default=200),
        },
    ),
    "mlp": ModelDefinition(
        name="mlp",
        build_fn=_mlp,
        requires_scaling=True,
        supports_feature_importance=False,
        hyperparameters={
            "hidden_layer_size": HyperparamSpec("int", 4, 512, default=64),
            "alpha": HyperparamSpec("float", 0.00001, 1.0, default=0.0001),
            "max_iter": HyperparamSpec("int", 50, 2000, default=300),
        },
    ),
}


def get_model_definition(name: str) -> ModelDefinition:
    if name not in MODEL_REGISTRY:
        raise ValueError(f"Unknown model '{name}'. Valid models: {list(MODEL_REGISTRY)}")
    return MODEL_REGISTRY[name]


def build_model(name: str, hyperparameters: dict) -> Any:
    definition = get_model_definition(name)
    return definition.build_fn(hyperparameters)


def list_available_models() -> list[str]:
    return list(MODEL_REGISTRY.keys())
