# Waywo Improvement Plan

This document tracks concrete improvement milestones to make the project leaner, better organized, and easier to extend for both humans and coding agents.

---

## Current State Summary (updated post-M2 refactor)

| Area | Files | Lines | Notes |
|------|-------|-------|-------|
| `src/` (Python backend) | 40 `.py` files | ~6,370 | Reorganized into `routes/`, `clients/`, `db/`, `worker/` packages |
| `src/routes/` | 7 files | ~1,186 | Extracted from old monolithic `main.py` |
| `src/clients/` | 5 files | ~800 | Grouped external service clients |
| `src/db/` | 4 files | ~1,468 | `client.py` still 926 lines — needs splitting |
| `src/worker/` | 4 files | ~439 | Celery app, tasks, beat, healthcheck |
| `src/workflows/` | 5 files | ~1,807 | Well-organized, two files over 300 lines |
| `src/test/` | 3 test files | ~211 | Minimal coverage |
| `src/main.py` | 1 file | 49 | Down from 1,245 — slim app entry point ✅ |
| `frontend/app/pages/` | 11 `.vue` files | ~4,178 | Several 500+ line pages (unchanged) |
| `frontend/app/components/` | ~300 UI files, 2 custom | - | Many unused shadcn components |
| `services/` | 3 services | - | 1 unused (speech-to-text) |
| `docker-compose.yml` | 1 file | 253 lines | 9 services, some experimental |

---

## Milestone 1: Remove Dead Code and Unused Dependencies

**Goal:** Strip out everything that isn't actively used to reduce noise and confusion.

### 1.1 Remove NAT service and all references
- [x] Delete `nat/` directory (service code, Dockerfile, workflow.yml)
- [x] Delete `src/nat_client.py` (63 lines)
- [x] Remove NAT endpoints from `src/main.py` (lines ~340-369: `/api/nat/health`, `/api/nat/query`)
- [x] Remove `NatQueryRequest` from `src/models.py`
- [x] Remove NAT imports from `src/main.py` (lines 48-49)
- [x] Remove `nat` service block from `docker-compose.yml`
- [x] Remove `NAT_SERVICE_URL` from docker-compose common-env

### 1.2 Remove legacy Redis data code
The project migrated from Redis to SQLite. Redis is still used as the Celery broker (which is fine), but the old data-storage code is dead.
- [x] Delete `src/redis_client.py` (137 lines) - fully replaced by `db_client.py`
- [x] Delete `src/migrate_redis_to_sqlite.py` (162 lines) - one-time migration, already completed
- [x] Remove `redis-om>=0.2.0` from `pyproject.toml` dependencies (not imported anywhere)
- [x] Remove `fakeredis>=2.31.0` from dev dependencies (only used by tests that test the dead redis_client)

**Estimated impact:** ~400 lines of dead Python code removed, cleaner dependency list.

---

## Milestone 2: Reorganize `src/` Backend Structure

**Goal:** Transform the flat `src/` directory into a logical package structure so developers and agents can quickly find and navigate code by domain.

### Current structure (flat, 24 files):
```
src/
├── main.py              (1,245 lines - routes, models, everything)
├── db_client.py         (927 lines - all DB operations)
├── tasks.py             (350 lines)
├── firecrawl_client.py  (326 lines)
├── db_models.py         (263 lines)
├── models.py            (152 lines)
├── ... 18 more files
└── workflows/           (only subdirectory)
```

