"""Text chat REST API with threaded conversations and agentic RAG.

Endpoints:
  GET    /api/chat/threads                     - list threads
  POST   /api/chat/threads                     - create thread
  GET    /api/chat/threads/{id}                - get thread with turns
  PUT    /api/chat/threads/{id}                - update thread title
  DELETE /api/chat/threads/{id}                - delete thread
  POST   /api/chat/threads/{id}/message        - send message (legacy)
  POST   /api/chat/threads/{id}/message/stream - send message (SSE streaming)
"""

import asyncio
import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from llama_index.core.llms import ChatMessage
from pydantic import BaseModel

from src.agent.engine import run_agent
from src.agent.events import AgentEventType
from src.agent.prompts import TEXT_AGENT_SYSTEM_PROMPT
from src.clients.content_safety import BLOCKED_MESSAGE, classify_exchange, classify_prompt
from src.db.chat import (
    create_thread,
    create_turn,
    delete_thread,
    get_thread,
    get_thread_count,
    get_turns,
    list_threads,
    search_threads,
    update_thread,
)
from src.llm_config import get_llm
from src.rag.messages import build_chat_messages
from src.rag.retrieve import smart_retrieve
from src.workflows.prompts import CHAT_RAG_CONTEXT_TEMPLATE, CHAT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_HISTORY_TURNS = 20


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateThreadRequest(BaseModel):
    title: Optional[str] = None


class UpdateThreadRequest(BaseModel):
    title: str


class SendMessageRequest(BaseModel):
    message: str
    top_k: int = 5


# ---------------------------------------------------------------------------
# Thread CRUD
# ---------------------------------------------------------------------------


@router.get("/api/chat/threads")
async def api_list_threads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
):
    if q:
        threads = search_threads(q, limit=limit)
    else:
        threads = list_threads(limit=limit, offset=offset)
    total = get_thread_count()
    return {
        "threads": [t.model_dump() for t in threads],
        "total": total,
    }


@router.post("/api/chat/threads", status_code=201)
async def api_create_thread(body: CreateThreadRequest = CreateThreadRequest()):
    thread = create_thread(title=body.title or "New conversation")
    return thread.model_dump()


@router.get("/api/chat/threads/{thread_id}")
async def api_get_thread(thread_id: str):
    thread = get_thread(thread_id, include_turns=True)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread.model_dump()


@router.put("/api/chat/threads/{thread_id}")
async def api_update_thread(thread_id: str, body: UpdateThreadRequest):
    thread = update_thread(thread_id, title=body.title)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread.model_dump()


