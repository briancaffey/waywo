"""Client for communicating with the NAT (NeMo Agent Toolkit) service."""

import os

import httpx

NAT_SERVICE_URL = os.environ.get("NAT_SERVICE_URL", "http://nat:8080")


async def generate(input_message: str, timeout: float = 60.0) -> dict:
    """
    Send a generate request to the NAT service.

    Args:
        input_message: The message/query to send to the LLM
        timeout: Request timeout in seconds

    Returns:
        The response from the NAT service
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{NAT_SERVICE_URL}/generate",
            json={"query": input_message},
        )
        response.raise_for_status()
        return response.json()


async def chat(messages: list[dict], timeout: float = 60.0) -> dict:
    """
    Send a chat request to the NAT service using OpenAI-compatible format.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        timeout: Request timeout in seconds

    Returns:
        The response from the NAT service
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{NAT_SERVICE_URL}/chat",
            json={"messages": messages},
        )
        response.raise_for_status()
        return response.json()


async def health_check() -> bool:
    """
    Check if the NAT service is healthy.

    Returns:
        True if healthy, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{NAT_SERVICE_URL}/health")
            return response.status_code == 200
    except Exception:
        return False
