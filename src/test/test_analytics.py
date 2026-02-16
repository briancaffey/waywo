"""Tests for the analytics SQL validation and execution module."""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.agent.analytics import (
    _append_limit,
    _format_results,
    execute_readonly_query,
    validate_sql,
)


# ---------------------------------------------------------------------------
# validate_sql
# ---------------------------------------------------------------------------


class TestValidateSql:
    def test_valid_select(self):
        assert validate_sql("SELECT COUNT(*) FROM waywo_projects") is None

    def test_valid_select_with_json_each(self):
        sql = (
            "SELECT COUNT(*) FROM waywo_projects, json_each(waywo_projects.hashtags) AS t "
            "WHERE t.value = 'ai'"
        )
        assert validate_sql(sql) is None

    def test_valid_select_with_subquery(self):
        sql = "SELECT * FROM waywo_projects WHERE id IN (SELECT project_id FROM waywo_project_submissions)"
        assert validate_sql(sql) is None

    def test_rejects_empty(self):
        assert validate_sql("") is not None
        assert validate_sql("   ") is not None

    def test_rejects_insert(self):
        assert validate_sql("INSERT INTO waywo_projects (title) VALUES ('hack')") is not None

    def test_rejects_update(self):
        assert validate_sql("UPDATE waywo_projects SET title = 'x'") is not None

    def test_rejects_delete(self):
        assert validate_sql("DELETE FROM waywo_projects") is not None

    def test_rejects_drop(self):
        assert validate_sql("DROP TABLE waywo_projects") is not None

    def test_rejects_alter(self):
        assert validate_sql("ALTER TABLE waywo_projects ADD COLUMN x TEXT") is not None

    def test_rejects_attach(self):
        assert validate_sql("ATTACH DATABASE 'other.db' AS other") is not None

    def test_rejects_forbidden_keyword_in_select(self):
        """Keyword blocklist catches DML hidden inside a SELECT-starting query."""
        result = validate_sql("SELECT 1; INSERT INTO waywo_projects (title) VALUES ('x')")
        assert result is not None

    def test_rejects_pragma(self):
        result = validate_sql("PRAGMA table_info(waywo_projects)")
        assert result is not None

    def test_rejects_multiple_statements(self):
        result = validate_sql("SELECT 1; DROP TABLE waywo_projects")
        assert result is not None
        assert "Multiple statements" in result or "Forbidden" in result

    def test_allows_semicolons_in_strings(self):
        sql = "SELECT * FROM waywo_projects WHERE title = 'hello; world'"
        assert validate_sql(sql) is None

    def test_rejects_non_select(self):
        result = validate_sql("WITH cte AS (SELECT 1) DELETE FROM waywo_projects")
        assert result is not None

    def test_trailing_semicolon_ok(self):
        assert validate_sql("SELECT 1;") is None


# ---------------------------------------------------------------------------
# _append_limit
# ---------------------------------------------------------------------------


class TestAppendLimit:
    def test_adds_limit_when_missing(self):
        result = _append_limit("SELECT * FROM waywo_projects")
        assert "LIMIT 200" in result

    def test_preserves_existing_limit(self):
        result = _append_limit("SELECT * FROM waywo_projects LIMIT 10")
        assert "LIMIT 10" in result
        assert "LIMIT 200" not in result

    def test_strips_trailing_semicolon(self):
        result = _append_limit("SELECT 1;")
        assert result.endswith("LIMIT 200")
        assert ";" not in result


# ---------------------------------------------------------------------------
# _format_results
# ---------------------------------------------------------------------------


class TestFormatResults:
    def test_empty_results(self):
        assert "0 rows" in _format_results(["col"], [])

    def test_markdown_table(self):
        result = _format_results(["name", "count"], [("ai", 42), ("ml", 10)])
        assert "| name | count |" in result
        assert "| ai | 42 |" in result
        assert "| ml | 10 |" in result

    def test_null_values(self):
        result = _format_results(["a"], [(None,)])
        assert "NULL" in result

    def test_truncation(self):
        # Generate a large result set
        rows = [(f"row_{i}", i) for i in range(500)]
        result = _format_results(["name", "val"], rows)
        assert "truncated" in result


