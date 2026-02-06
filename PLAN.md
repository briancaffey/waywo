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
| **Phase 5** | 12 | Jupyter Lab Integration | ✅ Complete |

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

## Future Enhancements (Not Yet Implemented)

- [ ] Tag-based filtering UI (autocomplete, multi-select)
- [ ] Score range sliders for filtering
- [ ] Date range picker for filtering
- [ ] Bulk delete projects
- [ ] Re-process project button
- [ ] Export projects to CSV/JSON
- [x] Search functionality across projects (semantic search implemented)
- [x] Jupyter Lab for interactive development
- [ ] Project bookmarking/favorites
- [ ] Backfill embeddings for existing projects
