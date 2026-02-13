"""Voice chat WebSocket endpoint + thread CRUD REST API.

Handles the full voice round-trip:
  Browser mic → PCM audio → STT (via WebSocket proxy) → LLM → TTS → WAV audio → Browser playback

REST endpoints for thread management:
  GET    /api/voice/threads          - list threads
  POST   /api/voice/threads          - create thread
  GET    /api/voice/threads/{id}     - get thread with turns
  PUT    /api/voice/threads/{id}     - update thread title
  DELETE /api/voice/threads/{id}     - delete thread
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import websockets
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from llama_index.core.llms import ChatMessage
from pydantic import BaseModel

from src.agent.engine import run_agent
from src.agent.events import AgentEventType
from src.agent.prompts import VOICE_AGENT_SYSTEM_PROMPT
from src.clients.tts import generate_speech, list_voices
from src.db.voice import (
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
from src.settings import STT_WS_URL

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/voice/voices")
async def get_voices():
    """List available TTS voices, parsed into a structured format."""
    try:
        raw = await list_voices()
        # raw is {"lang-codes": {"voices": [...]}}
        voices = []
        for _lang_key, data in raw.items():
            if isinstance(data, dict) and "voices" in data:
                for name in data["voices"]:
                    # Pattern: Magpie-Multilingual.EN-US.Mia.Happy
                    parts = name.split(".")
                    lang = parts[1] if len(parts) >= 2 else "unknown"
                    speaker = parts[2] if len(parts) >= 3 else name
                    emotion = parts[3] if len(parts) >= 4 else None
                    voices.append(
                        {
                            "id": name,
                            "language": lang,
                            "speaker": speaker,
                            "emotion": emotion,
                            "label": f"{speaker}" + (f" ({emotion})" if emotion else ""),
                        }
                    )
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        return {"voices": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Thread CRUD REST endpoints
# ---------------------------------------------------------------------------


class CreateThreadRequest(BaseModel):
    title: Optional[str] = None


class UpdateThreadRequest(BaseModel):
    title: str


@router.get("/api/voice/threads")
async def api_list_threads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
):
    """List voice threads, optionally filtered by search query."""
    if q:
        threads = search_threads(q, limit=limit)
    else:
        threads = list_threads(limit=limit, offset=offset)
    total = get_thread_count()
    return {
        "threads": [t.model_dump() for t in threads],
        "total": total,
    }


@router.post("/api/voice/threads", status_code=201)
async def api_create_thread(body: CreateThreadRequest = CreateThreadRequest()):
    """Create a new voice thread."""
    thread = create_thread(title=body.title or "New conversation")
    return thread.model_dump()


@router.get("/api/voice/threads/{thread_id}")
async def api_get_thread(thread_id: str):
    """Get a single voice thread with its turns."""
    thread = get_thread(thread_id, include_turns=True)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread.model_dump()


@router.put("/api/voice/threads/{thread_id}")
async def api_update_thread(thread_id: str, body: UpdateThreadRequest):
    """Update a voice thread's title."""
    thread = update_thread(thread_id, title=body.title)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread.model_dump()