# ---------------------------------------------------------------------------
# execute_readonly_query (uses a temp DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db(tmp_path):
    """Create a temp SQLite DB with some test data."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE waywo_projects ("
        "  id INTEGER PRIMARY KEY, title TEXT, hashtags TEXT,"
        "  idea_score INTEGER, is_valid_project BOOLEAN, created_at DATETIME"
        ")"
    )
    conn.executemany(
        "INSERT INTO waywo_projects (id, title, hashtags, idea_score, is_valid_project, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (1, "AI App", '["ai", "health"]', 8, 1, "2026-01-15"),
            (2, "ML Tool", '["ml", "ai"]', 7, 1, "2026-02-01"),
            (3, "Web App", '["web"]', 5, 1, "2025-06-01"),
            (4, "Invalid", '["test"]', 3, 0, "2026-01-01"),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


class TestExecuteReadonlyQuery:
    @pytest.mark.asyncio
    async def test_simple_query(self, temp_db):
        with patch("src.agent.analytics.DATABASE_PATH", temp_db):
            result = await execute_readonly_query("SELECT COUNT(*) AS total FROM waywo_projects")
        assert "| total |" in result
        assert "| 4 |" in result

    @pytest.mark.asyncio
    async def test_json_each_query(self, temp_db):
        with patch("src.agent.analytics.DATABASE_PATH", temp_db):
            result = await execute_readonly_query(
                "SELECT COUNT(*) AS count FROM waywo_projects, json_each(waywo_projects.hashtags) AS t "
                "WHERE t.value = 'ai' AND is_valid_project = 1"
            )
        assert "| count |" in result
        assert "| 2 |" in result

    @pytest.mark.asyncio
    async def test_readonly_rejects_write(self, temp_db):
        with patch("src.agent.analytics.DATABASE_PATH", temp_db):
            result = await execute_readonly_query(
                "INSERT INTO waywo_projects (id, title, hashtags, idea_score, is_valid_project, created_at) "
                "VALUES (99, 'x', '[]', 1, 1, '2026-01-01')"
            )
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_auto_limit(self, temp_db):
        with patch("src.agent.analytics.DATABASE_PATH", temp_db):
            result = await execute_readonly_query("SELECT * FROM waywo_projects")
        # Should work (the LIMIT is appended) and return data
        assert "| id |" in result

    @pytest.mark.asyncio
    async def test_timeout(self, temp_db):
        with patch("src.agent.analytics.DATABASE_PATH", temp_db):
            # Use a very short timeout — even a trivial query may or may not time out,
            # but the mechanism shouldn't raise an unhandled exception
            result = await execute_readonly_query("SELECT 1", timeout_seconds=0.0001)
        # Should either return a result or a timeout message, not crash
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Integration: _run_analytics_query tool function
# ---------------------------------------------------------------------------


class TestRunAnalyticsQueryTool:
    @pytest.mark.asyncio
    async def test_valid_query(self, temp_db):
        from src.agent.tools import _run_analytics_query

        with patch("src.agent.analytics.DATABASE_PATH", temp_db):
            text, projects = await _run_analytics_query(
                sql="SELECT COUNT(*) AS total FROM waywo_projects WHERE is_valid_project = 1",
                explanation="Count valid projects",
            )
        assert "| total |" in text
        assert "| 3 |" in text
        assert projects == []

    @pytest.mark.asyncio
    async def test_rejected_query(self, temp_db):
        from src.agent.tools import _run_analytics_query

        text, projects = await _run_analytics_query(
            sql="DROP TABLE waywo_projects",
            explanation="This should be rejected",
        )
        assert "rejected" in text.lower()
        assert projects == []
