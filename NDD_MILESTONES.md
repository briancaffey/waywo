# NeMo DataDesigner — Implementation Milestones

Reference: `NDD_PLAN.md` for full design.

---

## Milestone 1: Dependency & Install Verification

**Goal**: Add `data-designer` and confirm it installs without conflicts.

### Tasks
- [ ] Add `data-designer>=0.4.0` to `pyproject.toml` under `[project.dependencies]`
- [ ] Run `pip install -e .` (or `uv pip install -e .`) and verify clean install
- [ ] Smoke-test: `python -c "import data_designer; print(data_designer.__version__)"`

### Done when
- Import succeeds, no dependency conflicts with existing packages (FastAPI, LlamaIndex, Celery, etc.)

---

## Milestone 2: Database & Model Changes

**Goal**: Add the `source` column to distinguish generated projects from HN projects, and make `source_comment_id` nullable so generated projects don't need a fake comment reference.

### Why source_comment_id must become nullable
- Currently `source_comment_id` is `Integer, ForeignKey("waywo_comments.id"), nullable=False`
- Generated projects have no HN comment — there is no real comment to point to
- Several places join on `source_comment_id` to get comment timestamps; these joins must become LEFT JOINs (or be guarded) so generated projects don't break queries

### Database changes (`src/db/models.py`)

1. **Make `source_comment_id` nullable**:
   ```python
   source_comment_id: Mapped[Optional[int]] = mapped_column(
       Integer, ForeignKey("waywo_comments.id"), nullable=True
   )
   ```

2. **Add `source` column**:
   ```python
   source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
   ```
   Values: `"hn"`, `"nemo_data_designer"`, or `NULL` (legacy, treated as `"hn"`)

3. **Add index**: `Index("ix_waywo_projects_source", "source")`

### Migration (`src/db/migrate.py`)

SQLite can't ALTER a column to nullable, so for `source_comment_id` we need the copy-to-temp pattern:
1. Create temp table with new schema
2. Copy data from old table
3. Drop old table
4. Rename temp to original

For the new `source` column, a simple `ALTER TABLE ADD COLUMN` suffices.

### Pydantic model changes (`src/models.py`)

- `WaywoProject.source_comment_id`: `int` → `Optional[int] = None`
- `WaywoProject`: add `source: Optional[str] = None`
- `WaywoProjectSummary.source_comment_id`: `int` → `Optional[int] = None`
- `WaywoProjectSummary`: add `source: Optional[str] = None`
- `WaywoProjectListFilters`: add `source: Optional[str] = None`

### Query changes (`src/db/projects.py`)

- `get_project()` and `get_all_projects()` use outer joins to `WaywoCommentDB` — verify these are already LEFT JOINs (they use `outerjoin`, so they should be fine)
- `save_project()` — no change needed (source_comment_id can now be None)
- Add `source` filter to `get_all_projects()` query builder

### Route changes (`src/routes/projects.py`)

- Accept `source` query param on `GET /api/waywo-projects`
- Pass through to query builder

### Frontend detail page (`frontend/app/pages/projects/[id].vue`)

- Guard "Original Comment" section: only show when `source_comment_id` is not null

### Done when
- Existing HN projects still load and display correctly
- A project with `source_comment_id=NULL` and `source="nemo_data_designer"` can be saved and queried
- Project list can be filtered by `source`

---

## Milestone 3: NDD Client & Pipeline

**Goal**: Create the DataDesigner configuration and pipeline definition as standalone modules that can be tested independently.

### New file: `src/ndd_config.py`

Provider and model configuration using existing env vars (`LLM_BASE_URL`, `LLM_MODEL_NAME`, `LLM_API_KEY` from `src/llm_config.py` / `docker-compose.yml`):

- `build_ndd_provider()` → `ModelProvider` pointing at the same LLM endpoint
- `build_ndd_models(creativity: float)` → dict of three `ModelConfig` aliases:
  - `waywo-creative` (temperature=creativity, for idea generation)
  - `waywo-structured` (temperature=0.1, for JSON extraction)
  - `waywo-judge` (temperature=0.2, for scoring)

### New file: `src/ndd_pipeline.py`

Pipeline definition with all columns from `NDD_PLAN.md`:

- `build_tag_cooccurrence(projects)` — compute tag co-occurrence from existing projects in DB
- `build_pipeline_config(models, seed_tags, tag_cooccurrence)` — returns the full column pipeline:
  1. `primary_tag` (SamplerColumn — from seed_tags or full vocabulary)
  2. `secondary_tags` (SamplerColumn — co-occurring tags)
  3. `target_audience` (SamplerColumn — persona list)
  4. `target_complexity` (SamplerColumn — uniform 1-10)
  5. `project_idea` (LLMTextColumn — creative generation)
  6. `metadata` (LLMStructuredColumn — title, short_description, description, hashtags)
  7. `idea_quality` (LLMJudgeColumn — idea_score + complexity_score)
  8. Expression columns to flatten metadata fields

