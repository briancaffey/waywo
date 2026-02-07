# Waywo Plan

## Tech Stack Overview

- [x] Docker and docker compose
- [x] FastAPI
- [x] Celery worker and celery beat scheduler
- [x] Nuxt.js frontend (Nuxt 4 + shadcn/ui)
- [x] Hacker News Firebase API
- [x] SQLite with SQLAlchemy (migrated from Redis)
- [x] Pytest for testing suite
- [x] Makefile with make commands
- [x] Firecrawl for LLM-powered web scraping
- [x] LlamaIndex workflows for project extraction
- [x] sqlite-vector for semantic search
- [x] RAG chatbot with LlamaIndex
- [x] Jupyter Lab for interactive development

---

## Completed Work

### Data Structures
- [x] `WaywoPost` - A monthly "What are you working on?" HN post
- [x] `WaywoComment` - A top-level reply on a WaywoPost
- [x] `WaywoProject` - Extracted project data from a comment

### Storage (Migrated to SQLite)
- [x] SQLite database at `/app/data/waywo.db`
- [x] SQLAlchemy ORM models: `WaywoPostDB`, `WaywoCommentDB`, `WaywoProjectDB`
- [x] Redis retained for Celery broker only

### Celery Tasks
- [x] `process_waywo_posts` - loops over posts from waywo.yml
- [x] `process_waywo_post` - fetches and stores top-level comments
- [x] `process_waywo_comment` - processes single comment through LlamaIndex workflow
- [x] `process_waywo_comments` - batch processes unprocessed comments

### API Endpoints
- [x] `POST /api/process-waywo-posts` - trigger post processing
- [x] `GET /api/waywo-posts` - list posts with comment counts
- [x] `GET /api/waywo-posts/{post_id}` - single post with comments
- [x] `GET /api/waywo-posts/chart-data` - chart data for visualization
- [x] `GET /api/waywo-comments` - paginated comment list (with post_id filter)
- [x] `GET /api/waywo-comments/{comment_id}` - single comment with projects
- [x] `POST /api/waywo-comments/{comment_id}/process` - process single comment
- [x] `POST /api/process-waywo-comments` - batch process comments
- [x] `GET /api/waywo-projects` - paginated project list with filters
- [x] `GET /api/waywo-projects/{project_id}` - single project with source comment
- [x] `DELETE /api/waywo-projects/{project_id}` - delete a project
- [x] `GET /api/waywo-projects/hashtags` - list all unique hashtags
- [x] `GET /api/embedding/health` - embedding service health check
- [x] `GET /api/semantic-search/stats` - semantic search statistics
- [x] `POST /api/semantic-search` - semantic search over projects
- [x] `POST /api/waywo-chatbot` - RAG chatbot query
- [x] `GET /api/admin/stats` - database statistics
- [x] `DELETE /api/admin/reset-sqlite` - reset SQLite database
- [x] `DELETE /api/admin/reset-redis` - flush Redis
- [x] `DELETE /api/admin/reset-all` - reset both databases

### Frontend Pages
- [x] Home page (`/`) - landing page with overview
- [x] Posts page (`/posts`) - view posts, trigger processing, chart visualization
- [x] Comments page (`/comments`) - paginated comment browser with post filter
- [x] Comment detail page (`/comments/[id]`) - view comment, process button, extracted projects
- [x] Projects page (`/projects`) - paginated project browser with comment filter
- [x] Project detail page (`/projects/[id]`) - full project view with collapsible sections
- [x] Debug page (`/debug`) - debugging tools
- [x] Search page (`/search`) - semantic search with similarity scores
- [x] Chat page (`/chat`) - RAG chatbot for project Q&A
- [x] Admin page (`/admin`) - database reset and management tools

---

# WaywoProject Pipeline - Implementation Plan

## Milestone 1: SQLite Migration Foundation ✅ COMPLETE

**Goal**: Replace Redis data storage with SQLite while keeping Redis for Celery only.

### Files Created/Modified:
| File | Action |
|------|--------|
| `pyproject.toml` | Added `sqlalchemy`, `aiosqlite`, `llama-index-core`, `llama-index-llms-openai-like` |
| `src/database.py` | **New** - SQLAlchemy engine, session factory, Base class |
| `src/db_models.py` | **New** - `WaywoPostDB`, `WaywoCommentDB`, `WaywoProjectDB` models |
| `src/db_client.py` | **New** - All CRUD operations for posts, comments, projects |
| `src/models.py` | Added `WaywoProject`, `WaywoProjectSummary`, filter models |
| `src/migrate_redis_to_sqlite.py` | **New** - Migration script |
| `src/tasks.py` | Updated imports to use `db_client` |
| `src/main.py` | Updated imports, added `init_db()` on startup |
| `docker-compose.yml` | Added `DATA_DIR` env var and `./data:/app/data` volume |

---

## Milestone 2: LlamaIndex Workflow Setup ✅ COMPLETE

**Goal**: Create the processing workflow infrastructure.

### Tasks:
- [x] Create LLM client configuration (`src/llm_config.py`)
- [x] Define workflow events (`src/workflows/events.py`)
- [x] Create main workflow class (`src/workflows/waywo_project_workflow.py`)

### LLM Configuration:
- Endpoint: `http://192.168.6.19:8002/v1`
- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4`
- Uses OpenAI-compatible API

---

## Milestone 3: Firecrawl Integration ✅ COMPLETE

**Goal**: Reliable URL content fetching.

### Tasks:
- [x] Create Firecrawl client (`src/firecrawl_client.py`)
- [x] Add retry logic with exponential backoff
- [x] Add URL validation (skip social media, invalid URLs)
- [x] Logging with emojis (📥 fetch start, ✅ success, ⚠️ failure)
- [x] Update workflow to use Firecrawl client
- [x] Configure docker-compose with FIRECRAWL_URL and extra_hosts

### Firecrawl API:
- Endpoint: `http://localhost:3002/v1/scrape`
- No authentication required
- Request format:
  ```json
  {
    "url": "https://example.com",
    "formats": ["markdown"],
    "onlyMainContent": true
  }
  ```

---

## Milestone 4: Workflow Steps Implementation ✅ COMPLETE

**Goal**: Implement each processing step.