@router.delete("/api/voice/threads/{thread_id}")
async def api_delete_thread(thread_id: str):
    """Delete a voice thread and all its turns."""
    deleted = delete_thread(thread_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------


MAX_HISTORY_TURNS = 20  # Max recent turns to send as LLM context


def _make_event(event_type: str, **kwargs) -> str:
    """Build a JSON text frame to send to the client."""
    return json.dumps({"type": event_type, **kwargs})


def _make_debug(category: str, event: str, **data) -> str:
    """Build a debug event JSON frame."""
    return json.dumps(
        {
            "type": "debug",
            "category": category,
            "event": event,
            "data": data,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
    )


async def _send_debug(ws_client: WebSocket, category: str, event: str, **data):
    """Send a debug event to the client (fire-and-forget)."""
    try:
        await ws_client.send_text(_make_debug(category, event, **data))
    except Exception:
        pass  # Don't let debug events break the flow


async def _proxy_audio_to_stt(
    ws_client: WebSocket,
    stt_ws: websockets.WebSocketClientProtocol,
    state: dict,
):
    """Forward PCM binary frames from client to STT WebSocket."""
    chunk_count = 0
    total_bytes = 0
    try:
        while state["phase"] == "listening":
            raw = await asyncio.wait_for(ws_client.receive(), timeout=30.0)

            if raw["type"] == "websocket.disconnect":
                state["phase"] = "disconnected"
                return

            if "bytes" in raw and raw["bytes"]:
                chunk_count += 1
                total_bytes += len(raw["bytes"])
                await stt_ws.send(raw["bytes"])

                if chunk_count % 10 == 0:
                    await _send_debug(
                        ws_client,
                        "stt",
                        "chunks_forwarded",
                        count=chunk_count,
                        total_bytes=total_bytes,
                    )

            elif "text" in raw and raw["text"]:
                msg = json.loads(raw["text"])
                if msg.get("type") == "stop_listening":
                    state["phase"] = "processing"
                    return
                elif msg.get("type") == "cancel":
                    state["phase"] = "cancelled"
                    return
    except asyncio.TimeoutError:
        logger.warning("Audio proxy timed out waiting for client data")
        state["phase"] = "processing"
    except (WebSocketDisconnect, Exception) as e:
        logger.warning(f"Audio proxy error: {e}")
        state["phase"] = "disconnected"
    finally:
        state["audio_chunks"] = chunk_count
        state["audio_bytes"] = total_bytes


async def _collect_stt_results(
    stt_ws: websockets.WebSocketClientProtocol,
    ws_client: WebSocket,
) -> str | None:
    """Read partial/final transcription from the STT WebSocket and relay to client."""
    final_text = None
    partial_count = 0
    try:
        while True:
            result = await asyncio.wait_for(stt_ws.recv(), timeout=30.0)
            data = json.loads(result)

            if "error" in data:
                logger.error(f"STT error: {data['error']}")
                await _send_debug(
                    ws_client, "stt", "error", error=data["error"]
                )
                await ws_client.send_text(
                    _make_event("error", message=f"STT error: {data['error']}")
                )
                return None

            text = data.get("text", "")
            is_final = data.get("final", False)

            if is_final:
                final_text = text
                await _send_debug(
                    ws_client,
                    "stt",
                    "final",
                    text=text,
                    partial_count=partial_count,
                )
                await ws_client.send_text(_make_event("stt_final", text=text))
                break
            else:
                partial_count += 1
                await _send_debug(
                    ws_client, "stt", "partial", text=text, index=partial_count
                )
                await ws_client.send_text(
                    _make_event("stt_partial", text=text)
                )
    except asyncio.TimeoutError:
        logger.warning("STT result collection timed out")
        await _send_debug(ws_client, "stt", "timeout")
    except Exception as e:
        logger.error(f"STT result error: {e}")
        await _send_debug(ws_client, "stt", "error", error=str(e))

    return final_text


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
            logger.info(f"Voice chat: auto-titled thread {thread_id} → {title!r}")
    except Exception as e:
        logger.warning(f"Voice chat: auto-title failed: {e}")


@router.websocket("/ws/voice-chat")
async def voice_chat(
    ws_client: WebSocket,
    thread_id: Optional[str] = Query(None),
):
    """Main voice-chat WebSocket handler."""
    await ws_client.accept()
    logger.info(f"Voice chat: client connected (thread_id={thread_id!r})")

    selected_voice = None  # TTS voice, set via set_voice message
    turn_count_in_session = 0  # Track turns for auto-title

    # Resolve or create thread
    if thread_id:
        thread = get_thread(thread_id, include_turns=False)
        if thread is None:
            await ws_client.send_text(
                _make_event("error", message="Thread not found")
            )
            await ws_client.close()
            return
    else:
        thread = create_thread()
        thread_id = thread.id
        logger.info(f"Voice chat: created new thread {thread_id}")

    await _send_debug(ws_client, "ws", "connected", thread_id=thread_id)
    await ws_client.send_text(
        _make_event("state", state="idle", thread_id=thread_id)
    )

    try:
        while True:
            # ── Wait for start_listening ──────────────────────────────
            raw = await ws_client.receive()
            if raw["type"] == "websocket.disconnect":
                break

            if "text" not in raw:
                continue

            msg = json.loads(raw["text"])
            if msg.get("type") == "set_voice":
                selected_voice = msg.get("voice") or None
                logger.info(f"Voice chat: voice set to {selected_voice!r}")
                await _send_debug(ws_client, "tts", "voice_changed", voice=selected_voice)
                continue
            if msg.get("type") != "start_listening":
                continue

            # ── LISTENING phase ───────────────────────────────────────
            turn_start = time.monotonic()
            await _send_debug(ws_client, "state", "transition", to="listening")
            await ws_client.send_text(_make_event("state", state="listening"))
            logger.info("Voice chat: listening started")

            state = {"phase": "listening", "audio_chunks": 0, "audio_bytes": 0}
            stt_ws = None

            try:
                # Connect to STT WebSocket
                stt_connect_start = time.monotonic()
                stt_ws = await websockets.connect(STT_WS_URL)
                stt_connect_ms = int(
                    (time.monotonic() - stt_connect_start) * 1000
                )
                logger.info(
                    f"Voice chat: connected to STT at {STT_WS_URL}"
                )
                await _send_debug(
                    ws_client,
                    "stt",
                    "ws_connected",
                    url=STT_WS_URL,
                    connect_ms=stt_connect_ms,
                )

                # Forward audio and collect results concurrently
                proxy_task = asyncio.create_task(
                    _proxy_audio_to_stt(ws_client, stt_ws, state)
                )

                await proxy_task

                if state["phase"] == "disconnected":
                    break
                if state["phase"] == "cancelled":
                    await stt_ws.send("END")
                    await stt_ws.close()
                    await _send_debug(ws_client, "state", "transition", to="idle", reason="cancelled")
                    await ws_client.send_text(_make_event("state", state="idle"))
                    continue

                # ── PROCESSING phase ──────────────────────────────────
                await _send_debug(
                    ws_client,
                    "state",
                    "transition",
                    to="processing",
                    audio_chunks=state["audio_chunks"],
                    audio_bytes=state["audio_bytes"],
                )
                await ws_client.send_text(
                    _make_event("state", state="processing")
                )
                logger.info("Voice chat: processing (sending END to STT)")

                # Tell STT we're done sending audio
                await stt_ws.send("END")
                await _send_debug(ws_client, "stt", "end_sent")

                # Collect final transcription
                stt_start = time.monotonic()
                transcription = await _collect_stt_results(stt_ws, ws_client)
                stt_ms = int((time.monotonic() - stt_start) * 1000)
                await stt_ws.close()
                stt_ws = None
                await _send_debug(
                    ws_client, "stt", "ws_closed", duration_ms=stt_ms
                )

                if not transcription or not transcription.strip():
                    logger.info(
                        "Voice chat: empty transcription, returning to idle"
                    )
                    await _send_debug(
                        ws_client,
                        "stt",
                        "empty_result",
                    )
                    await ws_client.send_text(
                        _make_event("error", message="No speech detected")
                    )
                    await ws_client.send_text(
                        _make_event("state", state="idle")
                    )
                    continue

                logger.info(f"Voice chat: transcription = {transcription!r}")

                # ── Agent-driven RAG + LLM ────────────────────────────
                llm_start = time.monotonic()

                # Load conversation history for context
                history = get_turns(thread_id, limit=MAX_HISTORY_TURNS)
                await _send_debug(
                    ws_client,
                    "agent",
                    "started",
                    input_text=transcription,
                    input_chars=len(transcription),
                    history_turns=len(history),
                )

                llm_text = ""
                source_projects: list[dict] = []
                agent_steps: list[dict] = []

                async for event in run_agent(
                    user_message=transcription,
                    history=history,
                    system_prompt_template=VOICE_AGENT_SYSTEM_PROMPT,
                    stream_final_answer=False,
                ):
                    if event.type == AgentEventType.THINKING:
                        await ws_client.send_text(
                            _make_event("agent_thinking", thought=event.data.get("thought", ""))
                        )
                        await _send_debug(ws_client, "agent", "thinking", thought=event.data.get("thought", ""))

                    elif event.type == AgentEventType.TOOL_CALL:
                        await ws_client.send_text(
                            _make_event("agent_tool_call", tool=event.data.get("tool", ""), input=event.data.get("input", ""))
                        )
                        await _send_debug(ws_client, "agent", "tool_call", **event.data)

                    elif event.type == AgentEventType.TOOL_RESULT:
                        await ws_client.send_text(
                            _make_event("agent_tool_result", tool=event.data.get("tool", ""), projects_found=event.data.get("projects_found", 0))
                        )
                        await _send_debug(ws_client, "agent", "tool_result", **event.data)

                    elif event.type == AgentEventType.ANSWER_DONE:
                        llm_text = event.data.get("full_text", "")
                        source_projects = event.data.get("source_projects", [])
                        agent_steps = event.data.get("agent_steps", [])

                    elif event.type == AgentEventType.ERROR:
                        await _send_debug(ws_client, "agent", "error", error=event.data.get("error", ""))

                llm_ms = int((time.monotonic() - llm_start) * 1000)

                logger.info(
                    f"Voice chat: Agent response ({llm_ms}ms) = {llm_text[:120]}..."
                )
                await _send_debug(
                    ws_client,
                    "agent",
                    "complete",
                    duration_ms=llm_ms,
                    output_chars=len(llm_text),
                    output_preview=llm_text[:200],
                    projects_found=len(source_projects),
                )
                await ws_client.send_text(
                    _make_event("llm_complete", text=llm_text)
                )

                if not llm_text:
                    await _send_debug(
                        ws_client, "llm", "empty_response"
                    )
                    await ws_client.send_text(
                        _make_event("state", state="idle")
                    )
                    continue

                # ── TTS generation ────────────────────────────────────
                await _send_debug(
                    ws_client,
                    "state",
                    "transition",
                    to="speaking",
                )
                await ws_client.send_text(
                    _make_event("state", state="speaking")
                )

                tts_start = time.monotonic()
                await _send_debug(
                    ws_client,
                    "tts",
                    "request_started",
                    input_chars=len(llm_text),
                    voice=selected_voice,
                )

                wav_bytes = await generate_speech(llm_text, voice=selected_voice)
                tts_ms = int((time.monotonic() - tts_start) * 1000)

                logger.info(
                    f"Voice chat: TTS audio ({tts_ms}ms, {len(wav_bytes)} bytes)"
                )
                await _send_debug(
                    ws_client,
                    "tts",
                    "audio_received",
                    duration_ms=tts_ms,
                    audio_bytes=len(wav_bytes),
                )

                # Send audio to client
                await ws_client.send_bytes(wav_bytes)
                await _send_debug(ws_client, "audio", "sent_to_client", bytes=len(wav_bytes))

                turn_ms = int((time.monotonic() - turn_start) * 1000)

                # ── Persist turns to DB ───────────────────────────────
                await _send_debug(ws_client, "ws", "saving_turns", thread_id=thread_id)
                create_turn(
                    thread_id=thread_id,
                    role="user",
                    text=transcription,
                    stt_duration_ms=stt_ms,
                )
                create_turn(
                    thread_id=thread_id,
                    role="assistant",
                    text=llm_text,
                    tts_voice=selected_voice,
                    llm_duration_ms=llm_ms,
                    tts_duration_ms=tts_ms,
                    agent_steps=agent_steps if agent_steps else None,
                )
                await _send_debug(ws_client, "ws", "turns_saved", thread_id=thread_id)

                # Auto-title after the first user message
                turn_count_in_session += 1
                if turn_count_in_session == 1:
                    # Check if thread still has default title
                    t = get_thread(thread_id, include_turns=False)
                    if t and t.title == "New conversation":
                        asyncio.create_task(
                            _auto_title_thread(thread_id, transcription)
                        )

                await _send_debug(
                    ws_client,
                    "state",
                    "transition",
                    to="idle",
                    turn_total_ms=turn_ms,
                    stt_ms=stt_ms,
                    llm_ms=llm_ms,
                    tts_ms=tts_ms,
                )

                await ws_client.send_text(_make_event("turn_complete"))
                await ws_client.send_text(_make_event("state", state="idle"))

            except Exception as e:
                logger.error(f"Voice chat turn error: {e}", exc_info=True)
                await _send_debug(
                    ws_client, "ws", "turn_error", error=str(e)
                )
                try:
                    await ws_client.send_text(
                        _make_event("error", message=str(e))
                    )
                    await ws_client.send_text(
                        _make_event("state", state="idle")
                    )
                except Exception:
                    break
            finally:
                if stt_ws is not None:
                    try:
                        await stt_ws.close()
                    except Exception:
                        pass

    except WebSocketDisconnect:
        logger.info("Voice chat: client disconnected")
    except Exception as e:
        logger.error(f"Voice chat fatal error: {e}", exc_info=True)
    finally:
        logger.info("Voice chat: connection closed")