### Proposed structure:
```
src/
├── main.py              (slim - app creation, startup, middleware, router mounting)
├── settings.py          (centralized config from env vars - new)
├── routes/
│   ├── __init__.py
│   ├── health.py        (health/debug endpoints)
│   ├── posts.py         (waywo-posts CRUD)
│   ├── comments.py      (waywo-comments CRUD)
│   ├── projects.py      (waywo-projects CRUD + bookmarks + similar)
│   ├── search.py        (semantic search + chatbot)
│   ├── admin.py         (admin stats, resets, rebuild index)
│   └── workflows.py     (workflow prompts + visualization endpoints)
├── clients/
│   ├── __init__.py
│   ├── embedding.py     (was embedding_client.py)
│   ├── rerank.py        (was rerank_client.py)
│   ├── firecrawl.py     (was firecrawl_client.py)
│   ├── hn.py            (was hn_client.py)
│   └── screenshot.py    (was screenshot_client.py)
├── db/
│   ├── __init__.py
│   ├── models.py        (was db_models.py)
│   ├── database.py      (was database.py - engine/session setup)
│   ├── client.py        (was db_client.py)
│   └── migrate.py       (was migrate.py)
├── worker/
│   ├── __init__.py
│   ├── app.py           (was celery_app.py)
│   ├── tasks.py         (was tasks.py)
│   ├── beat.py          (was celery_beat.py)
│   └── healthcheck.py   (consolidate celery_worker_healthcheck + celery_beat_healthcheck)
├── workflows/           (keep as-is, already well-organized)
│   ├── __init__.py
│   ├── events.py
│   ├── prompts.py
│   ├── waywo_chatbot_workflow.py
│   └── waywo_project_workflow.py
├── models.py            (Pydantic request/response models)
├── tracing.py           (OpenTelemetry setup)
└── visualization.py     (workflow visualization)
```

### Key changes:
- [x] **Break `main.py` from 1,245 lines down to ~50 lines** by extracting routes into `src/routes/` using FastAPI `APIRouter`
- [x] **Group external service clients** into `src/clients/` - clearer than `*_client.py` scattered at top level
- [x] **Group database code** into `src/db/` - models, engine, client, migrations together
- [x] **Group Celery code** into `src/worker/` - app, tasks, beat, healthchecks together
- [x] **Create `src/settings.py`** to centralize all `os.environ.get()` calls (currently scattered across 10+ files with duplicate default values)
- [x] Update all imports throughout the codebase
- [x] Update `Dockerfile`, `docker-compose.yml` entrypoints
- [x] Update `pyproject.toml` test paths if needed (no changes needed)

**Estimated impact:** `main.py` goes from 1,245 to ~80 lines. Every file becomes findable by domain. Agents can operate on isolated route files without touching unrelated code.

---

## Milestone 3: Break Down Large Files

**Goal:** No single file should require scrolling through hundreds of lines to understand. Target max ~200-300 lines per file.

### 3.1 Backend: Split `db/client.py` (926 lines → 6 files, max 357 lines)
This file contains every database operation. Split by domain:
- [x] `src/db/posts.py` (98 lines) - post CRUD operations
- [x] `src/db/comments.py` (244 lines) - comment CRUD operations
- [x] `src/db/projects.py` (357 lines) - project CRUD, bookmarks, similar projects
- [x] `src/db/search.py` (189 lines) - semantic search, embeddings, vector operations
- [x] `src/db/stats.py` (59 lines) - admin stats, counts
- [x] `src/db/client.py` (55 lines) - re-export all functions for backwards compatibility (thin facade)

### 3.2 Backend: Other files over 300 lines
The M2 refactor brought most files well under 300 lines (`main.py` went from 1,245 → 49). These remaining files are over the target but are less critical since they have cohesive single responsibilities:

| File | Lines | Notes |
|------|-------|-------|
| `workflows/waywo_project_workflow.py` | 550 | Single workflow class — could split steps into separate files but adds complexity |
| `workflows/waywo_chatbot_workflow.py` | 481 | Single workflow class — same tradeoff |
| `worker/tasks.py` | 350 | Slightly over, manageable as-is |
| `clients/firecrawl.py` | 326 | Slightly over, mostly retry/validation logic |

**Recommendation:** Splitting `db/client.py` is the clear win (926 lines, mixed concerns). The workflow files are borderline — they're large but each is a single cohesive class. Consider splitting only if they grow further.

### 3.3 Backend summary (post-M2 refactor)
All other backend files are already under 300 lines:
- `workflows/prompts.py` (281), `db/models.py` (263), `routes/admin.py` (258)
- `workflows/events.py` (245), `routes/search.py` (228), `routes/projects.py` (211)
- Everything else under 200 lines

