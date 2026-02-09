"""
LLM configuration for waywo project processing.

Uses NVIDIA Nemotron model via OpenAI-compatible API.
"""

import logging

from llama_index.llms.openai_like import OpenAILike

from src.settings import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_MODEL_NAME,
    LLM_TEMPERATURE,
)

logger = logging.getLogger(__name__)


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
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
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
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
        },
    )

    return llm


def get_llm_for_creative_output() -> OpenAILike:
    """
    Get a configured LLM instance optimized for creative content generation.

    Uses higher temperature (0.8) to produce varied, creative outputs
    while still maintaining coherence. Used for video script generation.

    Returns:
        OpenAILike: Configured LLM client for creative output.
    """
    logger.info(f"🤖 Initializing LLM (creative): {LLM_MODEL_NAME}")

    llm = OpenAILike(
        api_base=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        model=LLM_MODEL_NAME,
        temperature=0.8,  # Higher temperature for creative variety
        max_tokens=LLM_MAX_TOKENS,
        is_chat_model=True,
        is_function_calling_model=False,
        additional_kwargs={
            "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}
        },
    )

    return llm
