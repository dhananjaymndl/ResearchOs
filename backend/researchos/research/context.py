import json
from dataclasses import dataclass

from researchos.db.models import Experiment, ResearchProject


@dataclass
class ResearchContext:
    project: ResearchProject
    experiments: list[Experiment]
    best_experiment: Experiment | None
    remaining_budget: int

    def completed_experiment_ids(self) -> set[str]:
        return {e.id for e in self.experiments if e.status == "COMPLETED"}

    def to_planner_prompt_state(self) -> str:
        history_lines = []
        for exp in self.experiments:
            metrics = exp.metrics_dict()
            metric_str = ", ".join(f"{k}={v:.4f}" for k, v in metrics.items()) if metrics else "n/a"

            class_report = (exp.diagnostics_json or {}).get("class_report")
            error_str = "n/a"
            if class_report:
                error_str = "; ".join(
                    f"class {cls} recall={stats['recall']:.3f} precision={stats['precision']:.3f}"
                    for cls, stats in class_report.items()
                )

            outcome = exp.interpretation.hypothesis_outcome if exp.interpretation else "n/a"

            history_lines.append(
                f"id={exp.id} seq={exp.sequence_number} model=[{exp.model_name}] "
                f"parent_id={exp.parent_experiment_id or 'none'} status={exp.status} "
                f"hypothesis_outcome={outcome} "
                f"hypothesis=\"{exp.hypothesis}\" metrics=({metric_str}) "
                f"per_class=({error_str})"
            )

        best_summary = "none yet"
        if self.best_experiment is not None:
            metrics = self.best_experiment.metrics_dict()
            best_summary = f"id={self.best_experiment.id} {self.best_experiment.model_name}: {json.dumps(metrics)}"

        # sequence_number 0 is always the deterministic baseline and does NOT count
        # against experiment_budget - only sequence_number >= 1 experiments do.
        non_baseline_completed = len([e for e in self.experiments if e.sequence_number > 0])

        state = {
            "objective": self.project.objective,
            "primary_metric": self.project.primary_metric,
            "note": (
                "experiment_budget counts only planner-proposed experiments "
                "(sequence_number >= 1). The baseline (sequence_number 0) is free and "
                "does not consume budget. Every experiment below has a unique 'id' - "
                "you may set parent_experiment_id to ANY completed experiment's id, not "
                "just the current best, to branch research in a controlled way (e.g. "
                "refine a promising-but-not-best experiment's hyperparameters instead of "
                "always building on the single best result)."
            ),
            "experiment_budget": self.project.experiment_budget,
            "planner_experiments_completed_so_far": non_baseline_completed,
            "remaining_budget": self.remaining_budget,
            "current_best_experiment": best_summary,
            "history": history_lines,
        }
        return json.dumps(state, indent=2)
