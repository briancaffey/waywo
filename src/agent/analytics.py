"""Read-only SQL analytics for the chatbot agent.

Provides safe query validation and execution against the SQLite database.
"""

import asyncio
import logging
import re
import sqlite3

from src.db.database import DATABASE_PATH

logger = logging.getLogger(__name__)

# Keywords that indicate a write/destructive operation
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|"
    r"ATTACH|DETACH|PRAGMA|GRANT|REVOKE|REPLACE|REINDEX|VACUUM"
    r")\b",
    re.IGNORECASE,
)

_MAX_RESULT_CHARS = 4000
_DEFAULT_ROW_LIMIT = 200
_DEFAULT_TIMEOUT = 10.0


def validate_sql(sql: str) -> str | None:
    """Validate that a SQL string is a safe read-only SELECT.

    Returns an error message if the query is unsafe, or None if it's OK.
    """
    stripped = sql.strip().rstrip(";").strip()

    if not stripped:
        return "Empty query."

    # Must start with SELECT
    if not stripped.upper().startswith("SELECT"):
        return "Only SELECT queries are allowed."

    # Reject forbidden keywords
    match = _FORBIDDEN_KEYWORDS.search(stripped)
    if match:
        return f"Forbidden keyword: {match.group(0).upper()}. Only SELECT queries are allowed."

    # Reject multiple statements (semicolons inside the query body)
    # Strip string literals first to avoid false positives on semicolons inside strings
    no_strings = re.sub(r"'[^']*'", "", stripped)
    if ";" in no_strings:
        return "Multiple statements are not allowed."

    return None


def _append_limit(sql: str, limit: int = _DEFAULT_ROW_LIMIT) -> str:
    """Append a LIMIT clause if one isn't already present."""
    stripped = sql.strip().rstrip(";").strip()
    if not re.search(r"\bLIMIT\b", stripped, re.IGNORECASE):
        stripped = f"{stripped} LIMIT {limit}"
    return stripped


def _format_results(columns: list[str], rows: list[tuple]) -> str:
    """Format query results as a markdown table."""
    if not rows:
        return "Query returned 0 rows."

    # Build markdown table
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    lines = [header, separator]
    for row in rows:
        cells = " | ".join(str(v) if v is not None else "NULL" for v in row)
        lines.append(f"| {cells} |")

    result = "\n".join(lines)

    # Truncate if too large
    if len(result) > _MAX_RESULT_CHARS:
        truncated = result[:_MAX_RESULT_CHARS]
        # Cut at the last complete row
        last_newline = truncated.rfind("\n")
        if last_newline > 0:
            truncated = truncated[:last_newline]
        result = truncated + f"\n\n... (results truncated, showing partial output of {len(rows)} rows)"

    return result


def _run_query_sync(sql: str) -> str:
    """Execute a read-only query synchronously. Runs in a thread."""
    conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only = ON")
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return _format_results(columns, rows)
    finally:
        conn.close()


async def execute_readonly_query(
    sql: str, timeout_seconds: float = _DEFAULT_TIMEOUT
) -> str:
    """Execute a validated SQL query on a read-only connection with a timeout.

    Returns formatted markdown table or an error message.
    """
    sql = _append_limit(sql)

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_run_query_sync, sql),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        return f"Query timed out after {timeout_seconds} seconds."
    except sqlite3.OperationalError as e:
        logger.warning(f"Analytics query failed: {e}")
        return f"Query error: {e}"
    except Exception as e:
        logger.error(f"Unexpected analytics error: {e}")
        return f"Query error: {e}"
