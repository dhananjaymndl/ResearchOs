from datetime import datetime, timezone

from sqlalchemy.orm import Session

from researchos.db.models import (
    Experiment,
    ExperimentArtifact,
    ExperimentInterpretation,
    ExperimentMetric,
    ResearchEvent,
)
from researchos.experiments.schemas import ExperimentResult, ExperimentSpec
from researchos.research.interpreter import Interpretation


def log_event(
    db: Session,
    project_id: str,
    message: str,
    event_type: str = "info",
    experiment_id: str | None = None,
    metadata: dict | None = None,
) -> ResearchEvent:
    event = ResearchEvent(
        project_id=project_id,
        experiment_id=experiment_id,
        event_type=event_type,
        message=message,
        metadata_json=metadata or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def create_experiment_record(
    db: Session,
    project_id: str,
    sequence_number: int,
    spec: ExperimentSpec,
) -> Experiment:
    experiment = Experiment(
        project_id=project_id,
        parent_experiment_id=spec.parent_experiment_id,
        sequence_number=sequence_number,
        hypothesis=spec.hypothesis,
        reasoning=spec.reasoning,
        model_name=spec.model,
        experiment_spec_json={},
        status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    spec.experiment_id = experiment.id
    experiment.experiment_spec_json = spec.model_dump()
    db.commit()
    db.refresh(experiment)
    return experiment


def save_experiment_result(
    db: Session,
    experiment: Experiment,
    result: ExperimentResult,
    artifact_paths: dict[str, str],
) -> Experiment:
    experiment.status = "COMPLETED" if result.status == "completed" else "FAILED"
    experiment.failure_reason = result.failure_reason
    experiment.training_time_seconds = result.training_time_seconds
    experiment.inference_latency_ms = result.inference_latency_ms
    experiment.completed_at = datetime.now(timezone.utc)
    experiment.diagnostics_json = {
        "confusion_matrix": result.confusion_matrix,
        "class_report": result.class_report,
        "feature_importance": result.feature_importance,
    }

    for name, value in result.metrics.items():
        db.add(ExperimentMetric(experiment_id=experiment.id, metric_name=name, metric_value=value))

    for artifact_type, path in artifact_paths.items():
        db.add(
            ExperimentArtifact(
                experiment_id=experiment.id,
                artifact_type=artifact_type,
                storage_path=path,
            )
        )

    db.commit()
    db.refresh(experiment)
    return experiment


def save_evaluation(db: Session, experiment: Experiment, evaluation_json: dict) -> Experiment:
    experiment.evaluation_json = evaluation_json
    db.commit()
    db.refresh(experiment)
    return experiment


def save_interpretation(db: Session, experiment_id: str, interpretation: Interpretation) -> None:
    record = ExperimentInterpretation(
        experiment_id=experiment_id,
        observation=interpretation.observation,
        interpretation=interpretation.interpretation,
        error_analysis=interpretation.error_analysis,
        hypothesis_outcome=interpretation.hypothesis_outcome,
        recommended_next_step=interpretation.recommended_next_step,
    )
    db.add(record)
    db.commit()
