# Analytics Tool Plan

Add a `run_analytics_query` tool to the chatbot agent, allowing it to answer aggregate/statistical questions by writing and executing read-only SQL against the SQLite database.

**Example questions this enables:**
- "How many projects are tagged with both ai and nutrition that were added in 2026?"
- "What's the average idea score for projects tagged with machine-learning?"
- "Which hashtags appear most frequently?"
- "How many projects were added each month?"

## What needs to change

### 1. New file: `src/agent/analytics.py`

A small module with two functions:

**`validate_sql(sql: str) -> str | None`**
- Returns an error message if the query is unsafe, or `None` if it's OK.
- Rejects any SQL containing DML/DDL keywords: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `ATTACH`, `DETACH`, `PRAGMA`, `GRANT`, `REVOKE`, `REPLACE`, `REINDEX`, `VACUUM`.
- Rejects multiple statements (no internal semicolons after stripping the trailing one).
- Requires the query to start with `SELECT` (case-insensitive, after stripping whitespace).

**`execute_readonly_query(sql: str, timeout_seconds: float = 10.0) -> str`**
- Opens a **separate read-only SQLite connection** using `sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)`.
- This connection is independent of the main SQLAlchemy engine — no risk of affecting it.
- Sets `PRAGMA query_only = ON` as a belt-and-suspenders layer.
- Appends `LIMIT 200` if no LIMIT clause is present.
- Runs the query in a thread with a timeout (using `asyncio.to_thread` + `asyncio.wait_for`).
- Formats results as a markdown table (column headers + rows).
- Truncates output to ~4000 chars if it's too large for the LLM context.
- Returns a formatted string (the result table, or an error message).

### 2. Update: `src/agent/tools.py`

Add a third tool to `AGENT_TOOLS` and `TOOL_SCHEMAS`:

**`_run_analytics_query(sql: str, explanation: str) -> tuple[str, list[dict]]`**
- Calls `validate_sql()` — if invalid, returns the error as observation text.
- Calls `execute_readonly_query()` — returns the result table as observation text.
- Always returns an empty `source_projects` list (analytics doesn't reference individual projects).

**Tool schema** (OpenAI function-calling format):
```json
{
  "type": "function",
  "function": {
    "name": "run_analytics_query",
    "description": "Run a read-only SQL query against the project database for analytics. Use for counting, aggregating, filtering, or statistical questions. Only SELECT queries allowed. The database is SQLite — use json_each() to query JSON array columns like hashtags.",
    "parameters": {
      "type": "object",
      "properties": {
        "sql": {
          "type": "string",
          "description": "A read-only SELECT query."
        },
        "explanation": {
          "type": "string",
          "description": "Brief explanation of what this query does and why it answers the user's question."
        }
      },
      "required": ["sql", "explanation"]
    }
  }
}
```

No changes needed to `engine.py` — it already dispatches dynamically via `get_tool(name)`.

### 3. Update: `src/agent/prompts.py`

Add to the `TEXT_AGENT_SYSTEM_PROMPT` (and optionally `VOICE_AGENT_SYSTEM_PROMPT`):

- Instructions for when to use `run_analytics_query` vs `search_projects` (analytics for counting/aggregating/statistics; search for finding specific projects by topic).
- The database schema for the tables the LLM can query, written as DDL with comments. Focus on `waywo_projects` since that's the main table for user-facing analytics:

```
-- Available tables and columns for analytics queries:

-- waywo_projects: the main project table
--   id (INTEGER PK), title (TEXT), short_description (TEXT), description (TEXT)
--   hashtags (TEXT, JSON array of strings — query with json_each, e.g.: json_each(hashtags))
--   idea_score (INTEGER 1-10), complexity_score (INTEGER 1-10)
--   is_valid_project (BOOLEAN), source (TEXT: "hn" or "nemo_data_designer")
--   primary_url (TEXT), source_comment_id (INTEGER FK)
--   created_at (DATETIME), processed_at (DATETIME)

-- waywo_posts: Hacker News "What are you working on?" threads
--   id (INTEGER PK, HN item ID), title (TEXT), year (INTEGER), month (INTEGER)
--   by (TEXT, HN username), score (INTEGER), descendants (INTEGER)

-- waywo_comments: top-level comments on posts (each may yield projects)
--   id (INTEGER PK, HN item ID), by (TEXT, HN username), parent (INTEGER FK to waywo_posts)
--   text (TEXT), processed (BOOLEAN)

-- waywo_project_submissions: tracks when a project appears in a comment
--   id (INTEGER PK), project_id (FK), comment_id (FK)
--   similarity_score (FLOAT), extracted_text (TEXT)
```

- A note about SQLite JSON functions: `json_each(column)` to unpack JSON arrays, query with `value` field.
- A few example question/SQL pairs to prime the LLM:

```
Example: "How many projects are tagged with both ai and nutrition?"
SQL: SELECT COUNT(*) FROM waywo_projects
     WHERE id IN (SELECT wp.id FROM waywo_projects wp, json_each(wp.hashtags) t WHERE t.value = 'ai')
       AND id IN (SELECT wp.id FROM waywo_projects wp, json_each(wp.hashtags) t WHERE t.value = 'nutrition')
       AND is_valid_project = 1
```

### 4. New test: `src/test/test_analytics.py`

Tests for the validation and execution logic:
- `validate_sql` rejects DML/DDL (`INSERT`, `DROP`, etc.)
- `validate_sql` rejects multiple statements
- `validate_sql` accepts valid SELECT queries
- `execute_readonly_query` returns results for a simple `SELECT 1`
- `execute_readonly_query` appends LIMIT when missing
- `execute_readonly_query` times out on slow queries
- Integration: `_run_analytics_query` tool returns formatted results

## Safety summary

| Layer | Protection |
|-------|-----------|
| Connection | `?mode=ro` — SQLite enforces read-only at the filesystem level |
| PRAGMA | `query_only = ON` — SQLite rejects writes even if mode check is bypassed |
| Validation | Keyword blocklist rejects DML/DDL before execution |
| Single-statement | No semicolons allowed (prevents injection chaining) |
| Row limit | Auto-appended `LIMIT 200` prevents huge result sets |
| Timeout | 10-second cap prevents runaway queries |
| Output cap | Results truncated to ~4000 chars |

## Files touched

| File | Change |
|------|--------|
| `src/agent/analytics.py` | **New** — `validate_sql()` + `execute_readonly_query()` |
| `src/agent/tools.py` | Add `_run_analytics_query`, register in `AGENT_TOOLS` + `TOOL_SCHEMAS` |
| `src/agent/prompts.py` | Add schema context + analytics instructions to system prompts |
| `src/test/test_analytics.py` | **New** — unit tests for validation and execution |
