from pathlib import Path

from sqlalchemy.orm import Session

from researchos.core.config import settings
from researchos.core.database import SessionLocal
from researchos.core.logging import get_logger
from researchos.datasets.loader import load_dataset
from researchos.datasets.profiler import profile_dataset
from researchos.datasets.splitter import split_dataset
from researchos.db.models import Dataset, Experiment, ResearchProject
from researchos.experiments.evaluator import evaluate_against_best
from researchos.experiments.runner import run_experiment
from researchos.experiments.schemas import ExperimentSpec
from researchos.experiments.service import (
    create_experiment_record,
    log_event,
    save_evaluation,
    save_experiment_result,
    save_interpretation,
)
from researchos.research.context import ResearchContext
from researchos.research.critic import review_experiment
from researchos.research.interpreter import interpret_result
from researchos.research.llm_provider import get_llm_provider
from researchos.research.planner import propose_experiment

logger = get_logger(__name__)


def _feature_columns(profile: dict) -> tuple[list[str], list[str]]:
    return profile["numeric_columns"], profile["categorical_columns"]


def _build_context(db: Session, project: ResearchProject) -> ResearchContext:
    db.refresh(project)
    experiments = list(project.experiments)
    # sequence_number 0 is the deterministic baseline and is free - only planner-proposed
    # experiments (sequence_number >= 1) consume the budget, whether they succeeded or failed.
    non_baseline_used = len([e for e in experiments if e.sequence_number > 0])
    best = None
    if project.best_experiment_id:
        best = next((e for e in experiments if e.id == project.best_experiment_id), None)
    remaining = max(project.experiment_budget - non_baseline_used, 0)
    return ResearchContext(project=project, experiments=experiments, best_experiment=best, remaining_budget=remaining)


def _deterministic_fallback_spec(context: ResearchContext) -> ExperimentSpec:
    tried_models = {e.model_name for e in context.experiments}
    for candidate in ("random_forest", "xgboost", "lightgbm", "logistic_regression"):
        if candidate not in tried_models:
            model = candidate
            break
    else:
        model = "random_forest"

    parent_id = context.best_experiment.id if context.best_experiment else None
    return ExperimentSpec(
        parent_experiment_id=parent_id,
        hypothesis=f"A deterministic fallback experiment using {model} with default hyperparameters.",
        reasoning="No planner proposal was approved by the critic within the revision limit; falling back to a safe default.",
        model=model,
        hyperparameters={},
        preprocessing={"scale_numeric": model == "logistic_regression", "encode_categorical": True},
        primary_metric=context.project.primary_metric,
        expected_outcome="Provides a valid data point to continue the research loop.",
    )


def _maybe_update_best(db: Session, project: ResearchProject, experiment: Experiment) -> None:
    if experiment.status != "COMPLETED":
        return
    metrics = experiment.metrics_dict()
    primary_value = metrics.get(project.primary_metric)
    if primary_value is None:
        return

    current_best = None
    if project.best_experiment_id:
        current_best = next((e for e in project.experiments if e.id == project.best_experiment_id), None)

    if current_best is None or primary_value > current_best.metrics_dict().get(project.primary_metric, float("-inf")):
        project.best_experiment_id = experiment.id
        db.commit()


