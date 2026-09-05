import json
from abc import ABC, abstractmethod
from typing import Any

from researchos.core.config import settings
from researchos.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Provider abstraction so core ResearchOS logic never couples to one vendor SDK."""

    @abstractmethod
    async def generate_structured(
        self, system_prompt: str, user_prompt: str, schema_hint: str
    ) -> dict[str, Any]:
        """Returns a parsed JSON object matching the caller's expected shape."""
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model

    async def generate_structured(
        self, system_prompt: str, user_prompt: str, schema_hint: str
    ) -> dict[str, Any]:
        full_prompt = (
            f"{user_prompt}\n\n"
            f"Respond with ONLY a single valid JSON object matching this shape "
            f"(no markdown fences, no commentary):\n{schema_hint}"
        )
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": full_prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return _extract_json(text)


class MockLLMProvider(LLMProvider):
    """Deterministic, rule-based stand-in used when no API key is configured.

    Mimics reasonable planner/critic/interpreter behavior so the full autonomous
    research loop can run end-to-end without any external dependency.
    """

    async def generate_structured(
        self, system_prompt: str, user_prompt: str, schema_hint: str
    ) -> dict[str, Any]:
        # Route on which agent invoked us via a marker embedded in the prompt.
        if "ROLE=PLANNER" in system_prompt:
            return self._plan(user_prompt)
        if "ROLE=CRITIC" in system_prompt:
            return {"approved": True, "critique": "Looks reasonable given prior results."}
        if "ROLE=INTERPRETER" in system_prompt:
            return self._interpret(user_prompt)
        if "ROLE=REPORT" in system_prompt:
            return {"summary": "Autonomous research loop completed successfully."}
        return {}

    def _plan(self, user_prompt: str) -> dict[str, Any]:
        # Simple fixed progression through model families, escalating complexity.
        progression = [
            ("logistic_regression", {"class_weight": "balanced"}, "Class weighting may improve minority-class recall on an imbalanced target."),
            ("random_forest", {"n_estimators": 400, "class_weight": "balanced"}, "A non-linear ensemble may capture interactions the linear baseline misses."),
            ("xgboost", {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 400, "scale_pos_weight": 10}, "Gradient boosting with class-weighted loss often improves recall on imbalanced tabular data."),
            ("lightgbm", {"max_depth": 8, "learning_rate": 0.05, "n_estimators": 500, "class_weight": "balanced"}, "A deeper, slower-learning-rate boosted model may refine minority-class discrimination further."),
            ("xgboost", {"max_depth": 8, "learning_rate": 0.03, "n_estimators": 800, "scale_pos_weight": 15}, "Further tuning the best-performing family with a lower learning rate and more estimators may extract additional gains."),
        ]
        try:
            state = json.loads(user_prompt[user_prompt.index("{") : user_prompt.rindex("}") + 1])
        except (ValueError, json.JSONDecodeError):
            state = {}
        idx = int(state.get("experiment_count", 0)) % len(progression)
        model, hyperparams, hypothesis = progression[idx]
        return {
            "hypothesis": hypothesis,
            "reasoning": f"Selected based on progression step {idx + 1}, building on prior experiment results.",
            "model": model,
            "hyperparameters": hyperparams,
            "preprocessing": {"scale_numeric": model in ("logistic_regression", "mlp"), "encode_categorical": True},
            "expected_outcome": "Improved primary metric relative to the current best experiment.",
        }

    def _interpret(self, user_prompt: str) -> dict[str, Any]:
        outcome = "SUPPORTED" if "IMPROVED" in user_prompt else (
            "NOT_SUPPORTED" if "REGRESSED" in user_prompt else "INCONCLUSIVE"
        )
        return {
            "observation": "Metric values changed relative to the parent experiment as recorded in the evaluation.",
            "interpretation": "The change is consistent with the hypothesis's expected mechanism given the model and preprocessing used.",
            "error_analysis": "Confusion matrix and per-class metrics indicate the model's error balance shifted between the two classes; see the raw diagnostics for exact counts.",
            "hypothesis_outcome": outcome,
            "recommended_next_step": "Continue exploring model families and hyperparameters that address the dataset's class imbalance.",
        }


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"LLM response did not contain a JSON object: {text[:200]}")
    return json.loads(text[start : end + 1])


_provider_instance: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    if settings.llm_provider == "anthropic" and settings.anthropic_api_key:
        logger.info("Using AnthropicProvider (model=%s)", settings.anthropic_model)
        _provider_instance = AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model)
    else:
        logger.info("Using MockLLMProvider (no Anthropic API key configured)")
        _provider_instance = MockLLMProvider()
    return _provider_instance
