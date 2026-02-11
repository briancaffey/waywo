"""
NeMo DataDesigner provider and model configuration.

Reuses the same LLM env vars (LLM_BASE_URL, LLM_MODEL_NAME, LLM_API_KEY)
as the rest of waywo so switching between local and remote inference
requires zero code changes.
"""

import logging

from data_designer.config.models import (
    ChatCompletionInferenceParams,
    ModelConfig,
    ModelProvider,
)

from src.settings import LLM_BASE_URL, LLM_MODEL_NAME

logger = logging.getLogger(__name__)


def build_ndd_provider() -> ModelProvider:
    """Build a ModelProvider pointing at the same LLM endpoint waywo uses.

    The api_key is set to the env var *name* "LLM_API_KEY" so that
    DataDesigner's default EnvironmentResolver will read it at runtime.
    """
    provider = ModelProvider(
        name="waywo-llm",
        endpoint=LLM_BASE_URL,
        provider_type="openai",
        api_key="LLM_API_KEY",
    )
    logger.info(f"NDD provider: {provider.name} -> {provider.endpoint}")
    return provider


def build_ndd_models(creativity: float = 0.85) -> list[ModelConfig]:
    """Build three model configs with different temperatures.

    Args:
        creativity: Temperature for the creative generation model.
            Passed from the frontend slider (0.1 - 1.5).

    Returns:
        List of ModelConfig with aliases:
        - waywo-creative  (temperature=creativity)
        - waywo-structured (temperature=0.1)
        - waywo-judge (temperature=0.2)
    """
    models = [
        ModelConfig(
            alias="waywo-creative",
            model=LLM_MODEL_NAME,
            provider="waywo-llm",
            inference_parameters=ChatCompletionInferenceParams(
                temperature=creativity,
                max_tokens=2048,
            ),
            skip_health_check=True,
        ),
        ModelConfig(
            alias="waywo-structured",
            model=LLM_MODEL_NAME,
            provider="waywo-llm",
            inference_parameters=ChatCompletionInferenceParams(
                temperature=0.1,
                max_tokens=2048,
            ),
            skip_health_check=True,
        ),
        ModelConfig(
            alias="waywo-judge",
            model=LLM_MODEL_NAME,
            provider="waywo-llm",
            inference_parameters=ChatCompletionInferenceParams(
                temperature=0.2,
                max_tokens=1024,
            ),
            skip_health_check=True,
        ),
    ]
    logger.info(
        f"NDD models: {[m.alias for m in models]}, "
        f"model={LLM_MODEL_NAME}, creative temp={creativity}"
    )
    return models