async def run_research(project_id: str) -> None:
    """Entry point invoked as a background task. Owns its own DB session."""
    db = SessionLocal()
    try:
        project = db.get(ResearchProject, project_id)
        if project is None:
            logger.error("Project %s not found", project_id)
            return

        provider = get_llm_provider()

        project.status = "PROFILING"
        db.commit()

        dataset: Dataset = project.dataset
        df = load_dataset(dataset.storage_path)
        profile = profile_dataset(df, project.target_column)
        dataset.profile_json = profile
        dataset.row_count = profile["rows"]
        dataset.column_count = profile["columns"]
        db.commit()

        log_event(db, project.id, "Dataset profiling completed.", "profiling")
        for warning in profile.get("warnings", []):
            log_event(db, project.id, warning, "warning")

        numeric_cols, categorical_cols = _feature_columns(profile)
        train_df, val_df = split_dataset(
            df, project.target_column, settings.train_split_ratio, project.split_seed
        )

        project.status = "BASELINE_RUNNING"
        db.commit()
        log_event(db, project.id, "Baseline Logistic Regression started.", "baseline")

        baseline_spec = ExperimentSpec(
            hypothesis="A deterministic linear baseline establishes the reference performance for this dataset.",
            reasoning="Every ResearchOS project must begin with a non-LLM-selected deterministic baseline.",
            model="logistic_regression",
            preprocessing={"scale_numeric": True, "encode_categorical": True},
            hyperparameters={},
            primary_metric=project.primary_metric,
            expected_outcome="Establishes the baseline the research loop will try to beat.",
        )
        await _execute_experiment(db, project, baseline_spec, sequence_number=0, numeric_cols=numeric_cols,
                                   categorical_cols=categorical_cols, train_df=train_df, val_df=val_df)

        project.status = "RESEARCHING"
        db.commit()

        completed_count = len([e for e in project.experiments if e.status in ("COMPLETED", "FAILED")])
        sequence = completed_count

        while completed_count - 1 < project.experiment_budget:  # -1 excludes the baseline from the budget count
            context = _build_context(db, project)

            critique = None
            spec = None
            approved = False
            for attempt in range(settings.max_critic_revisions + 1):
                spec = await propose_experiment(provider, context, critique)
                log_event(
                    db, project.id,
                    f"ResearchOS proposed: {spec.hypothesis}",
                    "hypothesis",
                    metadata={"model": spec.model, "attempt": attempt + 1},
                )
                review = await review_experiment(provider, context, spec)
                if review.approved:
                    approved = True
                    break
                critique = review.critique
                log_event(db, project.id, f"Critic requested revision: {critique}", "critic")

            if not approved:
                spec = _deterministic_fallback_spec(context)
                log_event(
                    db, project.id,
                    "Critic did not approve a proposal after maximum revisions; using deterministic fallback experiment.",
                    "critic",
                )

            await _execute_experiment(db, project, spec, sequence_number=sequence, numeric_cols=numeric_cols,
                                       categorical_cols=categorical_cols, train_df=train_df, val_df=val_df)
            sequence += 1
            completed_count = len([e for e in project.experiments if e.status in ("COMPLETED", "FAILED")])

        project.status = "COMPLETED"
        db.commit()
        log_event(db, project.id, "Research loop completed. Best experiment selected.", "completed")

    except Exception:
        logger.exception("Research loop crashed for project %s", project_id)
        project = db.get(ResearchProject, project_id)
        if project is not None:
            project.status = "FAILED"
            db.commit()
            log_event(db, project.id, "Research loop failed due to an internal error.", "error")
    finally:
        db.close()


async def _execute_experiment(
    db: Session,
    project: ResearchProject,
    spec: ExperimentSpec,
    sequence_number: int,
    numeric_cols: list[str],
    categorical_cols: list[str],
    train_df,
    val_df,
) -> Experiment:
    experiment = create_experiment_record(db, project.id, sequence_number, spec)
    artifact_dir = Path(settings.artifact_storage_dir) / experiment.id

    result, artifact_paths = run_experiment(
        spec, train_df, val_df, project.target_column, numeric_cols, categorical_cols, artifact_dir
    )
    experiment = save_experiment_result(db, experiment, result, artifact_paths)

    if result.status == "failed":
        log_event(db, project.id, f"Experiment failed: {result.failure_reason}", "failure", experiment.id)
        return experiment

    context = _build_context(db, project)
    best_metrics = context.best_experiment.metrics_dict() if context.best_experiment else None
    evaluation = evaluate_against_best(result.metrics, best_metrics, project.primary_metric)
    save_evaluation(db, experiment, {
        "status": evaluation.status,
        "metric_name": evaluation.metric_name,
        "candidate_value": evaluation.candidate_value,
        "best_value": evaluation.best_value,
        "absolute_improvement": evaluation.absolute_improvement,
        "relative_improvement": evaluation.relative_improvement,
    })

    provider = get_llm_provider()
    interpretation = await interpret_result(provider, spec, result, evaluation)
    save_interpretation(db, experiment.id, interpretation)

    _maybe_update_best(db, project, experiment)

    metric_val = result.metrics.get(project.primary_metric)
    if evaluation.status == "BASELINE":
        message = f"Experiment {sequence_number} completed. Baseline {project.primary_metric}={metric_val:.4f}."
    else:
        message = f"Experiment {sequence_number} completed. {project.primary_metric}={metric_val:.4f} ({evaluation.status})."
    log_event(db, project.id, message, "experiment_completed", experiment.id)
    return experiment
