from researchos.db.models import ResearchProject


def generate_report(project: ResearchProject) -> dict:
    experiments = sorted(project.experiments, key=lambda e: e.sequence_number)
    completed = [e for e in experiments if e.status == "COMPLETED"]
    failed = [e for e in experiments if e.status == "FAILED"]

    progression = [
        {
            "sequence_number": e.sequence_number,
            "model": e.model_name,
            "primary_metric_value": e.metrics_dict().get(project.primary_metric),
        }
        for e in completed
    ]

    baseline = experiments[0] if experiments else None
    best = None
    if project.best_experiment_id:
        best = next((e for e in experiments if e.id == project.best_experiment_id), None)

    improvement = None
    if baseline and best and baseline.id != best.id:
        base_val = baseline.metrics_dict().get(project.primary_metric)
        best_val = best.metrics_dict().get(project.primary_metric)
        if base_val is not None and best_val is not None and base_val != 0:
            improvement = {
                "absolute": round(best_val - base_val, 6),
                "relative_percent": round((best_val - base_val) / base_val * 100, 2),
            }

    key_findings = []
    failed_hypotheses = []
    for e in completed:
        outcome = e.interpretation.hypothesis_outcome if e.interpretation else None
        evaluation_status = (e.evaluation_json or {}).get("status")
        if outcome == "NOT_SUPPORTED" or evaluation_status == "REGRESSED":
            failed_hypotheses.append({"sequence_number": e.sequence_number, "hypothesis": e.hypothesis, "model": e.model_name})
        elif outcome == "SUPPORTED":
            key_findings.append({"sequence_number": e.sequence_number, "hypothesis": e.hypothesis, "model": e.model_name})

    return {
        "research_objective": project.objective,
        "primary_metric": project.primary_metric,
        "dataset_overview": (project.dataset.profile_json if project.dataset else {}),
        "dataset_concerns": (project.dataset.profile_json.get("warnings", []) if project.dataset else []),
        "baseline": {
            "model": baseline.model_name if baseline else None,
            "metrics": baseline.metrics_dict() if baseline else {},
        } if baseline else None,
        "experiments_conducted": [
            {
                "sequence_number": e.sequence_number,
                "model": e.model_name,
                "hypothesis": e.hypothesis,
                "status": e.status,
                "metrics": e.metrics_dict(),
                "hypothesis_outcome": e.interpretation.hypothesis_outcome if e.interpretation else None,
            }
            for e in experiments
        ],
        "experiment_progression": progression,
        "best_experiment": {
            "sequence_number": best.sequence_number,
            "model": best.model_name,
            "metrics": best.metrics_dict(),
            "hypothesis": best.hypothesis,
        } if best else None,
        "improvement_over_baseline": improvement,
        "key_findings": key_findings,
        "failed_hypotheses": failed_hypotheses,
        "limitations": [
            "Phase 1 supports tabular binary classification only.",
            "Experiments share a single fixed train/validation split.",
            "No statistical significance testing is performed on metric differences.",
        ],
        "recommended_future_experiments": [
            "Hyperparameter tuning around the best-performing model family.",
            "Feature engineering informed by feature-importance artifacts.",
            "Cross-validation to confirm result stability.",
        ],
        "experiment_count": len(experiments),
        "failed_experiment_count": len(failed),
    }