### Workflow Order:
1. **Extract Projects** (`extract_projects`)
   - Input: `StartEvent` with comment text
   - Parse comment for distinct projects (LLM call)
   - Handle multi-project comments (split into separate items)
   - Output: `list[ExtractProjectsEvent]`

2. **Validate Project** (`validate_project`)
   - Check for [Deleted]/[Removed]
   - LLM call to determine if it's a valid project/product
   - Filter out non-projects (studying, personal tasks, etc.)
   - Output: `ValidateProjectEvent` with `is_valid` flag

3. **Fetch URLs** (`fetch_urls`)
   - Extract URLs from project text using regex
   - Call Firecrawl API for each URL
   - Handle failures gracefully (continue without URL content)
   - Output: `FetchURLsEvent` with URL content dict

4. **Generate Metadata** (`generate_metadata`)
   - LLM calls for: title, short description, full description, hashtags, URL summaries
   - Use structured output (JSON mode) for reliability
   - Output: `GenerateMetadataEvent`

5. **Score Project** (`score_project`)
   - LLM call with scoring prompt
   - Structured output for `idea_score` and `complexity_score` (1-10)
   - Output: `ScoreProjectEvent`

6. **Finalize** (`finalize`)
   - Assemble complete `WaywoProject` object
   - Output: `StopEvent` with result

---

## Milestone 5: Celery Task Integration ✅ COMPLETE

**Goal**: Process comments via Celery with controlled concurrency.

### Tasks:
- [x] Create `process_waywo_comment` task with retry logic
- [x] Create `process_waywo_comments` batch task with limit parameter
- [x] Use `nest_asyncio` for nested event loops in Celery workers
- [x] Add logging with emojis
- [x] Set worker concurrency to 4 (to avoid overwhelming LLM server)

### Implementation Details:
- `nest_asyncio.apply()` called inside task function (not at module level) to avoid uvloop conflicts
- Tasks use `bind=True` and `max_retries=3` with exponential backoff
- Existing projects for a comment are deleted before reprocessing

### Logging Emojis:
- 🚀 Task started
- 🔍 Extracting projects
- ✅ Valid project found
- ❌ Invalid project filtered
- 📥 Fetching URL
- 🤖 LLM call
- 💾 Saving to database
- ✨ Task complete

---

## Milestone 6: Backend API Endpoints ✅ COMPLETE

**Goal**: CRUD endpoints for WaywoProject.

### Implemented Endpoints:
```
GET  /api/waywo-projects
     Query params: tags, min_idea_score, max_idea_score,
                   min_complexity_score, max_complexity_score, is_valid, comment_id
     Response: {projects: [...], total: int, limit: int, offset: int, filters: {...}}

GET  /api/waywo-projects/{project_id}
     Response: {project: {...}, source_comment: {...}, parent_post: {...}}

DELETE /api/waywo-projects/{project_id}
     Response: {status: "deleted", project_id: int, message: str}

POST /api/waywo-comments/{comment_id}/process
     Response: {status: "task_queued", task_id: str, comment_id: int}

POST /api/process-waywo-comments
     Body: {limit: int?}
     Response: {status: "queued", task_id: str, limit: int}

GET  /api/waywo-projects/hashtags
     Response: {hashtags: [str, ...], total: int}
```

---

## Milestone 7: Frontend - Comment Detail Page ✅ COMPLETE

**Goal**: View individual comment with processing trigger.

### Page: `frontend/app/pages/comments/[id].vue`

**Features**:
- Header with comment metadata (author avatar, name, date)
- Link to view on Hacker News
- Comment text (rendered HTML with prose styling)
- **Process Comment Button**: Triggers `/api/waywo-comments/{id}/process`
- Processing status alert with task ID
- Parent post info card with link to filtered comments
- List of extracted WaywoProjects with:
  - Title, validity badge
  - Idea and complexity scores
  - Short description
  - Hashtags as chips
  - Click to navigate to project detail
- Metadata card (comment ID, parent ID, replies count, type)

---

## Milestone 8: Frontend - Projects List Page ✅ COMPLETE

**Goal**: Browse and filter WaywoProjects.

### Page: `frontend/app/pages/projects/index.vue`

**Features**:
- Header with project icon and title
- Filter indicator when filtered by comment_id (with clear button)
- Stats card showing total project count
- Refresh button
- **Project cards** showing:
  - Title with invalid badge if applicable
  - Short description
  - Full description
  - Idea score and complexity score badges
  - Hashtags as chips
  - Created date
  - Delete button (with confirmation)
  - View Details link
- **Pagination** (Previous/Next with item range display)
- Empty state with link to comments page

---

## Milestone 9: Frontend - Project Detail Page ✅ COMPLETE

**Goal**: Comprehensive project view with expandable sections.

### Page: `frontend/app/pages/projects/[id].vue`

**Layout** (top to bottom):
1. **Back Button**: Link to projects list
2. **Header**: Title, invalid badge, short description, scores display
3. **Tags**: Hashtags as chips
4. **Delete Button**: Small text link below tags (with confirmation, redirects after delete)
5. **Invalid Reason Alert**: Shows reason if project marked invalid
6. **Description Card**: Full description text
7. **Collapsible: URLs & Scraped Content**
   - List of project URLs (clickable external links)
   - Scraped content summaries for each URL
8. **Collapsible: Original Comment**
   - Author avatar and name (links to HN profile)
   - Comment timestamp
   - Full comment text (rendered HTML)
   - Links to view on HN and view post comments
9. **Collapsible: Processing Logs**
   - Workflow step logs with emojis
   - Scrollable log viewer
10. **Metadata Card**: Project ID, source comment ID, created/processed timestamps

---

## Additional Fixes & Improvements ✅ COMPLETE

### Navigation Fix
- Replaced all `NuxtLink` components with regular `<a href>` tags
- Replaced all `router.push()` calls with `window.location.href`
- Fixed hydration mismatch caused by unregistered `ThemeToggle` component
- Ensures reliable full-page navigation (client-side routing was broken)

### File Structure
- Moved `pages/comments.vue` → `pages/comments/index.vue`
- Moved `pages/projects.vue` → `pages/projects/index.vue`
- Proper Nuxt 4 page structure for nested routes

### Delete Functionality
- Added `delete_project()` function in `db_client.py`
- Added `DELETE /api/waywo-projects/{project_id}` endpoint
- Delete buttons on both project list and detail pages
- Confirmation dialog before deletion
- Immediate UI update on list page, redirect on detail page

