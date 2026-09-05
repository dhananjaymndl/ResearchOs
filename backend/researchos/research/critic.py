from dataclasses import dataclass

from researchos.experiments.schemas import ExperimentSpec
from researchos.research.context import ResearchContext
from researchos.research.llm_provider import LLMProvider

SYSTEM_PROMPT = """ROLE=CRITIC
You are the Research Critic inside ResearchOS. You review a proposed ML experiment
before it is executed. Check whether the hypothesis makes sense, follows logically
from previous results, is meaningfully different from prior experiments, and is free
of obvious methodological errors. You do not calculate metrics or execute code.
"""

SCHEMA_HINT = """{
  "approved": true,
  "critique": "string - reason for rejection, empty if approved"
}"""


@dataclass
class CriticReview:
    approved: bool
    critique: str


def deterministic_validate(spec: ExperimentSpec, context: ResearchContext) -> CriticReview:
    """Schema/model/duplicate checks the LLM must not be relied on for."""
    for exp in context.experiments:
        prior_spec = exp.experiment_spec_json or {}
        if (
            prior_spec.get("model") == spec.model
            and prior_spec.get("hyperparameters") == spec.hyperparameters
        ):
            return CriticReview(False, f"Identical experiment already run (model={spec.model}, same hyperparameters).")

    if spec.max_runtime_seconds <= 0 or spec.max_runtime_seconds > 3600:
        return CriticReview(False, "max_runtime_seconds must be between 1 and 3600.")

    return CriticReview(True, "")


async def review_experiment(
    provider: LLMProvider, context: ResearchContext, spec: ExperimentSpec
) -> CriticReview:
    deterministic = deterministic_validate(spec, context)
    if not deterministic.approved:
        return deterministic

    user_prompt = (
        f"Research context:\n{context.to_planner_prompt_state()}\n\n"
        f"Proposed experiment:\n"
        f"model={spec.model}\nhypothesis={spec.hypothesis}\nreasoning={spec.reasoning}\n"
        f"hyperparameters={spec.hyperparameters}"
    )
    raw = await provider.generate_structured(SYSTEM_PROMPT, user_prompt, SCHEMA_HINT)
    return CriticReview(approved=bool(raw.get("approved", True)), critique=raw.get("critique", ""))
