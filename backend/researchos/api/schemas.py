from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CreateProjectRequest(BaseModel):
    name: str
    objective: str
    primary_metric: Literal["f1", "roc_auc", "precision", "recall", "accuracy"] = "f1"
    experiment_budget: Literal[3, 5, 10] = 5


class ProjectSummary(BaseModel):
    id: str
    name: str
    objective: str
    status: str
    dataset_filename: str | None
    experiment_count: int
    baseline_metric: float | None
    best_metric: float | None
    best_experiment_id: str | None
    primary_metric: str
    experiment_budget: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SetDatasetTargetRequest(BaseModel):
    target_column: str