---

## Implementation Status

| Phase | Milestones | Description | Status |
|-------|------------|-------------|--------|
| **Phase 1** | 1, 2 | Database foundation & workflow setup | ✅ Complete |
| **Phase 2** | 3, 4, 5 | Workflow implementation & Celery | ✅ Complete |
| **Phase 3** | 6, 7, 8, 9 | API & Frontend | ✅ Complete |
| **Phase 4** | 10, 11 | Vector Embeddings, RAG & Observability | ✅ Complete |
| **Phase 5** | 12, 13 | Jupyter Lab & Workflow Visualization | ✅ Complete |
| **Phase 6** | 14 | Project Bookmarking | ✅ Complete |
| **Phase 7** | 15 | Project Filtering UI | ✅ Complete |
| **Phase 8** | 16 | Reranking for RAG | ✅ Complete |
| **Phase 9** | 17 | Project Screenshots | ✅ Complete |
| **Phase 10** | 18 | Similar Projects | ✅ Complete |
| **Phase 10.5** | 18.5 | Project Quality & Display Improvements | ✅ Complete |
| **Phase 11** | 19, 20 | Voice Interface (STT & TTS) | 🔲 Planned |
| **Phase 12** | 21 | Safety & Content Moderation | 🔲 Planned |
| **Phase 13** | 22 | Vision-Language Screenshot Analysis | 🔲 Planned |
| **Phase 14** | 23 | Multimodal Visual Search | 🔲 Planned |
| **Phase 15** | 24 | Upgraded LLM & Tag Improvements | 🔲 Planned |
| **Phase 16** | 25 | Audio Summaries / Podcast Generation | 🔲 Planned |

---

## Configuration Reference

### LLM (Nemotron)
- Base URL: `http://192.168.6.19:8002/v1`
- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4`

### Firecrawl
- URL: `http://localhost:3002` (accessed via `host.docker.internal:3002` from containers)
- No auth required

### SQLite
- Path: `/app/data/waywo.db` (in container)
- Local: `./data/waywo.db`

### Celery
- Broker: `redis://redis:6379/0`
- Concurrency: 4 workers (reduced to avoid overwhelming LLM server)

### Embedding Service
- URL: `http://192.168.5.96:8000`
- Model: `nvidia/llama-embed-nemotron-8b`
- Embedding dimension: 4096

### Rerank Service
- URL: `http://192.168.5.173:8111`
- Model: `nvidia/llama-nemotron-rerank-1b-v2`
- Max sequence length: 512 tokens (configurable up to 8192)

---

## Milestone 10: Vector Embeddings and RAG

**Goal**: Add semantic search and RAG chatbot capabilities using vector embeddings.

### Dependencies Added:
| Package | Purpose |
|---------|---------|
| `sqliteai-vector` | SQLite extension for vector similarity search |

### Files Created/Modified:
| File | Action |
|------|--------|
| `pyproject.toml` | Added `sqliteai-vector>=0.1.0` |
| `src/embedding_client.py` | **New** - HTTP client for embedding service |
| `src/db_models.py` | Added `description_embedding` BLOB column to `WaywoProjectDB` |
| `src/database.py` | Added vector extension loading and `vector_init()` |
| `src/db_client.py` | Added `semantic_search()` and `get_projects_with_embeddings_count()` |
| `src/workflows/events.py` | Added `EmbeddingGeneratedEvent` |
| `src/workflows/waywo_project_workflow.py` | Added `generate_embedding` step |
| `src/workflows/waywo_chatbot_workflow.py` | **New** - RAG chatbot workflow |
| `src/main.py` | Added semantic search and chatbot API endpoints |
| `frontend/app/pages/search.vue` | **New** - Semantic search page |
| `frontend/app/pages/chat.vue` | **New** - RAG chatbot page |

### New API Endpoints:
```
GET  /api/embedding/health
     Response: {status: "healthy/unhealthy", url: "..."}

GET  /api/semantic-search/stats
     Response: {total_projects, projects_with_embeddings, embedding_coverage}

POST /api/semantic-search
     Body: {query: "...", limit: 10}
     Response: {results: [{project: {...}, similarity: 0.89}, ...], query, total}

POST /api/waywo-chatbot
     Body: {query: "...", top_k: 5}
     Response: {response: "...", source_projects: [...], query, projects_found}
```

### Processing Workflow Changes:
- New step `generate_embedding` added after `score_project`
- Combines title + description + hashtags for embedding text
- Embeddings stored in `description_embedding` column as FLOAT32 blob
- Embeddings are optional - workflow continues if embedding service unavailable

### Frontend Pages:
- **Search Page** (`/search`): Semantic search with similarity scores
- **Chat Page** (`/chat`): RAG chatbot with source project links

### Vector Search Configuration:
```sql
vector_init('waywo_projects', 'description_embedding',
  'type=FLOAT32,dimension=4096,distance=COSINE')
```

---

## Milestone 11: LLM Observability with Phoenix

**Goal**: Add OpenTelemetry-based tracing to LlamaIndex workflows, sending traces to Arize Phoenix for visualization and debugging.

### Dependencies to Add:
| Package | Purpose |
|---------|---------|
| `openinference-instrumentation-llama-index` | Auto-instruments LlamaIndex LLM/embedding calls |
| `opentelemetry-sdk` | OpenTelemetry SDK for trace management |
| `opentelemetry-exporter-otlp-proto-http` | OTLP HTTP exporter to send traces to Phoenix |

### Files to Create/Modify:
| File | Action |
|------|--------|
| `pyproject.toml` | Add OpenTelemetry and OpenInference packages |
| `src/tracing.py` | **New** - Tracing setup and initialization |
| `src/main.py` | Initialize tracing on FastAPI startup |
| `src/celery_app.py` | Initialize tracing for Celery workers |
| `docker-compose.yml` | Add `PHOENIX_HOST` env var for backend/worker services |

### Implementation Details:

**Tracing Configuration:**
- Phoenix endpoint: `http://phoenix:6006/v1/traces` (HTTP OTLP)
- Service name: `waywo-backend` / `waywo-worker`
- Auto-instruments: LLM calls, embedding calls, workflow steps

**What Gets Traced:**
- All `llm.acomplete()` calls (prompts, responses, latency)
- Embedding service calls
- Workflow step execution
- Token usage and model info

