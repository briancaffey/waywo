"""Voice thread and turn CRUD operations."""

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import desc

from src.db.database import SessionLocal
from src.db.models import VoiceThreadDB, VoiceTurnDB
from src.models import VoiceThread, VoiceTurn


def _turn_from_db(t: VoiceTurnDB) -> VoiceTurn:
    agent_steps = []
    if t.agent_steps_json:
        try:
            agent_steps = json.loads(t.agent_steps_json)
        except (json.JSONDecodeError, TypeError):
            pass
    return VoiceTurn(
        id=t.id,
        thread_id=t.thread_id,
        role=t.role,
        text=t.text,
        audio_duration_seconds=t.audio_duration_seconds,
        tts_voice=t.tts_voice,
        token_count=t.token_count,
        llm_duration_ms=t.llm_duration_ms,
        tts_duration_ms=t.tts_duration_ms,
        stt_duration_ms=t.stt_duration_ms,
        agent_steps=agent_steps,
        created_at=t.created_at,
    )


def _thread_from_db(
    t: VoiceThreadDB, include_turns: bool = False
) -> VoiceThread:
    turns = []
    if include_turns:
        turns = [_turn_from_db(turn) for turn in t.turns]
    return VoiceThread(
        id=t.id,
        title=t.title,
        system_prompt=t.system_prompt,
        created_at=t.created_at,
        updated_at=t.updated_at,
        turns=turns,
    )


# ---------------------------------------------------------------------------
# Thread CRUD
# ---------------------------------------------------------------------------


def create_thread(title: str = "New conversation") -> VoiceThread:
    with SessionLocal() as session:
        thread = VoiceThreadDB(
            id=str(uuid.uuid4()),
            title=title,
        )
        session.add(thread)
        session.commit()
        session.refresh(thread)
        return _thread_from_db(thread)


def get_thread(thread_id: str, include_turns: bool = True) -> Optional[VoiceThread]:
    with SessionLocal() as session:
        thread = session.get(VoiceThreadDB, thread_id)
        if thread is None:
            return None
        return _thread_from_db(thread, include_turns=include_turns)


def list_threads(limit: int = 50, offset: int = 0) -> list[VoiceThread]:
    with SessionLocal() as session:
        threads = (
            session.query(VoiceThreadDB)
            .order_by(desc(VoiceThreadDB.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_thread_from_db(t, include_turns=False) for t in threads]


def update_thread(thread_id: str, title: str) -> Optional[VoiceThread]:
    with SessionLocal() as session:
        thread = session.get(VoiceThreadDB, thread_id)
        if thread is None:
            return None
        thread.title = title
        thread.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(thread)
        return _thread_from_db(thread)


def delete_thread(thread_id: str) -> bool:
    with SessionLocal() as session:
        thread = session.get(VoiceThreadDB, thread_id)
        if thread is None:
            return False
        session.delete(thread)
        session.commit()
        return True


def search_threads(query: str, limit: int = 20) -> list[VoiceThread]:
    with SessionLocal() as session:
        threads = (
            session.query(VoiceThreadDB)
            .filter(VoiceThreadDB.title.ilike(f"%{query}%"))
            .order_by(desc(VoiceThreadDB.updated_at))
            .limit(limit)
            .all()
        )
        return [_thread_from_db(t, include_turns=False) for t in threads]


def get_thread_count() -> int:
    with SessionLocal() as session:
        return session.query(VoiceThreadDB).count()


# ---------------------------------------------------------------------------
# Turn CRUD
# ---------------------------------------------------------------------------


def create_turn(
    thread_id: str,
    role: str,
    text: str,
    audio_duration_seconds: Optional[float] = None,
    tts_voice: Optional[str] = None,
    stt_raw_json: Optional[str] = None,
    token_count: Optional[int] = None,
    llm_duration_ms: Optional[int] = None,
    tts_duration_ms: Optional[int] = None,
    stt_duration_ms: Optional[int] = None,
    agent_steps: list[dict] | None = None,
) -> VoiceTurn:
    with SessionLocal() as session:
        steps_json = json.dumps(agent_steps) if agent_steps else None
        turn = VoiceTurnDB(
            thread_id=thread_id,
            role=role,
            text=text,
            audio_duration_seconds=audio_duration_seconds,
            tts_voice=tts_voice,
            stt_raw_json=stt_raw_json,
            token_count=token_count,
            llm_duration_ms=llm_duration_ms,
            tts_duration_ms=tts_duration_ms,
            stt_duration_ms=stt_duration_ms,
            agent_steps_json=steps_json,
        )
        session.add(turn)
        # Also bump the thread's updated_at
        thread = session.get(VoiceThreadDB, thread_id)
        if thread:
            thread.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(turn)
        return _turn_from_db(turn)


def get_turns(
    thread_id: str, limit: Optional[int] = None
) -> list[VoiceTurn]:
    with SessionLocal() as session:
        q = (
            session.query(VoiceTurnDB)
            .filter(VoiceTurnDB.thread_id == thread_id)
            .order_by(VoiceTurnDB.created_at)
        )
        if limit:
            q = q.limit(limit)
        return [_turn_from_db(t) for t in q.all()]
