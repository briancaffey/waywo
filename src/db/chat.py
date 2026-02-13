"""Chat thread and turn CRUD operations."""

import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import desc

from src.db.database import SessionLocal
from src.db.models import ChatThreadDB, ChatTurnDB
from src.models import ChatThread, ChatTurn


def _turn_from_db(t: ChatTurnDB) -> ChatTurn:
    source_projects = []
    if t.source_projects_json:
        try:
            source_projects = json.loads(t.source_projects_json)
        except (json.JSONDecodeError, TypeError):
            pass
    agent_steps = []
    if t.agent_steps_json:
        try:
            agent_steps = json.loads(t.agent_steps_json)
        except (json.JSONDecodeError, TypeError):
            pass
    return ChatTurn(
        id=t.id,
        thread_id=t.thread_id,
        role=t.role,
        text=t.text,
        source_projects=source_projects,
        llm_duration_ms=t.llm_duration_ms,
        rag_triggered=t.rag_triggered,
        agent_steps=agent_steps,
        created_at=t.created_at,
    )


def _thread_from_db(
    t: ChatThreadDB, include_turns: bool = False
) -> ChatThread:
    turns = []
    if include_turns:
        turns = [_turn_from_db(turn) for turn in t.turns]
    return ChatThread(
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


def create_thread(title: str = "New conversation") -> ChatThread:
    with SessionLocal() as session:
        thread = ChatThreadDB(
            id=str(uuid.uuid4()),
            title=title,
        )
        session.add(thread)
        session.commit()
        session.refresh(thread)
        return _thread_from_db(thread)


def get_thread(thread_id: str, include_turns: bool = True) -> Optional[ChatThread]:
    with SessionLocal() as session:
        thread = session.get(ChatThreadDB, thread_id)
        if thread is None:
            return None
        return _thread_from_db(thread, include_turns=include_turns)


def list_threads(limit: int = 50, offset: int = 0) -> list[ChatThread]:
    with SessionLocal() as session:
        threads = (
            session.query(ChatThreadDB)
            .order_by(desc(ChatThreadDB.updated_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [_thread_from_db(t, include_turns=False) for t in threads]


def update_thread(thread_id: str, title: str) -> Optional[ChatThread]:
    with SessionLocal() as session:
        thread = session.get(ChatThreadDB, thread_id)
        if thread is None:
            return None
        thread.title = title
        thread.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(thread)
        return _thread_from_db(thread)


def delete_thread(thread_id: str) -> bool:
    with SessionLocal() as session:
        thread = session.get(ChatThreadDB, thread_id)
        if thread is None:
            return False
        session.delete(thread)
        session.commit()
        return True


def search_threads(query: str, limit: int = 20) -> list[ChatThread]:
    with SessionLocal() as session:
        threads = (
            session.query(ChatThreadDB)
            .filter(ChatThreadDB.title.ilike(f"%{query}%"))
            .order_by(desc(ChatThreadDB.updated_at))
            .limit(limit)
            .all()
        )
        return [_thread_from_db(t, include_turns=False) for t in threads]


def get_thread_count() -> int:
    with SessionLocal() as session:
        return session.query(ChatThreadDB).count()


# ---------------------------------------------------------------------------
# Turn CRUD
# ---------------------------------------------------------------------------


def create_turn(
    thread_id: str,
    role: str,
    text: str,
    source_projects: list[dict] | None = None,
    llm_duration_ms: int | None = None,
    rag_triggered: bool | None = None,
    agent_steps: list[dict] | None = None,
) -> ChatTurn:
    with SessionLocal() as session:
        source_json = json.dumps(source_projects) if source_projects else None
        steps_json = json.dumps(agent_steps) if agent_steps else None
        turn = ChatTurnDB(
            thread_id=thread_id,
            role=role,
            text=text,
            source_projects_json=source_json,
            llm_duration_ms=llm_duration_ms,
            rag_triggered=rag_triggered,
            agent_steps_json=steps_json,
        )
        session.add(turn)
        # Bump thread's updated_at
        thread = session.get(ChatThreadDB, thread_id)
        if thread:
            thread.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(turn)
        return _turn_from_db(turn)


def get_turns(
    thread_id: str, limit: int | None = None
) -> list[ChatTurn]:
    with SessionLocal() as session:
        q = (
            session.query(ChatTurnDB)
            .filter(ChatTurnDB.thread_id == thread_id)
            .order_by(ChatTurnDB.created_at)
        )
        if limit:
            q = q.limit(limit)
        return [_turn_from_db(t) for t in q.all()]
