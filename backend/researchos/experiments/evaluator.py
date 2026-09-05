from dataclasses import dataclass


@dataclass
class Evaluation:
    status: str  # BASELINE | IMPROVED | REGRESSED | NEUTRAL | FAILED
    metric_name: str
    candidate_value: float | None
    best_value: float | None
    absolute_improvement: float | None
    relative_improvement: float | None


NEUTRAL_THRESHOLD = 0.001  # 0.1% relative change treated as neutral


def evaluate_against_best(
    candidate_metrics: dict[str, float] | None,
    best_metrics: dict[str, float] | None,
    primary_metric: str,
) -> Evaluation:
    if not candidate_metrics or primary_metric not in candidate_metrics:
        return Evaluation("FAILED", primary_metric, None, None, None, None)

    candidate_value = candidate_metrics[primary_metric]

    if not best_metrics or primary_metric not in best_metrics:
        # first successful experiment (the baseline) establishes the bar - there is
        # nothing before it to have improved on, so it gets its own status.
        return Evaluation("BASELINE", primary_metric, candidate_value, None, None, None)

    best_value = best_metrics[primary_metric]
    absolute = candidate_value - best_value
    # best_value == 0 makes relative improvement undefined (division by zero) rather than
    # infinite - infinity isn't valid JSON and would break API responses. Status is still
    # derived from the (always well-defined) absolute difference.
    relative = (absolute / best_value) if best_value != 0 else None

    if relative is not None and abs(relative) < NEUTRAL_THRESHOLD:
        status = "NEUTRAL"
    elif absolute > 0:
        status = "IMPROVED"
    elif absolute == 0:
        status = "NEUTRAL"
    else:
        status = "REGRESSED"

    return Evaluation(status, primary_metric, candidate_value, best_value, absolute, relative)
