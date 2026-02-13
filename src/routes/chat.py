"""Text chat REST API with threaded conversations and smart RAG.

Endpoints:
  GET    /api/chat/threads              - list threads
  POST   /api/chat/threads              - create thread
  GET    /api/chat/threads/{id}         - get thread with turns
  PUT    /api/chat/threads/{id}         - update thread title
  DELETE /api/chat/threads/{id}         - delete thread
  POST   /api/chat/threads/{id}/message - send message (main chat endpoint)
"""

import asyncio
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from llama_index.core.llms import ChatMessage
from pydantic import BaseModel

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
