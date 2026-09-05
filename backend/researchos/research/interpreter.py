from dataclasses import dataclass

from researchos.experiments.evaluator import Evaluation
from researchos.experiments.schemas import ExperimentResult, ExperimentSpec
from researchos.research.llm_provider import LLMProvider

SYSTEM_PROMPT = """ROLE=INTERPRETER
You are the Research Interpreter inside ResearchOS. Given a hypothesis, the metric
values before and after an experiment, the confusion matrix, per-class precision/recall,
and top feature importances, explain in plain language what happened, WHY it likely
happened at an error-pattern level (which class is being missed and by how much), and
what should be investigated next. You do not recompute or invent any metric values -
use only the numbers you are given.
"""

SCHEMA_HINT = """{
  "observation": "string - what objectively changed in the summary metrics",
  "interpretation": "string - why it might have happened, grounded in the confusion matrix and per-class metrics",
  "error_analysis": "string - specific error pattern: which class is under-predicted/over-predicted, false positive vs false negative balance, and whether top features suggest a cause",
  "hypothesis_outcome": "SUPPORTED | NOT_SUPPORTED | INCONCLUSIVE",
  "recommended_next_step": "string - a specific, actionable next experiment (a hyperparameter change or a different model family), justified by the error pattern above"
}"""


@dataclass
class Interpretation:
    observation: str
    interpretation: str
    error_analysis: str
    hypothesis_outcome: str
    recommended_next_step: str


def _format_class_report(class_report: dict[str, dict[str, float]] | None) -> str:
    if not class_report:
        return "n/a"
    parts = []
    for cls, stats in class_report.items():
        parts.append(
            f"class {cls}: precision={stats['precision']:.3f} recall={stats['recall']:.3f} "
            f"f1={stats['f1']:.3f} support={stats['support']}"
        )
    return "; ".join(parts)


def _format_confusion_matrix(cm: list[list[int]] | None) -> str:
    if not cm:
        return "n/a"
    tn, fp = cm[0]
    fn, tp = cm[1]
    return f"TN={tn} FP={fp} FN={fn} TP={tp} (rows=actual [0,1], cols=predicted [0,1])"


def _format_feature_importance(fi: dict[str, float] | None) -> str:
    if not fi:
        return "n/a"
    top = list(fi.items())[:8]
    return ", ".join(f"{name}={score:.4f}" for name, score in top)


async def interpret_result(
    provider: LLMProvider,
    spec: ExperimentSpec,
    result: ExperimentResult,
    evaluation: Evaluation,
) -> Interpretation:
    if result.status == "failed":
        return Interpretation(
            observation=f"Experiment failed: {result.failure_reason}",
            interpretation="The experiment could not be evaluated because execution failed.",
            error_analysis="n/a - experiment did not produce predictions.",
            hypothesis_outcome="INCONCLUSIVE",
            recommended_next_step="Avoid the same configuration and try a more conservative experiment.",
        )

    if evaluation.status == "BASELINE":
        metric_val = result.metrics.get(evaluation.metric_name)
        return Interpretation(
            observation=f"Baseline {evaluation.metric_name}={metric_val:.4f} established the reference performance for this project.",
            interpretation="This is the deterministic first experiment; there is no prior result to compare it against.",
            error_analysis=(
                f"Confusion matrix: {_format_confusion_matrix(result.confusion_matrix)}. "
                f"Per-class breakdown: {_format_class_report(result.class_report)}."
            ),
            hypothesis_outcome="INCONCLUSIVE",
            recommended_next_step="Propose an experiment that addresses the weakest class's recall/precision observed in the baseline's confusion matrix.",
        )

    user_prompt = (
        f"Hypothesis: {spec.hypothesis}\n"
        f"Reasoning: {spec.reasoning}\n"
        f"Model: {spec.model}\n"
        f"Hyperparameters: {spec.hyperparameters}\n"
        f"Summary metrics: {result.metrics}\n"
        f"Confusion matrix: {_format_confusion_matrix(result.confusion_matrix)}\n"
        f"Per-class report: {_format_class_report(result.class_report)}\n"
        f"Top feature importances: {_format_feature_importance(result.feature_importance)}\n"
        f"Evaluation status: {evaluation.status}\n"
        f"Primary metric: {evaluation.metric_name}\n"
        f"Candidate value: {evaluation.candidate_value}\n"
        f"Previous best value: {evaluation.best_value}\n"
        f"Absolute improvement: {evaluation.absolute_improvement}\n"
        f"Relative improvement: {evaluation.relative_improvement}\n"
    )
    raw = await provider.generate_structured(SYSTEM_PROMPT, user_prompt, SCHEMA_HINT)
    return Interpretation(
        observation=raw.get("observation", ""),
        interpretation=raw.get("interpretation", ""),
        error_analysis=raw.get("error_analysis", ""),
        hypothesis_outcome=raw.get("hypothesis_outcome", "INCONCLUSIVE"),
        recommended_next_step=raw.get("recommended_next_step", ""),
    )
