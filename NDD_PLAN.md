# NeMo DataDesigner Integration Plan

## Overview

Integrate [NVIDIA NeMo DataDesigner](https://github.com/NVIDIA-NeMo/DataDesigner) into waywo to **generate synthetic project ideas** seeded by the tag taxonomy from real HN projects. Generated projects live in the same `waywo_projects` table with the same fields as HN-sourced projects, distinguished by a `source` column.

---

## What NeMo DataDesigner Is (and Why It Fits)

NeMo DataDesigner is a Python library for generating structured synthetic datasets by orchestrating LLM calls through a column-based pipeline. You define a schema of columns — some are statistical samplers (no LLM needed), others are LLM-generated text, structured output, or quality scores — and DataDesigner generates rows following that schema.

**Why it fits waywo specifically:**

| DataDesigner concept | waywo mapping |
|---------------------|---------------|
| **Sampler columns** (category, subcategory, distributions) | Pick tags from the existing hashtag vocabulary with realistic frequency weights |
| **LLM text columns** (free-form generation with Jinja2 templates) | Generate a project idea description conditioned on the selected tags |
| **LLM structured columns** (JSON output validated against a schema) | Extract title, short_description, description, hashtags — the exact fields `WaywoProjectDB` needs |
| **LLM judge columns** (score rubrics) | Produce `idea_score` and `complexity_score` on the same 1-10 scale HN projects use |
| **Post-pipeline processing** | Generate embeddings via existing embedding service, save to DB |
| **LiteLLM backend** (OpenAI-compatible) | Points directly at the same Nemotron endpoint the rest of waywo uses |
| **Preview mode** (generate 2-3 records for testing) | Iterate on prompts without burning through full generation runs |

The core insight: DataDesigner's pipeline maps almost 1:1 onto the fields of `WaywoProjectDB`. Instead of extracting projects from HN comments (the existing workflow), we're **generating** them from tag combinations. The output schema is identical — the only difference is the source.

---

## How DataDesigner Works — Key Concepts

### Pipeline = ordered list of columns

Each column has a type and can reference earlier columns via `{{ column_name }}` Jinja2 templates. DataDesigner resolves the dependency DAG automatically.

```
Sampler columns (fast, no LLM)
    → LLM text column (creative generation, references sampler outputs)
        → LLM structured column (extract metadata, references text output)
            → LLM judge column (score quality, references structured output)
```

### Column types we'll use

1. **`SamplerColumnConfig`** — Statistical sampling. Picks values from a weighted list. Used for selecting tags, target audience, complexity targets. No LLM calls, essentially free.

2. **`LLMTextColumnConfig`** — Free-form text generation with a Jinja2 prompt template. The workhorse for generating the actual project idea narrative.

3. **`LLMStructuredColumnConfig`** — LLM output validated against a JSON schema (or Pydantic model). Extracts structured fields (title, description, hashtags) from the free-form idea text.

4. **`LLMJudgeColumnConfig`** — Evaluates content against a scoring rubric. Each `Score` has named options mapping score values to descriptions. Returns scores per rubric dimension.

5. **`ExpressionColumnConfig`** — Jinja2 expressions to derive/reshape fields. Used to flatten structured output into individual columns.

### Execution model

- `DataDesigner.preview(config, num_records=3)` — Quick test, returns in-memory DataFrame
- `DataDesigner.create(config, num_records=N, dataset_name="...")` — Full run, saves to disk, returns results handle
- Within a run: rows are batched, columns generated sequentially per dependency order, cells within a column generated in parallel (configurable concurrency)

### LLM connection via LiteLLM

DataDesigner uses LiteLLM under the hood, which supports any OpenAI-compatible endpoint. You configure a `ModelProvider` (endpoint URL + auth) and `ModelConfig` (model name + inference params) and reference them by alias in column definitions.

---

## The Pipeline — From Tags to Projects

Here's the complete data flow, showing how DataDesigner columns map to `WaywoProjectDB` fields:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER INPUT (from frontend)                       │
│  seed_tags: ["ai", "python", "saas"]   num_ideas: 10               │
│  creativity: 0.85                                                   │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│  COLUMN 1: primary_tag          (SamplerColumn — CATEGORY)          │
│  Picks from user's seed_tags with equal weight, OR from full tag    │
│  vocabulary weighted by frequency if no seed tags specified.        │
│  Output: "ai"                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMN 2: secondary_tags       (SamplerColumn — SUBCATEGORY)       │
│  Given primary_tag, picks 2-3 co-occurring tags from pre-computed   │
│  co-occurrence data.                                                │
│  Output: ["llm", "python"]                                          │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMN 3: target_audience      (SamplerColumn — CATEGORY)          │
│  Random audience persona for diversity.                              │
│  Output: "indie hackers"                                            │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMN 4: target_complexity    (SamplerColumn — UNIFORM 1-10)      │
│  Random complexity target to ensure variety.                         │
│  Output: 7                                                          │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMN 5: project_idea         (LLMTextColumn)                     │
│  Prompt: "Generate a project idea for {{ primary_tag }} that also   │
│  involves {{ secondary_tags }}, targeting {{ target_audience }},     │
│  with ~{{ target_complexity }}/10 complexity..."                     │
│  Output: 2-3 paragraph project description (free-form text)         │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMN 6: metadata             (LLMStructuredColumn)               │
│  Prompt: "Extract from this project idea..."                        │
│  Output: {                                                          │
│    "title": "NeuroLint",                                            │
│    "short_description": "AI-powered code review for ML pipelines",  │
│    "description": "A tool that analyzes ML pipeline code for...",   │
│    "hashtags": ["ai", "llm", "python", "developer-tools"]           │
│  }                                                                  │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMN 7: idea_quality         (LLMJudgeColumn)                    │
│  Rubric: idea_score (1-10), complexity_score (1-10)                 │
│  Output: { "idea_score": 7, "complexity_score": 6 }                │
├─────────────────────────────────────────────────────────────────────┤
│  COLUMNS 8-11: Expression columns to flatten metadata               │
│  title = {{ metadata.title }}                                       │
│  short_description = {{ metadata.short_description }}               │
│  description = {{ metadata.description }}                           │
│  hashtags = {{ metadata.hashtags }}                                 │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    POST-PIPELINE PROCESSING                         │
│  For each generated row:                                            │
│  1. Generate embedding via existing embedding_client                │
│     (same create_embedding_text → get_single_embedding flow)       │
│  2. Save to waywo_projects with source="nemo_data_designer"        │
│  3. Set is_valid_project=True, source_comment_id=NULL              │
│  4. project_urls=[], url_summaries={}                               │
└─────────────────────────────────────────────────────────────────────┘
```

**LLM call count per generated project: 3** (text generation + structured extraction + judge scoring). The sampler and expression columns are pure computation — no LLM calls.

---

## LLM Configuration — Local or Remote

DataDesigner connects to LLMs via `ModelProvider` + `ModelConfig`. We'll configure these using the **same env vars** the rest of waywo already uses, so switching between local and remote inference requires zero code changes:

```python
import os
import data_designer.config as dd

# These are the same env vars from docker-compose.yml x-common-env
# and from src/llm_config.py — single source of truth
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://192.168.6.19:8002/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4")
LLM_API_KEY = os.getenv("LLM_API_KEY", "not-needed")

provider = dd.ModelProvider(
    name="waywo-llm",
    endpoint=LLM_BASE_URL,
    provider_type="openai",
    api_key="LLM_API_KEY",  # NDD reads this env var at runtime
)
```

**Switching to remote inference** (e.g., NVIDIA API Catalog, OpenAI, OpenRouter): just change the env vars in `docker-compose.yml` or `.env`:

```yaml
# Local Nemotron
LLM_BASE_URL: http://192.168.6.19:8002/v1
LLM_MODEL_NAME: nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16
LLM_API_KEY: not-needed

# OR: NVIDIA API Catalog (remote)
LLM_BASE_URL: https://integrate.api.nvidia.com/v1
LLM_MODEL_NAME: nvidia/llama-3.3-nemotron-super-49b-v1
LLM_API_KEY: nvapi-xxx

# OR: OpenAI
LLM_BASE_URL: https://api.openai.com/v1
LLM_MODEL_NAME: gpt-4.1
LLM_API_KEY: sk-xxx
```

Both the existing LlamaIndex workflow (HN processing) and the new DataDesigner pipeline (idea generation) will use whichever LLM the env vars point to. No config duplication.

**Three model aliases with different temperatures** (all pointing to the same model/provider):

| Alias | Temperature | Purpose |
|-------|-------------|---------|
| `waywo-creative` | 0.85 (or user-configured `creativity` param) | Free-form idea generation |
| `waywo-structured` | 0.1 | Structured metadata extraction (JSON) |
| `waywo-judge` | 0.2 | Quality scoring |

---

## Database Changes

### Make `source_comment_id` nullable

Currently `NOT NULL` with FK to `waywo_comments.id`. Generated projects have no source comment. Change to nullable:

```python
source_comment_id: Mapped[Optional[int]] = mapped_column(
    Integer, ForeignKey("waywo_comments.id"), nullable=True
)
```

### Add `source` column (nullable)

```python
source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
```

- `"hn"` — projects extracted from Hacker News comments
- `"nemo_data_designer"` — projects generated by NeMo DataDesigner
- `NULL` — legacy projects (pre-migration); functionally equivalent to `"hn"`

No backfill needed — you'll regenerate everything anyway. New HN-processed projects will set `source="hn"`, new generated projects will set `source="nemo_data_designer"`.

Add an index: `Index("ix_waywo_projects_source", "source")`

### Migration

In `src/migrate.py`, add:
1. `ALTER TABLE waywo_projects ADD COLUMN source TEXT` (nullable, no default needed)
2. Recreate table to make `source_comment_id` nullable (SQLite limitation — requires copy-to-temp, drop, recreate, copy-back)
3. Add index on `source`

### What stays the same

All other `WaywoProjectDB` fields remain identical. Generated projects will populate:
- `title`, `short_description`, `description`, `hashtags` — from DataDesigner pipeline
- `idea_score`, `complexity_score` — from LLM judge
- `description_embedding` — from post-pipeline embedding
- `is_valid_project` = `True` (always, since they're generated)
- `project_urls` = `[]`, `url_summaries` = `{}` (no URLs to scrape)
- `screenshot_path` = `None` (no URL to screenshot)
- `source_comment_id` = `None`
- `is_bookmarked` = `False`

---

## Tag Seeding Strategy

### How tags drive generation

The user selects tags in the frontend UI. These become the seed for the DataDesigner pipeline:

**If user provides specific tags**: The `primary_tag` sampler picks uniformly from those tags. Every generated project will be rooted in one of the user's chosen tags.

**If user provides no tags**: The `primary_tag` sampler picks from the full tag vocabulary weighted by frequency (popular tags like "ai", "saas", "web-dev" are more likely). This produces a "surprise me" generation mode.

### Tag co-occurrence for realistic combinations

Real projects have 3-5 tags that make sense together ("ai" + "llm" + "python", not "ai" + "gardening" + "cooking"). We need a co-occurrence map.

**Build co-occurrence data** from existing projects:
```python
def build_tag_cooccurrence(projects: list[WaywoProjectDB]) -> dict[str, list[tuple[str, int]]]:
    """
    For each tag, find which other tags most commonly appear alongside it.
    Returns: {"ai": [("llm", 45), ("python", 38), ("nlp", 22), ...], ...}
    """
```

This feeds the `SUBCATEGORY` sampler: given primary_tag="ai", sample secondary tags from ["llm", "python", "nlp", "computer-vision"] with co-occurrence-based weights.

**When to compute**: At pipeline build time (start of Celery task), querying the DB for current tag data. Not expensive — just counts over the project table.

---

## Embedding Integration

Generated projects get embeddings the **exact same way** HN projects do:

```python
# Same function used in WaywoProjectWorkflow.generate_embedding step
embedding_text = create_embedding_text(
    title=row["title"],
    description=row["description"],
    hashtags=row["hashtags"],
)
embedding = await get_single_embedding(
    text=embedding_text,
    embedding_url=EMBEDDING_URL,  # same env var
)
blob = embedding_to_blob(embedding)
# Save to description_embedding column
```

This means generated projects will:
- Appear in semantic search results alongside HN projects
- Show up in "similar projects" for HN projects (and vice versa)
- Be searchable via the RAG chatbot

The embedding service is called **after** the DataDesigner pipeline completes, not during it. DataDesigner doesn't know about embeddings — we handle that in the save loop. This avoids needing to configure a second provider for our custom `/embed` endpoint.

---

## End-to-End Flow

### 1. User opens "Generate Ideas" dialog in frontend

The dialog (on the `/projects` page) shows:
- **Tag selector**: Multi-select chips populated from `GET /api/waywo-projects/hashtags`. User picks tags they're interested in (or leaves empty for random).
- **Number of ideas**: Input/slider, 1-50, default 5
- **Creativity**: Slider, maps to LLM temperature (0.3 = conservative, 0.85 = balanced, 1.2 = wild)

### 2. Frontend calls `POST /api/generate-ideas`

```json
{
  "num_ideas": 10,
  "seed_tags": ["ai", "python", "developer-tools"],
  "creativity": 0.85
}
```

### 3. Backend enqueues Celery task

The endpoint validates the request, creates a Celery task, and returns the task ID immediately:

```json
{
  "task_id": "abc123-...",
  "num_requested": 10,
  "seed_tags": ["ai", "python", "developer-tools"]
}
```

### 4. Celery worker runs DataDesigner pipeline

```python
@celery_app.task(bind=True)
def generate_ideas(self, num_ideas: int, seed_tags: list[str], creativity: float):
    nest_asyncio.apply()

    # 1. Build tag data (co-occurrence map from DB)
    tag_cooccurrence = build_tag_cooccurrence(get_all_projects())

    # 2. Configure DataDesigner with env-var-driven LLM provider
    provider, models = build_ndd_provider_and_models(creativity=creativity)
    data_designer = DataDesigner(model_providers=[provider])
    config = build_pipeline_config(
        models=models,
        seed_tags=seed_tags,
        tag_cooccurrence=tag_cooccurrence,
    )

    # 3. Generate
    results = data_designer.create(config, num_records=num_ideas, dataset_name="waywo-ideas")
    df = results.load_dataset()

    # 4. Post-process: embeddings + save
    loop = asyncio.get_event_loop()
    for _, row in df.iterrows():
        embedding = loop.run_until_complete(generate_embedding_for_row(row))
        save_generated_project(row, embedding, source="nemo_data_designer")
```

### 5. Frontend polls for completion, then refreshes project list

The frontend polls `GET /api/generate-ideas/{task_id}/status` until complete, then reloads the project list (optionally filtered to `source=nemo_data_designer` to show just the new projects).

### 6. Generated projects appear in project list

They look like regular projects but with:
- A small "NDD" or "AI Generated" badge
- No "Original Comment" section on the detail page
- No screenshot (nothing to screenshot)
- `source_comment_id` is null → "Source" section hidden

---

## API Changes

### New endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/generate-ideas` | POST | Start idea generation (returns task ID) |
| `/api/generate-ideas/{task_id}/status` | GET | Poll task status |

### Updated endpoints

| Endpoint | Change |
|----------|--------|
| `GET /api/waywo-projects` | Add optional `source` query param (`hn`, `nemo_data_designer`, or omit for all) |
| `GET /api/waywo-projects/{id}` | Response now includes `source` field |

### Request/response models

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

---

## Frontend Changes

### Projects index page (`/projects`)

- **Source filter**: Tab bar or segmented control — "All" | "From HN" | "AI Generated"
- **"Generate Ideas" button**: Opens dialog/drawer with tag selector + options
- **Badge on project cards**: Small chip showing "AI" for `source === "nemo_data_designer"`

### Generate Ideas dialog

- Tag multi-select (from existing hashtags endpoint)
- Num ideas input
- Creativity slider
- Generate button → loading state → completion toast → refresh list

### Project detail page (`/projects/[id]`)

- Show "AI Generated" badge when `source === "nemo_data_designer"`
- Conditionally hide "Original Comment" section when `source_comment_id` is null
- Everything else (scores, tags, description, similar projects, bookmark) works identically

---

## Pydantic Model Changes

### `WaywoProject` + `WaywoProjectSummary`

Add:
```python
source: Optional[str] = None  # "hn", "nemo_data_designer", or None (legacy)
```

### `WaywoProjectListFilters`

Add:
```python
source: Optional[str] = None  # filter by source
```

---

## File Changes Summary

| File | Change |
|------|--------|
| `pyproject.toml` | Add `data-designer>=0.4.0` |
| `src/ndd_config.py` | **NEW** — Provider/model config using existing env vars |
| `src/ndd_pipeline.py` | **NEW** — Pipeline definition (columns, seed data builder, co-occurrence) |
| `src/db_models.py` | Add `source` (nullable); make `source_comment_id` nullable |
| `src/models.py` | Add `source` to project models; add `GenerateIdeasRequest`/`Response` |
| `src/db_client.py` | Update queries for `source` filter; update `save_project` |
| `src/main.py` | Add generate-ideas endpoints; update project list with source filter |
| `src/tasks.py` | Add `generate_ideas` Celery task |
| `src/migrate.py` | Migration for new column + nullable change |
| `frontend/app/pages/projects/index.vue` | Source filter tabs, Generate Ideas button + dialog |
| `frontend/app/pages/projects/[id].vue` | AI badge, conditional comment section |
| `docker-compose.yml` | No changes needed (env vars already flow to celery worker) |

---

## Implementation Order

1. Add `data-designer` dependency, verify it installs cleanly alongside existing deps
2. DB changes: add `source` column, make `source_comment_id` nullable, migration
3. Pydantic model updates (source field)
4. `ndd_config.py` — provider + model config reading from env vars
5. `ndd_pipeline.py` — tag co-occurrence builder + pipeline definition
6. Celery task (`generate_ideas`) with post-pipeline embedding + DB save
7. API endpoints (generate-ideas + source filter on project list)
8. Frontend: source filter, generate dialog, AI badges
9. Update HN workflow to set `source="hn"` on newly processed projects

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| `data-designer` dependency conflicts with existing packages | Test install in isolated venv first; pin version |
| Nemotron model struggles with creative generation or structured output | DataDesigner has built-in retry/correction loops for structured output; use LLM Judge to filter low-quality ideas; temperature tunable via UI |
| Generation runs compete with HN processing for LLM resources | Celery concurrency is already 1; tasks are sequential; generation runs are user-initiated so timing is controllable |
| DataDesigner async/event-loop conflicts with Celery | Same `nest_asyncio` pattern already used successfully for WaywoProjectWorkflow |
| Co-occurrence map is empty if no projects exist yet | Fallback: skip subcategory sampling, use only user-provided tags |

---

## Open Questions

1. **Generated project validity** — Recommend setting `is_valid_project = True` for all generated projects since they're not spam. The LLM Judge scores serve as the quality signal instead.

2. **"Similar to project X" mode** — Future enhancement: select an existing project and generate variations. Would use DataDesigner's seed dataset feature with the project's description as seed. Good v2 feature.

3. **Tag vocabulary control** — The structured extraction prompt should instruct the LLM to prefer existing tags but allow new ones if the idea genuinely introduces a new domain. The UI tag filter will auto-discover new tags.
