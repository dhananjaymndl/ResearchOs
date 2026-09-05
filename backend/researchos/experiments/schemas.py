from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from researchos.models.registry import get_model_definition, list_available_models

PrimaryMetric = Literal["f1", "roc_auc", "precision", "recall", "accuracy"]


class PreprocessingConfig(BaseModel):
    scale_numeric: bool = False
    encode_categorical: bool = True


class ExperimentSpec(BaseModel):
    experiment_id: str | None = None
    parent_experiment_id: str | None = None

    hypothesis: str
    reasoning: str

    model: str
    preprocessing: PreprocessingConfig = Field(default_factory=PreprocessingConfig)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)

    primary_metric: PrimaryMetric = "f1"
    expected_outcome: str = ""
    max_runtime_seconds: int = 600

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if v not in list_available_models():
            raise ValueError(f"Unsupported model '{v}'. Allowed: {list_available_models()}")
        return v

    @model_validator(mode="after")
    def validate_hyperparameters(self) -> "ExperimentSpec":
        definition = get_model_definition(self.model)
        validated: dict[str, Any] = {}
        for key, value in self.hyperparameters.items():
            spec = definition.hyperparameters.get(key)
            if spec is None:
                # unknown hyperparameter for this model - drop rather than reject the
                # whole spec, since the planner may hallucinate a benign extra key
                continue
            if spec.type in ("int", "float") and value is not None:
                if spec.min is not None and value < spec.min:
                    raise ValueError(f"Hyperparameter '{key}'={value} below minimum {spec.min}")
                if spec.max is not None and value > spec.max:
                    raise ValueError(f"Hyperparameter '{key}'={value} above maximum {spec.max}")
            if spec.type == "categorical" and spec.choices is not None and value not in spec.choices:
                raise ValueError(f"Hyperparameter '{key}'={value} not in allowed choices {spec.choices}")
            validated[key] = value
        self.hyperparameters = validated
        return self


class ExperimentResult(BaseModel):
    experiment_id: str
    status: Literal["completed", "failed"]
    metrics: dict[str, float] = Field(default_factory=dict)
    training_time_seconds: float | None = None
    inference_latency_ms: float | None = None
    confusion_matrix: list[list[int]] | None = None
    class_report: dict[str, dict[str, float]] | None = None
    feature_importance: dict[str, float] | None = None
    failure_reason: str | None = None
