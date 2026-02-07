# NeMo DataDesigner Integration Plan

## Overview

This plan describes how to integrate [NVIDIA NeMo DataDesigner](https://github.com/NVIDIA-NeMo/DataDesigner) into the waywo project to **generate synthetic project ideas** seeded by the existing tag taxonomy extracted from real Hacker News "What are you working on?" projects.

### What is NeMo DataDesigner?

NeMo DataDesigner is an open-source Python library (Apache 2.0) for creating high-quality synthetic datasets. It orchestrates LLM calls to produce structured, diverse data from scratch or by augmenting seed data. Key features:

- **Column-based pipeline**: Define a schema of columns (sampler, LLM text, LLM structured, expression, embedding, etc.) and DataDesigner generates rows following that schema
- **Seed datasets**: Provide real data (CSV, DataFrame, HuggingFace) to ground generation in reality
- **LiteLLM backend**: Connects to any OpenAI-compatible API (including local vLLM/TGI endpoints) via LiteLLM
- **Sampler columns**: Statistical sampling (category, subcategory, distributions) without LLM calls for fast structural data
- **LLM Judge**: Built-in quality scoring via LLM-as-Judge columns
- **Embedding columns**: Generate vector embeddings as part of the pipeline
- **Preview mode**: Test configs on small samples before committing to full generation
- **Fluent Python API**: `DataDesignerConfigBuilder` with chaining, plus YAML/JSON config serialization

**Package**: `pip install data-designer` (requires Python >=3.10, waywo uses 3.12)

---

## Goal

Create a new feature that lets users **generate novel project ideas** using NeMo DataDesigner, seeded by the existing tag corpus. Generated projects appear in the same project list alongside HN-sourced projects but are clearly marked as AI-generated. Users can:

1. Select tags (or let the system pick trending/random tags) to seed idea generation
2. Configure how many ideas to generate and creativity parameters
3. View generated projects with the same metadata structure as HN projects (title, description, hashtags, scores, embeddings)
4. Filter the project list by source (HN vs. AI-generated)

---

## Architecture

### How It Fits Into the Existing System

```
                          ┌────────────────────┐
                          │   Frontend (Nuxt)   │
                          │  "Generate Ideas"   │
                          └────────┬───────────┘
                                   │ POST /api/generate-ideas
                                   ▼
                          ┌────────────────────┐
                          │   FastAPI Backend   │
                          │  new endpoint       │
                          └────────┬───────────┘
                                   │ celery.delay()
                                   ▼
                          ┌────────────────────┐
                          │   Celery Worker     │
                          │  generate_ideas     │
                          └────────┬───────────┘
                                   │
                                   ▼
                ┌──────────────────────────────────────┐
                │        NeMo DataDesigner Pipeline     │
                │                                      │
                │  1. Sampler: pick tags (seed data)   │
                │  2. Sampler: persona/domain context   │
                │  3. LLM Text: generate project idea  │
                │  4. LLM Structured: extract metadata │
                │  5. LLM Judge: score idea quality    │
                │  6. Embedding: generate vector       │
                └──────────────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌──────────┐  ┌──────────┐  ┌──────────────┐
             │ Local LLM│  │Embedding │  │   SQLite DB   │
             │ Nemotron │  │ Service  │  │ (save projects)│
             └──────────┘  └──────────┘  └──────────────┘
```

### Service Reuse

| Service | Current Use | NDD Use |
|---------|------------|---------|
| **Nemotron LLM** (`http://192.168.6.19:8002/v1`) | Project extraction, validation, metadata, scoring | Text generation, structured output, judging |
| **Embedding Service** (`http://192.168.5.96:8000`) | Project embeddings for semantic search | Embedding generated projects (via NDD EmbeddingColumn or post-pipeline) |
| **SQLite** | Store HN projects | Store generated projects (same table, new `source` field) |
| **Celery/Redis** | Background task processing | Background idea generation tasks |

---

## Detailed Implementation Plan

### Phase 1: Add Dependency and Local LLM Provider Config

**1.1 Add `data-designer` to `pyproject.toml`**

Add to `dependencies`:
```
"data-designer>=0.4.0",
```

This pulls in `litellm`, `duckdb`, `faker`, `httpx`, `networkx`, `tiktoken`, and other deps. Most of these are lightweight and don't conflict with existing deps (httpx, pydantic, numpy already present).

**Potential conflicts to check**:
- `pydantic` — NDD uses Pydantic v2, waywo already uses `pydantic>=2.0.0` — OK
- `httpx` — NDD uses httpx, waywo already has `httpx>=0.24.0` — OK
- `numpy` — Both need numpy — OK
- `litellm` — New dep, no conflicts expected (it's a thin wrapper)

**1.2 Create `src/ndd_config.py` — DataDesigner provider/model configuration**

This module will configure NeMo DataDesigner to use our local Nemotron LLM and embedding service. Key config:

```python
import data_designer.config as dd
from data_designer.interface import DataDesigner

# Reuse the same env vars from llm_config.py
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://192.168.6.19:8002/v1")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4")
EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://192.168.5.96:8000")

# DataDesigner model provider pointing to local Nemotron
local_provider = dd.ModelProvider(
    name="local-nemotron",
    endpoint=LLM_BASE_URL,
    provider_type="openai",      # OpenAI-compatible API
    api_key="LOCAL_LLM_API_KEY", # env var name; can be "not-needed"
)

# Model configs
text_model = dd.ModelConfig(
    alias="local-text",
    model=LLM_MODEL_NAME,
    provider="local-nemotron",
    inference_parameters=dd.ChatCompletionInferenceParams(
        temperature=0.85,   # higher for creative idea generation
        max_tokens=2048,
    ),
)

structured_model = dd.ModelConfig(
    alias="local-structured",
    model=LLM_MODEL_NAME,
    provider="local-nemotron",
    inference_parameters=dd.ChatCompletionInferenceParams(
        temperature=0.1,    # lower for structured/deterministic output
        max_tokens=2048,
    ),
)

judge_model = dd.ModelConfig(
    alias="local-judge",
    model=LLM_MODEL_NAME,
    provider="local-nemotron",
    inference_parameters=dd.ChatCompletionInferenceParams(
        temperature=0.2,
        max_tokens=512,
    ),
)
```

**Note on embeddings**: NeMo DataDesigner's `EmbeddingColumnConfig` uses LiteLLM's embedding API, which expects an OpenAI-compatible `/v1/embeddings` endpoint. Our embedding service uses a custom `/embed` endpoint. Two options:

- **Option A**: Use a `CustomColumnConfig` that calls our existing `embedding_client.get_single_embedding()` — reuses our battle-tested client
- **Option B**: If the embedding service also exposes `/v1/embeddings`, configure an NDD embedding model provider

We should go with **Option A** (custom column calling our existing client) since it's guaranteed compatible and avoids a second embedding provider config.

---

### Phase 2: Database Schema Changes

**2.1 Add `source` column to `WaywoProjectDB`**

Add a new column to distinguish HN-sourced projects from AI-generated ones:

```python
# In WaywoProjectDB
source: Mapped[str] = mapped_column(
    String(50), default="hackernews", nullable=False
)
```

Values: `"hackernews"` (default for all existing projects) or `"ndd_generated"`.

This column also needs:
- An index for filtering: `Index("ix_waywo_projects_source", "source")`
- A migration script to set `source = "hackernews"` on all existing rows

**2.2 Make `source_comment_id` nullable**

Currently `source_comment_id` is `nullable=False` with a FK to `waywo_comments.id`. Generated projects have no source comment. Options:

- **Option A (recommended)**: Make `source_comment_id` nullable. Generated projects will have `source_comment_id = NULL`.
- **Option B**: Create a synthetic "comment" entry. Adds unnecessary complexity.

Go with Option A. This requires a migration and updating the FK constraint.

**2.3 Add generation metadata fields**

```python
# Optional fields for NDD-generated projects
generation_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON: seed tags, params
generation_batch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # group generated projects
```

`generation_config` stores the seed tags and parameters used, so users can see why a project was generated. `generation_batch_id` groups projects from the same generation run for easy batch management (e.g., "delete all projects from run X").

**2.4 Migration approach**

Add a new migration in `src/migrate.py`:
1. `ALTER TABLE waywo_projects ADD COLUMN source TEXT DEFAULT 'hackernews' NOT NULL`
2. `ALTER TABLE waywo_projects ADD COLUMN generation_config TEXT`
3. `ALTER TABLE waywo_projects ADD COLUMN generation_batch_id TEXT`
4. Make `source_comment_id` nullable (SQLite requires table recreation for this)
5. Add index on `source`

---

### Phase 3: Seed Data — Tag Extraction and Preparation

**3.1 Extract tag corpus from existing projects**

The existing `/api/waywo-projects/hashtags` endpoint returns all unique tags. We'll build a seed dataset from this:

```python
def build_tag_seed_data() -> pd.DataFrame:
    """
    Extract tags from existing projects with frequency counts.
    Returns DataFrame with columns: tag, count, sample_titles
    """
    # Query all valid projects' hashtags
    # Count frequency of each tag
    # For each tag, collect 3-5 sample project titles that use it
    # Return as DataFrame
```

The seed DataFrame will look like:

| tag | count | sample_titles |
|-----|-------|---------------|
| ai | 142 | "AI-Powered Code Review", "LLM Chat App", ... |
| saas | 87 | "Invoice SaaS Platform", ... |
| python | 76 | "Python Web Scraper", ... |
| web-dev | 65 | ... |

**3.2 Build tag combination sampler**

Instead of generating ideas for single tags, we want realistic multi-tag combinations (like real projects have 3-5 tags). DataDesigner's `SamplerType.CATEGORY` with weighted probabilities based on tag frequency handles this naturally, combined with subcategory sampling for complementary tags.

Alternatively, we can pre-compute common tag co-occurrence pairs from existing projects and use those as seed rows.

**3.3 Seed data strategy**

Two approaches, both valid:

- **Approach A — Tag-seeded generation**: Use sampler columns to pick tags, then LLM generates project ideas matching those tags. Tags drive the generation.
- **Approach B — Existing project-seeded generation**: Use existing project summaries (title + description + tags) as seed data, and have the LLM generate "similar but novel" project ideas. More grounded but less diverse.

**Recommendation**: Start with **Approach A** (tag-seeded) for maximum novelty, with the option to add Approach B later. The tag frequency data ensures generated ideas reflect the actual distribution of what people build.

---

### Phase 4: DataDesigner Pipeline Definition

**4.1 Pipeline column schema**

```python
config_builder = dd.DataDesignerConfigBuilder(
    model_configs=[text_model, structured_model, judge_model]
)

# --- Column 1: Primary tag (sampler) ---
config_builder.add_column(
    dd.SamplerColumnConfig(
        name="primary_tag",
        sampler_type=dd.SamplerType.CATEGORY,
        params={
            "values": ["ai", "saas", "python", "web-dev", ...],  # from seed data
            "weights": [142, 87, 76, 65, ...],                    # frequency weights
        },
    )
)

# --- Column 2: Secondary tags (sampler, conditioned on primary) ---
config_builder.add_column(
    dd.SamplerColumnConfig(
        name="secondary_tags",
        sampler_type=dd.SamplerType.SUBCATEGORY,
        params={
            "parent_column": "primary_tag",
            "mapping": {
                "ai": {"values": ["llm", "machine-learning", "nlp", "computer-vision"], "weights": [4,3,2,1]},
                "saas": {"values": ["billing", "api", "dashboard", "analytics"], "weights": [3,3,2,2]},
                # ... built from tag co-occurrence analysis
            },
        },
    )
)

# --- Column 3: Target audience / persona context (sampler) ---
config_builder.add_column(
    dd.SamplerColumnConfig(
        name="target_audience",
        sampler_type=dd.SamplerType.CATEGORY,
        params={
            "values": [
                "indie hackers", "enterprise teams", "developers",
                "small businesses", "students", "researchers",
                "content creators", "data scientists"
            ],
            "weights": [3, 2, 4, 2, 1, 1, 1, 1],
        },
    )
)

# --- Column 4: Complexity target (sampler) ---
config_builder.add_column(
    dd.SamplerColumnConfig(
        name="target_complexity",
        sampler_type=dd.SamplerType.UNIFORM,
        params={"low": 1, "high": 10},
        convert_to="int",
    )
)

# --- Column 5: Project idea generation (LLM text) ---
config_builder.add_column(
    dd.LLMTextColumnConfig(
        name="project_idea",
        prompt="""You are a creative tech entrepreneur brainstorming project ideas.

Generate a novel, specific, and actionable project idea that:
- Focuses on the domain: {{ primary_tag }}
- Incorporates elements of: {{ secondary_tags }}
- Targets: {{ target_audience }}
- Has approximately {{ target_complexity }}/10 complexity

The idea should be something a solo developer or small team could realistically build.
Write 2-3 paragraphs describing the project concept, what it does, why it's useful,
and what makes it interesting. Be specific about features and technical approach.

Do NOT describe a project that already exists as a well-known product.
Be creative and original.""",
        model_alias="local-text",
    )
)

# --- Column 6: Structured metadata extraction (LLM structured) ---
config_builder.add_column(
    dd.LLMStructuredColumnConfig(
        name="metadata",
        prompt="""Extract structured metadata from this project idea.

Project idea: {{ project_idea }}
Primary domain: {{ primary_tag }}
Related tags: {{ secondary_tags }}

Return a JSON object with:
- "title": A catchy, concise project name (2-5 words)
- "short_description": A one-line summary (5-10 words)
- "description": A 1-2 sentence description
- "hashtags": An array of 3-5 lowercase hashtag strings (include {{ primary_tag }})""",
        output_format={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "short_description": {"type": "string"},
                "description": {"type": "string"},
                "hashtags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "short_description", "description", "hashtags"],
        },
        model_alias="local-structured",
    )
)

# --- Column 7: Idea quality score (LLM judge) ---
config_builder.add_column(
    dd.LLMJudgeColumnConfig(
        name="idea_quality",
        prompt="""Evaluate this project idea for quality and potential.

Title: {{ metadata.title }}
Description: {{ metadata.description }}
Full idea: {{ project_idea }}""",
        scores=[
            dd.Score(
                name="idea_score",
                description="How novel, useful, and feasible is this idea?",
                options={
                    "1": "Trivial/unoriginal — a to-do app clone",
                    "3": "Somewhat interesting but common",
                    "5": "Solid idea with clear value",
                    "7": "Very creative with strong potential",
                    "9": "Exceptional — novel, high-impact, and feasible",
                },
            ),
            dd.Score(
                name="complexity_score",
                description="How complex would this be to build?",
                options={
                    "1": "Weekend project, very simple",
                    "3": "A few weeks of work",
                    "5": "A month or two for one developer",
                    "7": "Several months, needs multiple skills",
                    "9": "Major undertaking, team required",
                },
            ),
        ],
        model_alias="local-judge",
    )
)

# --- Column 8: Expression columns to extract final fields ---
config_builder.add_column(
    dd.ExpressionColumnConfig(
        name="title",
        expr="{{ metadata.title }}",
    )
)
config_builder.add_column(
    dd.ExpressionColumnConfig(
        name="short_description",
        expr="{{ metadata.short_description }}",
    )
)
config_builder.add_column(
    dd.ExpressionColumnConfig(
        name="description",
        expr="{{ metadata.description }}",
    )
)
config_builder.add_column(
    dd.ExpressionColumnConfig(
        name="hashtags",
        expr="{{ metadata.hashtags }}",
    )
)
```

**4.2 Embedding generation (post-pipeline)**

Since our embedding service uses a custom API (not OpenAI-compatible `/v1/embeddings`), we'll generate embeddings **after** the DataDesigner pipeline completes, using our existing `embedding_client`:

```python
# After DataDesigner produces DataFrame:
df = results.load_dataset()

for _, row in df.iterrows():
    embedding_text = create_embedding_text(
        title=row["title"],
        description=row["description"],
        hashtags=row["hashtags"],
    )
    embedding = await get_single_embedding(text=embedding_text)
    # Save to DB with embedding
```

This keeps the pipeline simple and reuses our existing, tested embedding code path.

**4.3 Alternative: Use NDD CustomColumnConfig for embeddings**

If we want embeddings inside the pipeline (for preview/analysis), we can use a custom column:

```python
@dd.custom_column_generator()
async def generate_waywo_embedding(row, generator_params):
    from src.embedding_client import get_single_embedding, create_embedding_text
    text = create_embedding_text(row["title"], row["description"], row["hashtags"])
    return await get_single_embedding(text=text)

config_builder.add_column(
    dd.CustomColumnConfig(
        name="embedding",
        generator_function=generate_waywo_embedding,
        generation_strategy="cell_by_cell",
    )
)
```

**Recommendation**: Start with post-pipeline embedding (simpler), consider moving to CustomColumn later if needed.

---

### Phase 5: API Endpoints

**5.1 `POST /api/generate-ideas`**

Request body:
```python
class GenerateIdeasRequest(BaseModel):
    num_ideas: int = Field(default=5, ge=1, le=50)
    seed_tags: Optional[list[str]] = None    # specific tags to seed with; None = auto-select
    min_idea_score: Optional[int] = Field(default=None, ge=1, le=10)  # filter threshold
    creativity: float = Field(default=0.85, ge=0.1, le=1.5)  # maps to LLM temperature
```

Response:
```python
class GenerateIdeasResponse(BaseModel):
    task_id: str          # Celery task ID for polling
    batch_id: str         # generation_batch_id for grouping
    num_requested: int
    seed_tags: list[str]  # the tags that will be used
```

**5.2 `GET /api/generate-ideas/{task_id}/status`**

Returns task status (PENDING, STARTED, SUCCESS, FAILURE) and progress info.

**5.3 `DELETE /api/generated-projects/batch/{batch_id}`**

Delete all projects from a specific generation batch.

**5.4 Update existing `GET /api/waywo-projects`**

Add `source` filter parameter:
- `source=hackernews` — only HN projects
- `source=ndd_generated` — only AI-generated projects
- `source=all` (default) — both

---

### Phase 6: Celery Task

**6.1 `generate_ideas` task**

```python
@celery_app.task(bind=True)
def generate_ideas(self, num_ideas, seed_tags, creativity, batch_id):
    """
    Generate synthetic project ideas using NeMo DataDesigner.
    """
    # 1. Build tag seed data (from DB or provided tags)
    # 2. Configure DataDesigner pipeline
    # 3. Run pipeline: data_designer.create(config, num_records=num_ideas)
    # 4. Post-process: generate embeddings via embedding service
    # 5. Save each generated project to DB with source="ndd_generated"
    # 6. Return summary of generated projects
```

**6.2 Async considerations**

NeMo DataDesigner uses async internally. Like the existing workflow tasks, we'll use `nest_asyncio.apply()` to run async code within the sync Celery task. DataDesigner's `create()` method handles its own async event loop, but we need to ensure compatibility with Celery's execution model.

---

### Phase 7: Pydantic Model Updates

**7.1 Update `WaywoProject`**

Add fields:
```python
source: str = "hackernews"                           # "hackernews" or "ndd_generated"
generation_config: Optional[dict] = None             # seed tags, params used
generation_batch_id: Optional[str] = None            # batch grouping
```

**7.2 Update `WaywoProjectSummary`**

Add:
```python
source: str = "hackernews"
```

**7.3 Update `WaywoProjectListFilters`**

Add:
```python
source: Optional[str] = None  # "hackernews", "ndd_generated", or None for all
```

---

### Phase 8: Frontend Changes

**8.1 Projects index page (`/projects`)**

- Add a **source filter** tab/toggle: "All" | "From HN" | "AI Generated"
- Add a **"Generate Ideas" button** that opens a dialog/drawer
- Show a badge on project cards indicating source (small "AI" chip for generated projects)

**8.2 Generate Ideas dialog**

- Tag selector: multi-select from existing tags (pre-populated from `/api/waywo-projects/hashtags`)
- Number of ideas: slider (1-50, default 5)
- Creativity: slider (0.1-1.5, default 0.85) with labels ("Conservative" to "Wild")
- "Generate" button → calls `POST /api/generate-ideas` → shows progress/polling
- On completion: refresh project list with `source=ndd_generated` filter active

**8.3 Project detail page (`/projects/[id]`)**

- Show "AI Generated" badge for `source === "ndd_generated"`
- Show "Seed Tags" section if `generation_config` is present
- Hide "Original Comment" section (since there's no source comment)
- Show "Generation Batch" info with link to see other projects from same batch
- "Delete Batch" button to remove all projects from the generation run

---

### Phase 9: Tag Co-occurrence Analysis

To make the subcategory sampling realistic, we need to analyze which tags commonly appear together in existing projects.

**9.1 Build co-occurrence matrix**

```python
def build_tag_cooccurrence() -> dict[str, dict[str, int]]:
    """
    Analyze existing projects to find which tags commonly appear together.
    Returns: {primary_tag: {co_tag: count, ...}, ...}
    """
    # For each project, for each pair of tags, increment co-occurrence count
    # Filter to top-N co-occurring tags per primary tag
```

This data feeds into the `SUBCATEGORY` sampler's `mapping` parameter, ensuring generated ideas have realistic tag combinations (e.g., "ai" commonly pairs with "llm", "python", "nlp" — not with "gardening").

**9.2 Cache/refresh strategy**

Store the co-occurrence data as a JSON file or in a DB table. Refresh when new HN projects are processed. The generation pipeline reads this at startup.

---

## File Changes Summary

| File | Change |
|------|--------|
| `pyproject.toml` | Add `data-designer>=0.4.0` dependency |
| `src/ndd_config.py` | **NEW** — DataDesigner provider/model config, pipeline builder |
| `src/ndd_pipeline.py` | **NEW** — Pipeline definition (columns, seed data, generation logic) |
| `src/db_models.py` | Add `source`, `generation_config`, `generation_batch_id` columns; make `source_comment_id` nullable |
| `src/models.py` | Add `source`, `generation_config`, `generation_batch_id` to Pydantic models; add `GenerateIdeasRequest`/`Response` |
| `src/db_client.py` | Update `save_project` and query methods for new fields; add `delete_batch` |
| `src/main.py` | Add `/api/generate-ideas` endpoints; update project list filtering |
| `src/tasks.py` | Add `generate_ideas` Celery task |
| `src/migrate.py` | Add migration for new columns |
| `frontend/app/pages/projects/index.vue` | Source filter, Generate Ideas button/dialog |
| `frontend/app/pages/projects/[id].vue` | AI-generated badge, generation metadata display |

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| `data-designer` dependency conflicts | Test install in isolated venv first; pin version |
| LiteLLM conflicts with existing `openai` package | LiteLLM wraps openai; test compatibility |
| Nemotron model quality for creative generation | Use higher temperature (0.85); add quality filtering via LLM Judge; allow regeneration |
| Embedding service compatibility | Use post-pipeline embedding with existing client (not NDD's EmbeddingColumn) |
| Large generation runs blocking LLM for HN processing | Use separate Celery queue or rate limiting; limit max batch size to 50 |
| DataDesigner async compatibility with Celery | Follow same `nest_asyncio` pattern as existing workflow tasks |

---

## Implementation Order

1. **Phase 1** — Add dependency, create `ndd_config.py` with local LLM provider setup
2. **Phase 2** — Database schema changes + migration
3. **Phase 7** — Pydantic model updates (needed before API/task work)
4. **Phase 3** — Tag seed data extraction utilities
5. **Phase 9** — Tag co-occurrence analysis
6. **Phase 4** — DataDesigner pipeline definition
7. **Phase 6** — Celery task for generation
8. **Phase 5** — API endpoints
9. **Phase 8** — Frontend changes

---

## Testing Strategy

- **Unit tests**: Pipeline config validation, tag extraction, co-occurrence analysis
- **Integration test**: Run DataDesigner preview (2-3 records) against local LLM, verify output schema
- **DB tests**: Migration correctness, nullable `source_comment_id`, filtering by source
- **API tests**: Generate ideas endpoint, status polling, batch deletion
- **E2E test**: Frontend → API → Celery → DataDesigner → DB → Frontend display

---

## Open Questions

1. **Should generated projects be valid by default?** Currently, HN projects go through a validation step. Generated projects are inherently "valid" (they're not spam/deleted comments). Recommend setting `is_valid_project = True` for all generated projects.

2. **Should we support "similar to project X" generation?** Approach B from Phase 3 — seed with existing project descriptions to generate variations. Could be a v2 feature.

3. **Tag vocabulary control**: Should we limit generated hashtags to the existing vocabulary, or allow the LLM to create new tags? Recommend constraining to existing tags for consistency, with an option to allow new ones.

4. **Generation quotas**: Should there be limits on how many ideas a user can generate? Relevant if LLM resources are shared.
