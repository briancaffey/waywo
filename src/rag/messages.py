"""Shared message builder for multi-turn chat with optional RAG context."""

from llama_index.core.llms import ChatMessage


def build_chat_messages(
    system_prompt: str,
    history: list,
    user_text: str,
    rag_context: str | None = None,
) -> list[ChatMessage]:
    """Build LLM message list: system + optional RAG context + history + user.

    Args:
        system_prompt: The system prompt string.
        history: List of turn objects with .role and .text attributes.
        user_text: The current user message.
        rag_context: Optional RAG context to inject as an additional system message.
    """
    messages = [ChatMessage(role="system", content=system_prompt)]

    if rag_context:
        messages.append(ChatMessage(role="system", content=rag_context))

    for turn in history:
        messages.append(ChatMessage(role=turn.role, content=turn.text))

    messages.append(ChatMessage(role="user", content=user_text))
    return messages
