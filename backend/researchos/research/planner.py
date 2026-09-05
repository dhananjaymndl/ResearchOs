from researchos.experiments.schemas import ExperimentSpec
from researchos.models.registry import list_available_models
from researchos.research.context import ResearchContext
from researchos.research.llm_provider import LLMProvider

SYSTEM_PROMPT = """ROLE=PLANNER
You are the Research Planner inside ResearchOS, an autonomous ML experimentation system.
You propose exactly one machine learning experiment at a time to improve a project's primary metric.

Rules you MUST follow:
- Propose only models from this catalogue: {models}
- Use only hyperparameters valid for the chosen model.
- Do not repeat an experiment identical to one already tried.
- Reference what was learned from previous experiments, including per-class precision/recall
  where relevant (which class the model is failing on).
- Create exactly one clear, testable hypothesis.
- Respect the remaining experiment budget.
- Optimize for the project's primary metric.
- Prefer meaningful, reasoned experiments over blind random search.
- You do not execute code and you do not calculate metrics.

Branching: you may set parent_experiment_id to the id of ANY completed experiment in the
history (not only the current best). Two valid strategies:
1. Try a new model family, branching from the current best.
2. Refine a promising experiment's hyperparameters (a controlled, targeted change,
   justified by that experiment's per-class error pattern) even if it is not the current
   best - e.g. it had strong precision but weak recall, and you want to test whether a
   specific hyperparameter change fixes that without a full model swap.
Explain which strategy you are using in `reasoning`.
"""

SCHEMA_HINT = """{
  "hypothesis": "string - one clear testable hypothesis",
  "reasoning": "string - why this follows from prior results, including which branching strategy (new model family vs. hyperparameter refinement) and which experiment id you are branching from",
  "parent_experiment_id": "string - the id of the experiment you are branching from (from the history's 'id' fields)",
  "model": "string - one of the allowed model names",
  "hyperparameters": { "...": "valid hyperparameters for the chosen model" },
  "preprocessing": {"scale_numeric": true, "encode_categorical": true},
  "expected_outcome": "string"
}"""


async def propose_experiment(
    provider: LLMProvider,
    context: ResearchContext,
    critique: str | None = None,
) -> ExperimentSpec:
    system_prompt = SYSTEM_PROMPT.format(models=list_available_models())
    user_prompt = f"Research context:\n{context.to_planner_prompt_state()}"
    if critique:
        user_prompt += f"\n\nYour previous proposal was rejected by the critic for this reason:\n{critique}\nPropose a revised experiment that addresses this critique."

    raw = await provider.generate_structured(system_prompt, user_prompt, SCHEMA_HINT)

    valid_parent_ids = context.completed_experiment_ids()
    proposed_parent_id = raw.get("parent_experiment_id")
    if proposed_parent_id in valid_parent_ids:
        parent_id = proposed_parent_id
    else:
        # fall back to branching from the current best when the planner omits it or
        # hallucinates an id that doesn't exist in this project's history
        parent_id = context.best_experiment.id if context.best_experiment else None

    spec = ExperimentSpec(
        parent_experiment_id=parent_id,
        hypothesis=raw.get("hypothesis", "Untitled hypothesis"),
        reasoning=raw.get("reasoning", ""),
        model=raw["model"],
        hyperparameters=raw.get("hyperparameters", {}),
        preprocessing=raw.get("preprocessing", {}),
        primary_metric=context.project.primary_metric,
        expected_outcome=raw.get("expected_outcome", ""),
        max_runtime_seconds=600,
    )
    return spec