@router.delete("/api/chat/threads/{thread_id}")
async def api_delete_thread(thread_id: str):
    if not delete_thread(thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Chat message endpoint
# ---------------------------------------------------------------------------


@router.post("/api/chat/threads/{thread_id}/message")
async def api_send_message(thread_id: str, body: SendMessageRequest):
    """Send a message and get an LLM response with optional RAG context."""
    thread = get_thread(thread_id, include_turns=False)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_text = body.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # 0. Content safety: classify user prompt
    if await classify_prompt(user_text):
        logger.info(f"Chat: blocked harmful prompt in thread {thread_id}")
        create_turn(thread_id=thread_id, role="user", text=user_text)
        create_turn(thread_id=thread_id, role="assistant", text=BLOCKED_MESSAGE)
        return {
            "response": BLOCKED_MESSAGE,
            "source_projects": [],
            "thread_id": thread_id,
            "rag_triggered": False,
            "llm_duration_ms": 0,
            "blocked": True,
        }

    # 1. Load recent history
    history = get_turns(thread_id, limit=MAX_HISTORY_TURNS)

    # 2. Smart RAG retrieval
    rag = await smart_retrieve(user_text, top_k=body.top_k)

    # 3. Build messages
    rag_context_str = None
    if rag.was_triggered:
        rag_context_str = CHAT_RAG_CONTEXT_TEMPLATE.format(context=rag.context_text)

    messages = build_chat_messages(
        system_prompt=CHAT_SYSTEM_PROMPT,
        history=history,
        user_text=user_text,
        rag_context=rag_context_str,
    )

    # 4. LLM call
    llm_start = time.monotonic()
    llm = get_llm()
    response = await llm.achat(messages)
    llm_text = response.message.content.strip()
    llm_ms = int((time.monotonic() - llm_start) * 1000)

    # 4b. Content safety: classify LLM response
    if await classify_exchange(user_text, llm_text):
        logger.info(f"Chat: blocked harmful response in thread {thread_id}")
        llm_text = BLOCKED_MESSAGE

    # 5. Persist turns
    create_turn(
        thread_id=thread_id,
        role="user",
        text=user_text,
    )
    create_turn(
        thread_id=thread_id,
        role="assistant",
        text=llm_text,
        source_projects=rag.source_projects if rag.was_triggered else None,
        llm_duration_ms=llm_ms,
        rag_triggered=rag.was_triggered,
    )

    # 6. Auto-title on first message (fire-and-forget)
    if not history:
        asyncio.create_task(_auto_title_thread(thread_id, user_text))

    return {
        "response": llm_text,
        "source_projects": rag.source_projects,
        "thread_id": thread_id,
        "rag_triggered": rag.was_triggered,
        "llm_duration_ms": llm_ms,
    }


# ---------------------------------------------------------------------------
# SSE streaming chat endpoint (agentic)
# ---------------------------------------------------------------------------


def _sse_event(event: str, data: dict) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/api/chat/threads/{thread_id}/message/stream")
async def api_send_message_stream(thread_id: str, body: SendMessageRequest):
    """Send a message and stream the agentic response as SSE events."""
    thread = get_thread(thread_id, include_turns=False)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    user_text = body.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    async def event_generator():
        llm_start = time.monotonic()

        # Load recent history
        history = get_turns(thread_id, limit=MAX_HISTORY_TURNS)

        # Persist user turn immediately
        create_turn(thread_id=thread_id, role="user", text=user_text)

        # Content safety: classify user prompt
        if await classify_prompt(user_text):
            logger.info(f"Chat stream: blocked harmful prompt in thread {thread_id}")
            create_turn(thread_id=thread_id, role="assistant", text=BLOCKED_MESSAGE)
            yield _sse_event("answer_start", {})
            yield _sse_event("answer_token", {"token": BLOCKED_MESSAGE})
            yield _sse_event("answer_done", {"full_text": BLOCKED_MESSAGE, "source_projects": [], "blocked": True})
            yield _sse_event("done", {"llm_duration_ms": 0, "thread_id": thread_id})
            return

        # Run the agent
        final_text = ""
        source_projects: list[dict] = []
        agent_steps: list[dict] = []

        async for event in run_agent(
            user_message=user_text,
            history=history,
            system_prompt_template=TEXT_AGENT_SYSTEM_PROMPT,
            stream_final_answer=True,
        ):
            if event.type == AgentEventType.THINKING:
                yield _sse_event("thinking", {
                    "thought": event.data.get("thought", ""),
                    "iteration": event.data.get("iteration", 0),
                })

            elif event.type == AgentEventType.TOOL_CALL:
                yield _sse_event("tool_call", {
                    "tool": event.data.get("tool", ""),
                    "input": event.data.get("input", ""),
                })

            elif event.type == AgentEventType.TOOL_RESULT:
                yield _sse_event("tool_result", {
                    "tool": event.data.get("tool", ""),
                    "projects_found": event.data.get("projects_found", 0),
                    "result_summary": event.data.get("result_summary", ""),
                })

            elif event.type == AgentEventType.ANSWER_START:
                yield _sse_event("answer_start", {})

            elif event.type == AgentEventType.ANSWER_TOKEN:
                yield _sse_event("answer_token", {
                    "token": event.data.get("token", ""),
                })

            elif event.type == AgentEventType.ANSWER_DONE:
                final_text = event.data.get("full_text", "")
                source_projects = event.data.get("source_projects", [])
                agent_steps = event.data.get("agent_steps", [])
                yield _sse_event("answer_done", {
                    "full_text": final_text,
                    "source_projects": source_projects,
                })

            elif event.type == AgentEventType.ERROR:
                yield _sse_event("error", {
                    "error": event.data.get("error", "Unknown error"),
                })

            elif event.type == AgentEventType.MAX_ITERATIONS:
                yield _sse_event("max_iterations", {
                    "iterations": event.data.get("iterations", 0),
                })

        llm_ms = int((time.monotonic() - llm_start) * 1000)

        # Content safety: classify LLM response
        if final_text and await classify_exchange(user_text, final_text):
            logger.info(f"Chat stream: blocked harmful response in thread {thread_id}")
            final_text = BLOCKED_MESSAGE

        # Persist assistant turn
        if final_text:
            create_turn(
                thread_id=thread_id,
                role="assistant",
                text=final_text,
                source_projects=source_projects if source_projects else None,
                llm_duration_ms=llm_ms,
                rag_triggered=bool(source_projects),
                agent_steps=agent_steps if agent_steps else None,
            )

        # Auto-title on first message
        if not history:
            asyncio.create_task(_auto_title_thread(thread_id, user_text))

        yield _sse_event("done", {
            "llm_duration_ms": llm_ms,
            "thread_id": thread_id,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _auto_title_thread(thread_id: str, user_text: str):
    """Generate a short title for the thread based on the first user message."""
    try:
        llm = get_llm()
        resp = await llm.achat(
            [
                ChatMessage(
                    role="system",
                    content="Generate a very short title (3-6 words) for a conversation that starts with the following message. Return ONLY the title, no quotes or punctuation.",
                ),
                ChatMessage(role="user", content=user_text),
            ]
        )
        title = resp.message.content.strip().strip('"').strip("'")
        if title:
            update_thread(thread_id, title=title)
            logger.info(f"Chat: auto-titled thread {thread_id} → {title!r}")
    except Exception as e:
        logger.warning(f"Chat: auto-title failed: {e}")