**Phoenix UI Access:**
- URL: `http://localhost:6006`
- Shows trace waterfall, LLM inputs/outputs, latency breakdown

### Tasks:
- [x] Add OpenTelemetry packages to pyproject.toml
- [x] Create `src/tracing.py` with initialization function
- [x] Initialize tracing in FastAPI startup
- [x] Initialize tracing in Celery worker
- [x] Add PHOENIX_HOST to docker-compose.yml
- [x] Test traces appear in Phoenix UI

---

## Milestone 12: Jupyter Lab Integration

**Goal**: Add Jupyter Lab as a development/exploration tool with full access to the application's dependencies.

### Dependencies Added:
| Package | Purpose |
|---------|---------|
| `jupyterlab>=4.0.0` | Interactive notebook environment |

### Files Created/Modified:
| File | Action |
|------|--------|
| `pyproject.toml` | Added `notebook` optional dependency group with `jupyterlab` |
| `Dockerfile` | Added `.[notebook]` to pip install |
| `docker-compose.yml` | Added `jupyter` service |
| `notebooks/getting_started.ipynb` | **New** - Sample notebook with project examples |

### Docker Service Configuration:
- Container: `waywo-jupyter`
- Port: `8888` (http://localhost:8888)
- Authentication: Disabled (development only)
- Notebook directory: `/app/notebooks`
- Depends on: `redis` (healthy), `migrate` (completed)

### Sample Notebook Contents:
1. **Setup** - Path configuration and async support
2. **Database Access** - Query posts, comments, projects using SQLAlchemy
3. **Embedding Client** - Generate embeddings for text
4. **Semantic Search** - Find similar projects by vector similarity
5. **LLM Client** - Make LLM calls using the configured endpoint
6. **Workflow Testing** - Run workflow components interactively
7. **RAG Chatbot** - Test the chatbot workflow
8. **Raw SQL** - Direct SQL queries for advanced analysis

### Usage:
```bash
# Start Jupyter Lab
docker compose up jupyter

# Access at http://localhost:8888
```

---

## Milestone 13: Workflow Visualizer

**Goal**: Add workflow visualization capabilities to visualize LlamaIndex workflows, supporting both static workflow structure diagrams and runtime execution traces.

### Dependencies Added:
| Package | Purpose |
|---------|---------|
| `llama-index-utils-workflow>=0.9.0` | Workflow visualization utilities |

### Files Created/Modified:
| File | Action |
|------|--------|
| `pyproject.toml` | Added `llama-index-utils-workflow` dependency |
| `src/workflows/events.py` | Added chatbot workflow events |
| `src/workflows/waywo_chatbot_workflow.py` | Converted to proper LlamaIndex Workflow class |
| `src/workflows/__init__.py` | Updated exports for new events and workflow |
| `src/visualization.py` | **New** - Visualization utility functions |
| `src/workflow_server.py` | **New** - WorkflowServer configuration |
| `src/main.py` | Added visualization endpoints and mounted WorkflowServer |

### New Chatbot Events:
| Event | Description |
|-------|-------------|
| `ChatQueryEvent` | Initial query with top_k setting |
| `QueryEmbeddingEvent` | Query with generated embedding |
| `ProjectsRetrievedEvent` | Retrieved projects and context |
| `ChatResponseEvent` | Final response with sources |

### Converted Chatbot Workflow Structure:
```
StartEvent
  | @step start()
  v
ChatQueryEvent(query, top_k)
  | @step generate_query_embedding()
  v
QueryEmbeddingEvent(query, top_k, query_embedding)
  | @step retrieve_projects()
  v
ProjectsRetrievedEvent(query, projects, context)
  | @step generate_response()
  v
StopEvent(result=ChatbotResult)
```

### New API Endpoints:
```
GET  /api/workflow-visualization/workflows
     Response: {workflows: [{name, steps, description}, ...]}

GET  /api/workflow-visualization/structure/{name}
     Response: HTML file download

GET  /api/workflow-visualization/executions
     Response: {structures: [...], executions: [...], directory: "..."}

GET  /api/workflow-visualization/executions/{filename}
     Response: HTML file download

POST /api/workflow-visualization/run-with-trace/{name}
     Query params: query (chatbot), comment_id/comment_text (project), top_k
     Response: {execution_id, workflow, trace_file, result: {...}}
```

### Visualization Storage:
- Directory: `data/visualizations/`
- Structure files: `{workflow}_structure.html`
- Execution traces: `{workflow}_execution_{id}.html`

### Usage Examples:

**Generate workflow structure visualization:**
```bash
curl http://localhost:8008/api/workflow-visualization/structure/chatbot -o chatbot.html
open chatbot.html
```

**Run chatbot with execution trace:**
```bash
curl -X POST "http://localhost:8008/api/workflow-visualization/run-with-trace/chatbot?query=AI%20projects"
```

---

## Milestone 14: Project Bookmarking ✅ COMPLETE

**Goal**: Add star/unstar functionality to projects with a filter to view bookmarked projects.

### Backend Changes

| File | Change |
|------|--------|
| `src/db_models.py` | Added `is_bookmarked` boolean column to `WaywoProjectDB` |
| `src/models.py` | Added `is_bookmarked` field to `WaywoProject` and `WaywoProjectSummary` |
| `src/db_client.py` | Added `toggle_bookmark()` and `get_bookmarked_count()` functions |
| `src/db_client.py` | Added `is_bookmarked` filter to `get_all_projects()` |
| `src/main.py` | Added `POST /api/waywo-projects/{id}/bookmark` endpoint |
| `src/main.py` | Added `bookmarked` query param and `bookmarked_count` to `GET /api/waywo-projects` |
| `src/migrate.py` | Added migration for `is_bookmarked` column |

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/app/pages/projects/index.vue` | Added star button on project cards, filter tabs (All/Bookmarked) |
| `frontend/app/pages/projects/[id].vue` | Added star button on project detail page |

### API

```
POST /api/waywo-projects/{project_id}/bookmark
     Response: { "is_bookmarked": true/false, "project_id": 123 }

GET /api/waywo-projects?bookmarked=true
     (existing endpoint, new filter param)
     Response includes: bookmarked_count for badge display
```

### UI Features
- Star icon on each project card (yellow when bookmarked)
- Star icon on project detail page header
- Filter tabs: "All Projects" | "Bookmarked" (with count badge)
- Optimistic UI updates on toggle

---

## Milestone 15: Project Filtering UI

**Goal**: Add a comprehensive filtering system for the Projects list page with tag multi-select, score range sliders, and date range picker, all synced to URL query parameters.

### Backend Changes

| File | Change |
|------|--------|
| `src/main.py` | Expose `date_from` and `date_to` query params in `GET /api/waywo-projects` |

### Frontend Changes

| File | Change |
|------|--------|
| `frontend/app/pages/projects/index.vue` | Add filter section UI and URL sync logic |

### Filter Section UI

**Layout**: Collapsible filter panel above the projects list with:

1. **Tags Filter**
   - Multi-select combobox with autocomplete
   - Fetches options from `GET /api/waywo-projects/hashtags`
   - Shows selected tags as removable chips

2. **Score Range Sliders**
   - Idea Score: Dual-handle slider (1-10)
   - Complexity Score: Dual-handle slider (1-10)
   - Show current range values

3. **Date Range Picker**
   - Start date input
   - End date input

4. **Filter Actions**
   - "Clear All" button to reset filters
   - Active filter count badge on the filter toggle

### URL Query Parameter Sync

| Filter | Query Param | Example |
|--------|-------------|---------|
| Tags | `tags` | `?tags=ai,llm,saas` |
| Min Idea Score | `min_idea` | `?min_idea=5` |
| Max Idea Score | `max_idea` | `?max_idea=10` |
| Min Complexity | `min_complexity` | `?min_complexity=3` |
| Max Complexity | `max_complexity` | `?max_complexity=8` |
| Date From | `date_from` | `?date_from=2024-01-01` |
| Date To | `date_to` | `?date_to=2024-12-31` |
| Bookmarked | `bookmarked` | `?bookmarked=true` |

**Behavior:**
- On filter change: Update URL without page reload
- On page load: Read URL params and apply filters
- Shareable URLs with filter state

### Tasks

- [x] Expose `date_from` and `date_to` in API endpoint
- [x] Create tag multi-select component with autocomplete
- [x] Create score range slider components (dual-handle)
- [x] Create date range picker inputs
- [x] Implement URL param sync (read on mount, update on change)
- [x] Add collapsible filter panel with active filter count
- [x] Add "Clear All Filters" button
- [x] Style filter section to match existing UI

---

## Milestone 16: Reranking for RAG ✅ COMPLETE

**Goal**: Add a reranking step to semantic search and chatbot to dramatically improve result relevance using the Nemotron Reranker model.

### Model
- **llama-nemotron-rerank-1b-v2** - Cross-encoder fine-tuned for multilingual retrieval
- Supports up to 8192 tokens per document
- Self-hosted via FastAPI service

### Architecture
```
Query → Embedding Search (top_k × 3) → Reranker (top_k) → Response
```

### Files Created/Modified

| File | Action |
|------|--------|
| `services/rerank-service/` | **New** - FastAPI rerank microservice |
| `src/rerank_client.py` | **New** - HTTP client for reranker service |
| `src/workflows/events.py` | Added `ProjectsCandidatesEvent` for rerank pipeline |
| `src/workflows/waywo_chatbot_workflow.py` | Added reranking step after retrieval |
| `src/main.py` | Added rerank health endpoint, updated search with reranking |
| `docker-compose.yml` | Added `RERANK_URL` environment variable |
| `frontend/app/pages/admin.vue` | Added reranker to services health display |
| `notebooks/getting_started.ipynb` | Added rerank service testing section |

### Rerank Service

```
services/rerank-service/
├── main.py          # FastAPI service with /rerank and /health endpoints
├── pyproject.toml   # Dependencies (transformers, torch, fastapi)
├── sample.py        # Standalone usage example
└── README.md        # Documentation
```

### New API Endpoints

```
GET /api/rerank/health
    Response: {status: "healthy/unhealthy", url: "..."}

POST /api/semantic-search
     Body: {query: "...", limit: 10, use_rerank: true}
     - Fetches limit × 3 candidates by embedding similarity
     - Reranks to top `limit` by relevance score
     - Returns reranked results with both similarity and rerank_score
     - Falls back to similarity order if rerank service unavailable

POST /api/waywo-chatbot
     - Automatically uses reranking for context retrieval
     - Better answers due to more relevant context
```

### Chatbot Workflow Changes

New workflow flow with reranking:
```
StartEvent
  | @step start()
  v
ChatQueryEvent(query, top_k)
  | @step generate_query_embedding()
  v
QueryEmbeddingEvent(query, top_k, query_embedding)
  | @step retrieve_candidates()  ← Fetches top_k × 3 candidates
  v
ProjectsCandidatesEvent(query, top_k, candidates)
  | @step rerank_projects()      ← Reranks and filters to top_k
  v
ProjectsRetrievedEvent(query, projects, context)
  | @step generate_response()
  v
StopEvent(result=ChatbotResult)
```

### Configuration

```yaml
# docker-compose.yml
RERANK_URL: http://192.168.5.173:8111
```

### Tasks

- [x] Deploy/configure reranker model endpoint
- [x] Create `src/rerank_client.py` with retry logic
- [x] Update semantic search to fetch more candidates
- [x] Add reranking step to search results
- [x] Update chatbot workflow with reranking
- [x] Add `use_rerank` toggle to search API
- [x] Add rerank scores to response
- [x] Add rerank health check endpoint
- [x] Add reranker to admin services health page

### Milestone 16.1: Rerank Comparison Mode ✅ COMPLETE

**Goal**: Add side-by-side comparison view on semantic search page to visualize difference between similarity-based and reranked results.

**Files Modified:**
| File | Change |
|------|--------|
| `src/main.py` | Return `original_results` alongside `results` when reranking |
| `frontend/app/pages/search.vue` | Add toggles and side-by-side comparison layout |
| `frontend/app/components/SearchResultCard.vue` | **New** - Reusable result card component |

**UI Features:**
- "Use Rerank" toggle (default: on)
- "Compare Mode" toggle (visible when Use Rerank is on)
- Side-by-side columns: "By Similarity" vs "By Relevance"
- Shows both similarity score and rerank score
- Service health badges for both Embedding and Rerank services

**API Response (when use_rerank=true):**
```json
{
  "results": [...],           // Reranked results
  "original_results": [...],  // Top N by similarity (for comparison)
  "query": "...",
  "total": 10,
  "reranked": true
}
```

---

## Milestone 17: Project Screenshots ✅ COMPLETE

**Goal**: Automatically capture screenshots of project URLs during processing and display them in the UI.

### Approach
- Playwright runs as a local library inside the main app (no separate service)
- Screenshots captured as a post-processing step in `tasks.py` after projects are saved
- Full JPEG + 320x200 thumbnail generated via Pillow
- Stored in `./media/screenshots/` volume, served via FastAPI StaticFiles at `/media/`
- Failures are non-blocking (logged but don't prevent project creation)

### Files Created/Modified

| File | Action |
|------|--------|
| `pyproject.toml` | Added `playwright>=1.40.0`, `Pillow>=10.0.0` |
| `Dockerfile` | Added `PLAYWRIGHT_BROWSERS_PATH` env var, `playwright install --with-deps chromium` |
| `src/screenshot_client.py` | **New** - `capture_screenshot()` async, `save_screenshot_to_disk()`, `ScreenshotError` |
| `src/db_models.py` | Added `screenshot_path` column (nullable Text) to `WaywoProjectDB` |
| `src/models.py` | Added `screenshot_path` field to `WaywoProject` and `WaywoProjectSummary` |
| `src/migrate.py` | Added idempotent `ALTER TABLE` migration for `screenshot_path` column |
| `src/db_client.py` | Added `screenshot_path` to all project constructors, new `update_project_screenshot()` |
| `src/tasks.py` | Added post-save screenshot capture for first URL (non-fatal try/except) |
| `src/main.py` | Added `StaticFiles` mount at `/media` for serving screenshots |
| `src/firecrawl_client.py` | Fixed URL extraction: added `html.unescape()` to decode HN `&#x2F;` entities |
| `src/workflows/waywo_project_workflow.py` | Fallback URL extraction from `original_comment_text` when LLM strips URLs |
| `src/test/test_url_extraction.py` | **New** - 11 tests for URL extraction with HN HTML entity encoding |
| `frontend/app/pages/projects/index.vue` | Added 160x96px thumbnail area on project cards with placeholder icon |
| `frontend/app/pages/projects/[id].vue` | Added full screenshot Card section between Description and URLs |

### Screenshot Configuration

- Resolution: 1280x800 (desktop viewport)
- Format: JPEG (quality 80)
- Thumbnail: 320x200 for list cards
- Timeout: 30 seconds per URL
- Navigation: `wait_until="networkidle"` (falls back to screenshot on timeout)
- Storage: `./media/screenshots/{project_id}.jpg` and `{project_id}_thumb.jpg`

### Bug Fixes During Implementation

1. **HN HTML entity encoding**: URLs in HN comments use `&#x2F;` for `/`, causing the regex `https?://` to never match. Fixed by adding `html.unescape()` before URL extraction.
2. **LLM strips URLs**: The LLM project extraction step returns cleaned text without URLs. Added fallback to extract URLs from `original_comment_text` (raw HTML).
3. **Playwright browser path**: Browsers installed as root during Docker build went to `/root/.cache/ms-playwright/`, but the app runs as `app` user. Fixed by setting `PLAYWRIGHT_BROWSERS_PATH=/app/.playwright-browsers` in Dockerfile.

### Tasks

- [x] Add Playwright and Pillow dependencies
- [x] Install Chromium in Dockerfile with correct browser path
- [x] Create `src/screenshot_client.py` with async capture + thumbnail generation
- [x] Add database column, migration, and model fields
- [x] Add `screenshot_path` to all db_client project constructors
- [x] Add post-save screenshot capture in tasks.py (non-fatal)
- [x] Mount `/media` via StaticFiles for serving screenshots
- [x] Fix HN HTML entity URL extraction (`html.unescape`)
- [x] Fix LLM URL stripping (fallback to original comment text)
- [x] Fix Playwright browser path for non-root Docker user
- [x] Update project list cards with thumbnails
- [x] Update project detail page with full screenshot
- [x] Write URL extraction tests (11 tests)

---

## Milestone 18: Similar Projects ✅ COMPLETE

**Goal**: Add a "Similar Projects" section to the project detail page using existing embeddings.

### Approach
- Use vector similarity on existing `description_embedding`
- Exclude current project from results
- Show 3-5 most similar projects

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/db_client.py` | Add `get_similar_projects()` function |
| `src/main.py` | Add similar projects endpoint |
| `frontend/app/pages/projects/[id].vue` | Add similar projects section |

### New API Endpoint

```
GET /api/waywo-projects/{id}/similar
    Query params: limit (default: 5)
    Response: {
      similar_projects: [
        {project: {...}, similarity: 0.92},
        ...
      ],
      project_id: 123
    }
```

### Tasks

- [x] Add `get_similar_projects()` to db_client
- [x] Create API endpoint
- [x] Add "Similar Projects" card to detail page
- [x] Display similarity percentage
- [x] Handle projects without embeddings
- [x] Add loading state for similar projects

---

## Milestone 18.5: Project Quality & Display Improvements ✅ COMPLETE

**Goal**: Batch of small quality-of-life fixes — better descriptions, full scraped content display, primary URL field, HN links on cards, and disable LLM thinking tokens.

### Changes

- **Better descriptions**: Updated LLM prompt from "1-2 sentences" to "3-5 sentences" synthesizing both comment text and scraped web data
- **Store & display full scraped content**: Added `url_contents` field to DB; detail page shows full scraped markdown with summaries as secondary info
- **Extract primary URL**: LLM now identifies the single most important project URL during metadata generation; stored in new `primary_url` field
- **HN link on project cards**: Orange "Y" icon next to date in card footer, linking to the HN comment
- **Primary URL on cards & detail page**: Hostname link next to project title on cards; full URL link below title on detail page
- **Disable LLM thinking**: Added `additional_kwargs` with `enable_thinking: False` to both LLM config functions

### Files Modified

| File | Change |
|------|--------|
| `src/db_models.py` | Added `primary_url` and `url_contents` columns + JSON helpers |
| `src/database.py` | Added safe ALTER TABLE migration in `init_db()` |
| `src/models.py` | Added `primary_url` and `url_contents` to `WaywoProject`, `primary_url` to `WaywoProjectSummary` |
| `src/llm_config.py` | Added `enable_thinking: False` to both LLM functions |
| `src/workflows/prompts.py` | Rewrote `GENERATE_METADATA_TEMPLATE` for 3-5 sentence descriptions and `primary_url` extraction |
| `src/workflows/events.py` | Added `primary_url` to `MetadataGeneratedEvent`, `ScoredProjectEvent`, `EmbeddingGeneratedEvent` |
| `src/workflows/waywo_project_workflow.py` | Extract `primary_url` in `generate_metadata`, include both new fields in `finalize` |
| `src/tasks.py` | Pass `primary_url` and `url_contents` to `WaywoProject` construction |
| `src/db_client.py` | Added both fields to all 4 CRUD functions |
| `frontend/app/pages/projects/index.vue` | Added HN "Y" icon, primary URL hostname link, updated interface |
| `frontend/app/pages/projects/[id].vue` | Added HN button, primary URL link, full scraped content display, updated interface |

---

## Milestone 19: Voice Input (Speech-to-Text)

**Goal**: Add voice input capability to the chatbot page using Nemotron speech models.

### Models (Choose One)
- **Parakeet TDT 0.6B v3** - Fast, multilingual ASR (25 languages)
- **Canary-Qwen-2.5B** - Higher accuracy, translation support
- **Nemotron Speech Streaming 0.6B** - Real-time streaming for low latency

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/stt_client.py` | **New** - Speech-to-text client |
| `src/main.py` | Add STT endpoint (WebSocket or REST) |
| `docker-compose.yml` | Add `STT_URL` environment variable |
| `frontend/app/pages/chat.vue` | Add microphone button and recording UI |
| `frontend/app/composables/useVoiceInput.ts` | **New** - Voice recording composable |

### API Options

**Option A: REST (simpler)**
```
POST /api/speech-to-text
     Body: Audio file (WAV/WebM)
     Response: {text: "transcribed text", confidence: 0.95}
```

**Option B: WebSocket (real-time)**
```
WS /api/speech-to-text/stream
   - Send audio chunks
   - Receive partial transcriptions in real-time
```

### Frontend Features
- Microphone button on chat input
- Visual feedback during recording (waveform)
- Auto-stop on silence detection
- Transcribed text populates input field

### Tasks

- [ ] Deploy/configure STT model endpoint
- [ ] Create `src/stt_client.py`
- [ ] Add STT API endpoint (REST or WebSocket)
- [ ] Create voice input composable
- [ ] Add microphone button to chat UI
- [ ] Add recording visualization
- [ ] Handle browser permissions
- [ ] Add silence detection / auto-stop
- [ ] Test with various accents/environments

---

## Milestone 20: Voice Output (Text-to-Speech)

**Goal**: Add voice output to read chatbot responses aloud using Nemotron TTS models.

### Model
- **NeMo TTS** - High-quality speech synthesis

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/tts_client.py` | **New** - Text-to-speech client |
| `src/main.py` | Add TTS endpoint |
| `docker-compose.yml` | Add `TTS_URL` environment variable |
| `frontend/app/pages/chat.vue` | Add speaker button on responses |
| `frontend/app/composables/useVoiceOutput.ts` | **New** - Audio playback composable |

### New API Endpoint

```
POST /api/text-to-speech
     Body: {text: "...", voice: "default"}
     Response: Audio stream (WAV/MP3)
```

### Frontend Features
- Speaker icon on each chatbot response
- Play/pause/stop controls
- Voice selection (if multiple voices available)
- Visual indicator while speaking

### Tasks

- [ ] Deploy/configure TTS model endpoint
- [ ] Create `src/tts_client.py`
- [ ] Add TTS API endpoint
- [ ] Create voice output composable
- [ ] Add speaker button to chat responses
- [ ] Add audio playback controls
- [ ] Cache generated audio for replay
- [ ] Add voice selection UI (optional)

---

## Milestone 21: Safety & Content Moderation

**Goal**: Add content safety checks using Nemotron Safety model to filter inappropriate content and protect against jailbreak attempts.

### Model
- **Nemotron Safety** - Jailbreak detection, content safety, privacy detection

### Features
- Filter spam/inappropriate comments before processing
- Detect jailbreak attempts in chatbot queries
- Flag projects with potentially sensitive content
- Add safety scores to projects

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/safety_client.py` | **New** - Safety model client |
| `src/models.py` | Add safety fields to WaywoProject |
| `src/db_models.py` | Add `safety_score`, `safety_flags` columns |
| `src/workflows/waywo_project_workflow.py` | Add safety check step |
| `src/workflows/waywo_chatbot_workflow.py` | Add input validation |
| `src/main.py` | Add safety check to chatbot endpoint |
| `src/migrate.py` | Add migration for safety columns |
| `frontend/app/pages/projects/[id].vue` | Display safety warnings |

### Safety Check Types

| Check | Description |
|-------|-------------|
| `jailbreak` | Detect prompt injection attempts |
| `toxicity` | Harmful or offensive content |
| `privacy` | PII or sensitive data exposure |
| `spam` | Low-quality or promotional content |

### New API Behavior

```
POST /api/waywo-chatbot
     - Validates query against jailbreak patterns
     - Returns error if query is flagged
     - Logs flagged attempts for review

GET /api/waywo-projects/{id}
     Response includes: safety_score, safety_flags[]
```

### Tasks

- [ ] Deploy/configure safety model endpoint
- [ ] Create `src/safety_client.py`
- [ ] Add safety check to project workflow
- [ ] Add jailbreak detection to chatbot
- [ ] Add database columns and migration
- [ ] Display safety warnings in UI
- [ ] Add admin view for flagged content
- [ ] Configure safety thresholds

---

## Milestone 22: Vision-Language Screenshot Analysis

**Goal**: Use Nemotron Nano VL to analyze project screenshots and auto-generate descriptions, detect project types, and validate content.

### Model
- **Nemotron Nano VL 12B** - Vision-language model for document intelligence

### Features
- Analyze screenshots to generate descriptions
- Detect project type (SaaS, mobile app, CLI, library, etc.)
- Extract visible text/features from landing pages
- Validate if screenshot matches project description

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/vl_client.py` | **New** - Vision-language model client |
| `src/models.py` | Add VL analysis fields |
| `src/db_models.py` | Add `vl_description`, `detected_type`, `vl_features` |
| `src/workflows/waywo_project_workflow.py` | Add VL analysis step (after screenshot) |
| `src/main.py` | Add VL analysis endpoint |
| `src/migrate.py` | Add migration for VL columns |
| `frontend/app/pages/projects/[id].vue` | Display VL insights |

### VL Analysis Output

```json
{
  "detected_type": "saas_dashboard",
  "vl_description": "A dark-themed analytics dashboard showing...",
  "features": ["charts", "sidebar_navigation", "data_tables"],
  "technologies": ["react", "tailwind"],
  "confidence": 0.87
}
```

### Project Type Categories
- `saas_dashboard` - Web application with dashboard UI
- `mobile_app` - Mobile application screenshot
- `landing_page` - Marketing/landing page
- `cli_tool` - Terminal/command-line interface
- `library_docs` - Documentation site
- `api_docs` - API documentation
- `portfolio` - Personal portfolio/blog
- `ecommerce` - E-commerce site
- `other` - Uncategorized

### Tasks

- [ ] Deploy/configure VL model endpoint
- [ ] Create `src/vl_client.py`
- [ ] Add VL analysis step to workflow (depends on Milestone 17)
- [ ] Add database columns and migration
- [ ] Create analysis prompts for different aspects
- [ ] Display VL insights on project detail page
- [ ] Add project type badges/filters
- [ ] Use VL description as fallback when scraping fails

---

## Milestone 23: Multimodal Visual Search

**Goal**: Enable searching projects by visual description using the multimodal reranker model.

### Model
- **llama-nemotron-rerank-vl-1b-v2** - Vision-language cross-encoder

### Features
- Search by visual description: "dark mode dashboard with charts"
- Combine text embeddings + screenshot analysis
- Visual similarity between projects

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/vl_rerank_client.py` | **New** - Multimodal reranker client |
| `src/db_client.py` | Add `visual_search()` function |
| `src/main.py` | Add visual search endpoint |
| `frontend/app/pages/search.vue` | Add visual search mode toggle |

### New API Endpoint

```
POST /api/visual-search
     Body: {
       query: "minimalist landing page with hero section",
       limit: 10
     }
     Response: {
       results: [
         {project: {...}, visual_score: 0.89, text_score: 0.76},
         ...
       ]
     }
```

### Search Modes
- **Text Only**: Current semantic search (embeddings)
- **Visual Only**: Match query against screenshot analysis
- **Combined**: Weighted combination of both scores

### Tasks

- [ ] Deploy/configure VL reranker endpoint
- [ ] Create `src/vl_rerank_client.py`
- [ ] Implement visual search function
- [ ] Add visual search API endpoint
- [ ] Update search page with mode toggle
- [ ] Display visual match scores
- [ ] Add visual search examples/suggestions

---

## Milestone 24: Upgraded LLM & Tag Improvements

**Goal**: Improve extraction quality with larger Nemotron model and standardize tag generation.

### Models
- **Llama Nemotron Super 49B v1.5** - Higher accuracy for complex comments
- Keep Nano for speed, use Super for re-processing or complex cases

### Tag Improvements
- Standardize similar tags (ml → machine-learning)
- Create tag hierarchy (category → subcategory)
- Detect technology stack from URLs/descriptions
- Limit to curated tag vocabulary

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/llm_config.py` | Add Super model configuration |
| `src/tag_normalizer.py` | **New** - Tag standardization logic |
| `data/tag_vocabulary.yml` | **New** - Curated tag list with aliases |
| `src/workflows/prompts.py` | Update prompts for better tag generation |
| `src/workflows/waywo_project_workflow.py` | Add tag normalization step |
| `src/main.py` | Add re-process with upgraded model option |

### Tag Vocabulary Example

```yaml
categories:
  ai:
    canonical: "artificial-intelligence"
    aliases: ["ai", "ml", "machine-learning", "deep-learning"]
    subcategories: ["nlp", "computer-vision", "llm"]

  web:
    canonical: "web-development"
    aliases: ["web", "frontend", "backend", "fullstack"]
    subcategories: ["react", "vue", "nextjs", "nuxt"]
```

### New API Features

```
POST /api/waywo-comments/{id}/process
     Query params: model=super (use upgraded model)

GET /api/waywo-projects/tags/suggest
     Body: {text: "..."}
     Response: {suggested_tags: [...]}
```

### Tasks

- [ ] Deploy/configure Super model endpoint
- [ ] Create tag vocabulary file
- [ ] Implement tag normalizer
- [ ] Update workflow with normalization step
- [ ] Add model selection to process endpoint
- [ ] Create tag suggestion endpoint
- [ ] Migrate existing tags to normalized form
- [ ] Add tag management admin UI (optional)

---

## Milestone 25: Audio Summaries / Podcast Generation

**Goal**: Generate audio summaries of trending projects as shareable podcast-style content.

### Features
- Weekly digest: "Top 10 projects this month"
- Individual project audio summaries
- Shareable audio clips
- RSS feed for podcast apps

### Files to Create/Modify

| File | Action |
|------|--------|
| `src/podcast_generator.py` | **New** - Summary generation and TTS orchestration |
| `src/main.py` | Add podcast endpoints |
| `data/podcasts/` | **New** - Generated audio storage |
| `frontend/app/pages/podcast.vue` | **New** - Podcast/audio page |
| `templates/podcast_script.txt` | **New** - Script template for summaries |

### New API Endpoints

```
GET /api/podcast/weekly
    Response: {
      title: "Week of Jan 15, 2026",
      audio_url: "/api/podcast/weekly/2026-01-15.mp3",
      duration: 180,
      projects: [...]
    }

GET /api/podcast/project/{id}
    Response: Audio summary of single project

GET /api/podcast/feed.xml
    Response: RSS feed for podcast apps
```

### Podcast Script Template

```
Welcome to Waywo Weekly, your digest of the most interesting projects
from Hacker News "What are you working on" threads.

This week's top project is {title} by {author}.
{short_description}.
The community rated it {idea_score} out of 10 for idea quality.

[Continue for each project...]
```

### Tasks

- [ ] Create podcast script templates
- [ ] Implement summary text generation (LLM)
- [ ] Integrate TTS for audio generation (depends on Milestone 20)
- [ ] Create audio storage and serving
- [ ] Build weekly digest generation (Celery scheduled task)
- [ ] Create podcast page with audio player
- [ ] Generate RSS feed
- [ ] Add share buttons for audio clips