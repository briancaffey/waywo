"""
Client for the Nemotron Content Safety Reasoning service.

Classifies user prompts and LLM responses for content safety using
nvidia/Nemotron-Content-Safety-Reasoning-4B served via vLLM.
"""

import asyncio
import logging

import httpx

from src.settings import CONTENT_SAFETY_ENABLED, CONTENT_SAFETY_TIMEOUT, CONTENT_SAFETY_URL

logger = logging.getLogger(__name__)

CONTENT_SAFETY_MODEL = "nvidia/Nemotron-Content-Safety-Reasoning-4B"

SAFETY_POLICY = """You are a classifier for analyzing interactions between humans and LLMs. \
The AI assistant is a chatbot that helps users discover and learn about \
software projects shared on Hacker News "What are you working on?" threads.

Determine if the user's request or the assistant's response is harmful.

The following are harmful:
- Violence, threats, harassment, or hate speech
- Sexual or explicit content
- Illegal activity or criminal planning
- Personal information disclosure
- Manipulation or social engineering
- Requests for financial advice, gambling strategies, or betting tips
- Content completely unrelated to software projects, technology, or the assistant's purpose

The following are NOT harmful:
- Questions about software projects, programming, or technology
- Asking for project recommendations or comparisons
- Technical discussions, even about security tools or penetration testing
- Casual greetings or small talk that leads into on-topic conversation
- Questions about how the assistant works or what it can do"""

PROMPT_ONLY_TEMPLATE = """{policy}

Human user:
{user_prompt}

AI assistant:
None

Determine if the user's request is harmful based on the policy above. Output your answer in the following format:

"Prompt harm: <harmful/unharmful>
Response harm: <harmful/unharmful>"

Only output the answer in the format specified above. /no_think"""

EXCHANGE_TEMPLATE = """{policy}

Human user:
{user_prompt}

AI assistant:
{assistant_response}

Determine if the user's request or the assistant's response is harmful based on the policy above. Output your answer in the following format:

"Prompt harm: <harmful/unharmful>
Response harm: <harmful/unharmful>"

Only output the answer in the format specified above. /no_think"""

# Canned response when content is blocked
BLOCKED_MESSAGE = (
    "I'm sorry, but I can't help with that request. "
    "I'm designed to help you discover and learn about software projects "
    "shared on Hacker News. Feel free to ask me about any tech projects or programming topics!"
)


def _parse_classification(text: str) -> dict[str, bool]:
    """Parse the model output into prompt_harmful and response_harmful booleans."""
    text_lower = text.lower()
    prompt_harmful = "prompt harm: harmful" in text_lower and "prompt harm: unharmful" not in text_lower
    response_harmful = "response harm: harmful" in text_lower and "response harm: unharmful" not in text_lower
    return {
        "prompt_harmful": prompt_harmful,
        "response_harmful": response_harmful,
    }


async def classify_prompt(
    user_text: str,
    max_retries: int = 2,
) -> bool:
    """
    Classify whether a user prompt is harmful.

    Returns True if harmful, False if unharmful.
    Falls back to False (unharmful) on errors (fail-open).
    """
    if not CONTENT_SAFETY_ENABLED:
        return False

    prompt = PROMPT_ONLY_TEMPLATE.format(policy=SAFETY_POLICY, user_prompt=user_text)

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=CONTENT_SAFETY_TIMEOUT) as client:
                response = await client.post(
                    f"{CONTENT_SAFETY_URL}/v1/chat/completions",
                    json={
                        "model": CONTENT_SAFETY_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0.0,
                    },
                )
                response.raise_for_status()
                data = response.json()
                output_text = data["choices"][0]["message"]["content"]
                result = _parse_classification(output_text)
                logger.info(f"Content safety (prompt): {result} for input: {user_text[:80]!r}")
                return result["prompt_harmful"]

        except httpx.TimeoutException:
            logger.warning(f"Content safety timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
        except Exception as e:
            logger.warning(f"Content safety error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)

    # Fail open: allow the request if the safety service is unavailable
    logger.warning("Content safety: falling back to unharmful (service unavailable)")
    return False


async def classify_exchange(
    user_text: str,
    assistant_text: str,
    max_retries: int = 2,
) -> bool:
    """
    Classify whether an LLM response is harmful in context of the user prompt.

    Returns True if the response is harmful, False if unharmful.
    Falls back to False (unharmful) on errors (fail-open).
    """
    if not CONTENT_SAFETY_ENABLED:
        return False

    prompt = EXCHANGE_TEMPLATE.format(
        policy=SAFETY_POLICY,
        user_prompt=user_text,
        assistant_response=assistant_text,
    )

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=CONTENT_SAFETY_TIMEOUT) as client:
                response = await client.post(
                    f"{CONTENT_SAFETY_URL}/v1/chat/completions",
                    json={
                        "model": CONTENT_SAFETY_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 100,
                        "temperature": 0.0,
                    },
                )
                response.raise_for_status()
                data = response.json()
                output_text = data["choices"][0]["message"]["content"]
                result = _parse_classification(output_text)
                logger.info(f"Content safety (exchange): {result}")
                return result["response_harmful"]

        except httpx.TimeoutException:
            logger.warning(f"Content safety timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)
        except Exception as e:
            logger.warning(f"Content safety error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2**attempt)

    logger.warning("Content safety: falling back to unharmful (service unavailable)")
    return False


async def check_content_safety_health(timeout: float = 5.0) -> bool:
    """Check if the content safety vLLM service is healthy."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{CONTENT_SAFETY_URL}/v1/models")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Content safety health check failed: {e}")
        return False
