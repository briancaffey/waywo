import aiosqlite
import os
from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "narration.db")


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                text TEXT NOT NULL,
                sanitized_text TEXT NOT NULL,
                service TEXT NOT NULL DEFAULT 'dia',
                status TEXT NOT NULL DEFAULT 'pending',
                audio_path TEXT,
                duration_seconds REAL,
                error_message TEXT,
                selected_variant_id INTEGER,
                voice_sample_id INTEGER,
                magpie_voice TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS variants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                segment_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                sanitized_text TEXT NOT NULL,
                service TEXT NOT NULL,
                audio_path TEXT,
                duration_seconds REAL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (segment_id) REFERENCES segments(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS voice_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                audio_path TEXT NOT NULL,
                transcript TEXT NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    finally:
        await db.close()


def row_to_dict(row: aiosqlite.Row) -> dict:
    return dict(row)


# --- Projects ---

async def list_projects() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


async def get_project(project_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        return row_to_dict(row) if row else None
    finally:
        await db.close()


async def create_project(name: str, description: str = "") -> dict:
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            "INSERT INTO projects (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, description, now, now),
        )
        await db.commit()
        return await get_project(cursor.lastrowid)
    finally:
        await db.close()


async def update_project(project_id: int, **kwargs) -> dict | None:
    db = await get_db()
    try:
        allowed = {"name", "description"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return await get_project(project_id)
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [project_id]
        await db.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        await db.commit()
        return await get_project(project_id)
    finally:
        await db.close()


async def delete_project(project_id: int) -> bool:
    """Delete a project and all its segments/variants. Returns True if deleted."""
    db = await get_db()
    try:
        # CASCADE handles segments and variants
        cursor = await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def get_project_audio_paths(project_id: int) -> list[str]:
    """Get all audio file paths for a project (segments + variants)."""
    db = await get_db()
    try:
        paths = []
        cursor = await db.execute(
            "SELECT audio_path FROM segments WHERE project_id = ? AND audio_path IS NOT NULL",
            (project_id,),
        )
        for row in await cursor.fetchall():
            paths.append(row["audio_path"])
        cursor = await db.execute(
            """SELECT v.audio_path FROM variants v
               JOIN segments s ON v.segment_id = s.id
               WHERE s.project_id = ? AND v.audio_path IS NOT NULL""",
            (project_id,),
        )
        for row in await cursor.fetchall():
            paths.append(row["audio_path"])
        return paths
    finally:
        await db.close()


# --- Segments ---

async def list_segments(project_id: int) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM segments WHERE project_id = ? ORDER BY position ASC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


async def get_segment(segment_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM segments WHERE id = ?", (segment_id,))
        row = await cursor.fetchone()
        return row_to_dict(row) if row else None
    finally:
        await db.close()


async def create_segment(project_id: int, text: str, sanitized_text: str, position: int, service: str = "dia", voice_sample_id: int | None = None, magpie_voice: str | None = None) -> dict:
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            """INSERT INTO segments (project_id, text, sanitized_text, position, service, status, voice_sample_id, magpie_voice, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
            (project_id, text, sanitized_text, position, service, voice_sample_id, magpie_voice, now, now),
        )
        await db.commit()
        return await get_segment(cursor.lastrowid)
    finally:
        await db.close()


async def update_segment(segment_id: int, **kwargs) -> dict | None:
    db = await get_db()
    try:
        allowed = {"text", "sanitized_text", "position", "service", "status", "audio_path", "duration_seconds", "error_message", "selected_variant_id", "voice_sample_id", "magpie_voice"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return await get_segment(segment_id)
        updates["updated_at"] = datetime.utcnow().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [segment_id]
        await db.execute(f"UPDATE segments SET {set_clause} WHERE id = ?", values)
        await db.commit()
        return await get_segment(segment_id)
    finally:
        await db.close()


async def delete_segment(segment_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM segments WHERE id = ?", (segment_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def reorder_segments(ordering: list[dict]) -> None:
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        for item in ordering:
            await db.execute(
                "UPDATE segments SET position = ?, updated_at = ? WHERE id = ?",
                (item["position"], now, item["id"]),
            )
        await db.commit()
    finally:
        await db.close()


async def import_script(project_id: int, lines: list[str], service: str = "dia") -> list[dict]:
    from app.services.sanitize import sanitize_text

    db = await get_db()
    try:
        # Clear existing variants and segments for this project
        await db.execute(
            "DELETE FROM variants WHERE segment_id IN (SELECT id FROM segments WHERE project_id = ?)",
            (project_id,),
        )
        await db.execute("DELETE FROM segments WHERE project_id = ?", (project_id,))
        now = datetime.utcnow().isoformat()
        for i, line in enumerate(lines, 1):
            sanitized = sanitize_text(line)
            await db.execute(
                """INSERT INTO segments (project_id, text, sanitized_text, position, service, status, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
                (project_id, line, sanitized, i, service, now, now),
            )
        await db.commit()
    finally:
        await db.close()
    return await list_segments(project_id)


async def delete_all_segments(project_id: int) -> int:
    """Delete all segments and variants for a project. Returns count deleted."""
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM variants WHERE segment_id IN (SELECT id FROM segments WHERE project_id = ?)",
            (project_id,),
        )
        cursor = await db.execute("DELETE FROM segments WHERE project_id = ?", (project_id,))
        await db.commit()
        return cursor.rowcount
    finally:
        await db.close()


# --- Variants ---

async def create_variant(segment_id: int, text: str, sanitized_text: str, service: str, audio_path: str, duration_seconds: float) -> dict:
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            """INSERT INTO variants (segment_id, text, sanitized_text, service, audio_path, duration_seconds, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (segment_id, text, sanitized_text, service, audio_path, duration_seconds, now),
        )
        await db.commit()
        return await get_variant(cursor.lastrowid)
    finally:
        await db.close()


async def get_variant(variant_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM variants WHERE id = ?", (variant_id,))
        row = await cursor.fetchone()
        return row_to_dict(row) if row else None
    finally:
        await db.close()


async def list_variants(segment_id: int) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM variants WHERE segment_id = ? ORDER BY created_at DESC", (segment_id,)
        )
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


async def delete_variant(variant_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM variants WHERE id = ?", (variant_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


# --- Voice Samples ---

async def list_voice_samples() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM voice_samples ORDER BY created_at ASC")
        rows = await cursor.fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        await db.close()


async def get_voice_sample(sample_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM voice_samples WHERE id = ?", (sample_id,))
        row = await cursor.fetchone()
        return row_to_dict(row) if row else None
    finally:
        await db.close()


async def create_voice_sample(name: str, audio_path: str, transcript: str = "") -> dict:
    db = await get_db()
    try:
        now = datetime.utcnow().isoformat()
        cursor = await db.execute(
            "INSERT INTO voice_samples (name, audio_path, transcript, created_at) VALUES (?, ?, ?, ?)",
            (name, audio_path, transcript, now),
        )
        await db.commit()
        return await get_voice_sample(cursor.lastrowid)
    finally:
        await db.close()


async def delete_voice_sample(sample_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM voice_samples WHERE id = ?", (sample_id,))
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()