### 3.4 Frontend: Split large page components (unchanged)
| Page | Lines | Split strategy |
|------|-------|----------------|
| `projects/index.vue` | 858 | Extract filter sidebar, project card, project list into components |
| `projects/[id].vue` | 627 | Extract project header, similar projects section into components |
| `admin.vue` | 532 | Extract service health cards, stats section, action buttons into components |
| `search.vue` | 439 | Extract search filters, result card, compare mode into components |
| `comments/index.vue` | 418 | Extract comment card, filter controls into components |
| `comments/[id].vue` | 377 | Extract comment detail sections into components |

**Estimated impact:** The main backend win is splitting `db/client.py` into ~5 focused files. Frontend pages still need component extraction. After this milestone, no file should exceed ~300 lines (with workflow files as acceptable exceptions at ~500 lines given their cohesive nature).

---

## Milestone 4: Centralize Configuration

**Goal:** All environment-dependent values live in one place, documented and typed.

### Previous problem (resolved):
`os.environ.get()` was called in ~10 different files with hardcoded default IPs and URLs. This has been fixed — all env var reads are now centralized in `src/settings.py` and other files import from there.

### Solution:
- [x] Create `src/settings.py` with centralized config (uses `os.getenv()` with typed defaults — simpler than Pydantic Settings but achieves the same goal)
- [x] Define all config with types and defaults in one place (18 env vars across Redis, LLM, embedding, rerank, firecrawl, data dirs, Phoenix)
- [x] Replace all `os.environ.get()` calls — no scattered env reads remain in other `src/` files
- [x] Add `.env.example` documenting every environment variable (backend at project root, frontend at `frontend/.env.example`)
- [x] Frontend: `NUXT_PUBLIC_API_BASE` documented in `frontend/.env.example` — Nuxt auto-overrides `runtimeConfig.public.apiBase` when the env var is set

**Estimated impact:** Single source of truth for config. New developers/agents can see all knobs in one file. No more scattered hardcoded IPs.

---

## Milestone 5: Frontend Composables and Shared Types

**Goal:** Eliminate duplicated patterns across pages by extracting reusable composables.

### 5.1 Create API composable
- [x] Create `app/composables/useApi.ts` - typed API client with built-in error handling and loading state
- [x] Available for pages to adopt incrementally (pages still work with direct `$fetch` too)

### 5.2 Create domain composables
- Skipped — pages don't share behavior, only types and utility functions. Domain composables (`useProjects()`, `useSearch()`, etc.) would move complexity sideways without reducing it. The `useApi` composable plus shared types is sufficient.

### 5.3 Centralize TypeScript types and utilities
- [x] Create `app/types/models.ts` with all 15 shared interfaces (WaywoProject, WaywoComment, WaywoPost, SearchResult, ChatMessage, etc.)
- [x] Create `app/utils/format.ts` with shared formatting functions (`formatUnixTime`, `formatYearMonth`, `formatISODate`)
- [x] Remove all inline type definitions from 9 page files
- [x] Remove all duplicate format functions from 5 page files
- [x] ~260 lines of duplicated code removed across script sections

---

## Milestone 6: Testing Infrastructure

**Goal:** Go from 2 test files with no coverage visibility to a practical test suite with CI-friendly coverage reporting.

### Current state:
- 2 test files: `test_data_collection.py` (tests dead redis_client), `test_url_extraction.py`
- `pyproject.toml` has pytest + coverage config already set up but unused
- No test for any API endpoint, no test for db_client, no test for workflows
- No CI pipeline running tests

### 6.1 Fix existing tests
- [ ] Update `test_data_collection.py` to test `db_client` instead of dead `redis_client`
- [ ] Verify `test_url_extraction.py` still passes

### 6.2 Add high-value tests (prioritized by risk)
- [ ] **API route tests** - use FastAPI `TestClient` to test each endpoint group
  - Health/debug endpoints
  - Posts CRUD
  - Comments CRUD
  - Projects CRUD (including bookmark, similar, delete)
  - Search endpoints
  - Admin endpoints
- [ ] **Database client tests** - test `db_client.py` operations with an in-memory SQLite DB
- [ ] **Workflow tests** - test project extraction and chatbot workflows with mocked LLM responses
- [ ] **Client tests** - test embedding/rerank/firecrawl clients with mocked HTTP responses

