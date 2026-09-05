from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from researchos.core.database import get_db
from researchos.db.models import Experiment, ResearchProject

router = APIRouter(tags=["experiments"])


def _experiment_detail(experiment: Experiment) -> dict:
    return {
        "id": experiment.id,
        "project_id": experiment.project_id,
        "parent_experiment_id": experiment.parent_experiment_id,
        "sequence_number": experiment.sequence_number,
        "hypothesis": experiment.hypothesis,
        "reasoning": experiment.reasoning,
        "model": experiment.model_name,
        "status": experiment.status,
        "failure_reason": experiment.failure_reason,
        "experiment_spec": experiment.experiment_spec_json,
        "metrics": experiment.metrics_dict(),
        "evaluation": experiment.evaluation_json,
        "diagnostics": experiment.diagnostics_json,
        "training_time_seconds": experiment.training_time_seconds,
        "inference_latency_ms": experiment.inference_latency_ms,
        "artifacts": [
            {"type": a.artifact_type, "storage_path": a.storage_path} for a in experiment.artifacts
        ],
        "interpretation": (
            {
                "observation": experiment.interpretation.observation,
                "interpretation": experiment.interpretation.interpretation,
                "error_analysis": experiment.interpretation.error_analysis,
                "hypothesis_outcome": experiment.interpretation.hypothesis_outcome,
                "recommended_next_step": experiment.interpretation.recommended_next_step,
            }
            if experiment.interpretation
            else None
        ),
        "started_at": experiment.started_at,
        "completed_at": experiment.completed_at,
        "created_at": experiment.created_at,
    }


@router.get("/projects/{project_id}/experiments")
def list_experiments(project_id: str, db: Session = Depends(get_db)):
    project = db.get(ResearchProject, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return [_experiment_detail(e) for e in project.experiments]


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(404, "Experiment not found")
    return _experiment_detail(experiment)
