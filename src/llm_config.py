"""
LLM configuration for waywo project processing.

Uses NVIDIA Nemotron model via OpenAI-compatible API.
"""

import os
import logging

from llama_index.llms.openai_like import OpenAILike

logger = logging.getLogger(__name__)

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://192.168.6.19:8002/v1")
LLM_MODEL_NAME = os.getenv(
    "LLM_MODEL_NAME", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4"
)
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")

# LLM parameters
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))


def get_llm() -> OpenAILike:
    """
    Get a configured LLM instance for use in workflows.

    Returns:
        OpenAILike: Configured LLM client pointing to Nemotron endpoint.
    """
    logger.info(f"🤖 Initializing LLM: {LLM_MODEL_NAME} at {LLM_BASE_URL}")

    llm = OpenAILike(
        api_base=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL_NAME,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        is_chat_model=True,
        is_function_calling_model=False,  # Nemotron doesn't support function calling
        additional_kwargs={
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": False}
            }
        },
    )

    return llm


def get_llm_for_structured_output() -> OpenAILike:
    """
    Get a configured LLM instance optimized for structured JSON output.

    Uses lower temperature for more deterministic outputs.

    Returns:
        OpenAILike: Configured LLM client for structured output.
    """
    logger.info(f"🤖 Initializing LLM (structured): {LLM_MODEL_NAME}")

    llm = OpenAILike(
        api_base=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL_NAME,
        temperature=0.1,  # Lower temperature for structured output
        max_tokens=LLM_MAX_TOKENS,
        is_chat_model=True,
        is_function_calling_model=False,
        additional_kwargs={
            "extra_body": {
                "chat_template_kwargs": {"enable_thinking": False}
            }
        },
    )

    return llm