### Done when
- Both modules import cleanly
- Config reads from env vars correctly
- Pipeline config builds without errors (can validate structure without running LLM)

---

## Milestone 4: Notebook for Testing

**Goal**: Create `notebooks/ndd_test.ipynb` to interactively test the pipeline before wiring it into the full stack.

### Notebook cells

1. **Setup** — imports, env var verification, provider/model instantiation
2. **Tag data** — load existing projects from DB, build co-occurrence map, inspect it
3. **Pipeline preview** — run `DataDesigner.preview(config, num_records=2-3)`, inspect DataFrame
4. **Validate output** — check that output columns match `WaywoProjectDB` fields
5. **Prompt iteration** — tweak prompts, re-run preview, compare quality
6. **Embedding test** — take a generated row, run it through `create_embedding_text()` → `get_single_embedding()`, verify vector shape
7. **Full save test** — save one generated project to DB with `source="nemo_data_designer"`, verify it appears in project list

### Done when
- Preview generates valid-looking projects with all required fields
- Prompts produce quality output (good titles, coherent descriptions, sensible tags)
- Embedding integration works end-to-end
- At least one generated project is saved and queryable

---

## Milestone 5: Celery Task & API Endpoints

**Goal**: Wire the pipeline into the existing async task infrastructure so the frontend can trigger and monitor generation runs.

### Celery task (`src/worker/tasks.py`)

`generate_ideas(num_ideas, seed_tags, creativity)`:
1. Build tag co-occurrence from DB
2. Configure DataDesigner provider + models
3. Build pipeline config
4. Run `data_designer.create(config, num_records=num_ideas)`
5. Post-process each row: generate embedding, save to DB with `source="nemo_data_designer"`
6. Report progress via Celery task state updates

### New API routes (new file: `src/routes/generate.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate-ideas` | POST | Accept `GenerateIdeasRequest`, enqueue Celery task, return task ID |
| `/api/generate-ideas/{task_id}/status` | GET | Return task state (PENDING/STARTED/SUCCESS/FAILURE + result) |

### New Pydantic models (`src/models.py`)

```python
class GenerateIdeasRequest(BaseModel):
    num_ideas: int = Field(default=5, ge=1, le=50)
    seed_tags: Optional[list[str]] = None
    creativity: float = Field(default=0.85, ge=0.1, le=1.5)

class GenerateIdeasResponse(BaseModel):
    task_id: str
    num_requested: int
    seed_tags: list[str]
```

### Update HN workflow

In `src/worker/tasks.py`, update `process_waywo_comment` to set `source="hn"` when saving projects, so all new HN projects are tagged.

### Done when
- `POST /api/generate-ideas` returns a task ID
- Task runs to completion in Celery worker
- Generated projects appear in DB with correct `source`
- `GET /api/waywo-projects?source=nemo_data_designer` returns only generated projects
- Existing HN project processing still works (now with `source="hn"`)

---

## Milestone 6: Frontend UI

**Goal**: Add generation controls and source-aware display to the project pages.

### Projects list page (`frontend/app/pages/projects/index.vue`)

1. **Source filter tabs**: "All" | "From HN" | "AI Generated" — maps to `source` query param
2. **"Generate Ideas" button**: Opens a dialog/drawer
3. **AI badge on project cards**: Small chip/badge for `source === "nemo_data_designer"`

### Generate Ideas dialog

- **Tag multi-select**: Populated from existing `GET /api/waywo-projects/hashtags` endpoint
- **Number of ideas**: Input or slider, 1-50, default 5
- **Creativity slider**: 0.3 (conservative) → 0.85 (balanced) → 1.2 (wild)
- **Generate button**: Calls `POST /api/generate-ideas`, shows loading state
- **Polling**: Polls status endpoint until complete, then shows toast and refreshes list

### Project detail page (`frontend/app/pages/projects/[id].vue`)

- Show "AI Generated" badge when `source === "nemo_data_designer"`
- Hide "Original Comment" section when `source_comment_id` is null
- Everything else (scores, tags, description, similar projects, bookmark) works identically

### Done when
- User can filter projects by source
- User can open dialog, pick tags, set options, and trigger generation
- Generation progress is visible (loading state)
- Generated projects display with badge and without comment section
- Existing project display is unaffected