### 6.3 Coverage visibility
- [ ] Add `make test` target to Makefile: `pytest --cov=src --cov-report=term-missing`
- [ ] Add `make test-html` target for HTML coverage report
- [ ] Add coverage badge or minimum threshold (start with whatever current coverage is, then ratchet up)

### 6.4 Frontend tests (lower priority)
- [ ] Add Vitest for component/composable testing
- [ ] Start with composable tests (pure logic, easy to test)

**Estimated impact:** Confidence to refactor. Catch regressions. Coverage visibility motivates incremental improvement.

---

## Milestone 7: Developer Experience Improvements

**Goal:** Make it easy for anyone (or any agent) to get oriented and productive quickly.

### 7.1 Makefile improvements
Current Makefile has 5 targets. Add practical shortcuts:
- [ ] `make test` - run Python tests with coverage
- [ ] `make lint` - run black + isort + flake8 checks
- [ ] `make fmt` - auto-format code
- [ ] `make dev` - start backend + frontend for local development
- [ ] `make seed` - seed database with sample data (if applicable)
- [ ] `make clean` - clean up generated files, caches, etc.

### 7.2 Add `.env.example`
- [ ] Document every environment variable with descriptions and example values
- [ ] Group by service (LLM, Embedding, Rerank, Database, Redis, etc.)

### 7.3 Improve project entry points
- [ ] Add a brief `CLAUDE.md` for coding agents with project conventions, key file locations, how to run tests
- [ ] Keep `PLAN.md` for feature milestones, this `IMPROVEMENTS.md` for code quality milestones

**Estimated impact:** Faster onboarding. Less time figuring out "how do I run X?"

---

## Milestone 8: Minor Cleanups

**Goal:** Small wins that reduce friction and tech debt.

### 8.1 Backend cleanups
- [ ] Remove `RunWithTraceRequest` model from `main.py` (line 1060) - it's defined but the endpoint uses Query params instead
- [ ] Remove deprecated `@app.on_event("startup")` in favor of FastAPI lifespan handler
- [ ] Consolidate duplicate Pydantic models (check if any request/response models in `main.py` duplicate those in `models.py`)
- [ ] Remove inline imports scattered throughout `main.py` (e.g., `import redis`, `import httpx` inside route handlers) - move to top-level once routes are split into separate files

### 8.2 Frontend cleanups
- [ ] Update `frontend/README.md` (references non-existent `/about` route)
- [ ] Remove `v-html` usage in comments pages if possible (XSS risk) or sanitize content
- [ ] Add proper `<title>` / `useHead()` to pages that are missing it

### 8.3 Docker cleanups
- [ ] Review if `jupyter` service should be in a separate `docker-compose.dev.yml` (it's a dev-only tool)
- [ ] Review if `phoenix` and `flower` services should be in a separate dev/observability compose file
- [ ] Add health checks to docker-compose services that are missing them

---

## Suggested Execution Order

| Priority | Milestone | Effort | Risk | Impact |
|----------|-----------|--------|------|--------|
| 1 | **M1: Remove Dead Code** | Low | Low | High - less noise, smaller codebase |
| 2 | **M4: Centralize Config** | Low | Low | Medium - foundation for other work |
| 3 | **M2: Reorganize src/** | Medium | Medium | High - navigability, agent-friendliness |
| 4 | **M3: Break Down Large Files** | Medium | Medium | High - readability |
| 5 | **M6: Testing** | Medium | Low | High - confidence for all future changes |
| 6 | **M5: Frontend Composables** | Medium | Low | Medium - cleaner frontend code |
| 7 | **M7: Developer Experience** | Low | Low | Medium - productivity |
| 8 | **M8: Minor Cleanups** | Low | Low | Low - polish |

M1 and M4 are safe, high-value starting points. M2 is the biggest structural improvement but should happen after dead code removal. M6 (testing) ideally happens before or alongside M2/M3 so refactors are covered by tests.

---

## Metrics to Track

After completing these milestones, the project should achieve:
- No file over 300 lines in `src/`
- `main.py` under 100 lines
- All configuration in one settings file
- Test coverage > 60% for `src/`
- Every page component under 300 lines
- Zero dead code / unused dependencies
- A new developer or coding agent can find any piece of functionality in under 30 seconds
