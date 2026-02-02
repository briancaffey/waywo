# Waywo Plan

## Tech stack overview

- [x] docker and docker compose
- [x] FastAPI
- [x] celery worker and celery beat scheduler
- [x] Nuxt.js frontend
- [x] Hacker News Firebase API
- [] Firecrawl for LLM-powered web scraping
- [] NeMo Agent Toolkit for Agentic web crawling
- [x] Pytest for testing suite
- [x] Makefile with make commands that use `docker compose run` for development tasks
- [] IPython Notebooks for demonstrating functionality

## Data structures and Initial Tests

- []

## Data collection

### Terminology
- `WaywoPost` - A monthly "Who is hiring?" / "What are you working on?" HN post
- `WaywoComment` - A top-level reply on a WaywoPost (someone's project submission)

### Pydantic models
- [x] Create `WaywoPost` Pydantic model with all HN API fields (id, by, time, text, kids, etc.)
- [x] Create `WaywoComment` Pydantic model with all HN API fields (id, by, time, text, parent, kids, etc.)

### Storage
- [x] Use regular Redis keys (not RedisOM) for simplicity
- [x] Store all data from the HN API for each comment
- [x] Key structure: `waywo:post:{post_id}` and `waywo:comment:{comment_id}`

### Celery tasks
- [x] `process_waywo_posts` task - loops over posts from waywo.yml, triggers individual post processing
- [x] `process_waywo_post` task - accepts a post ID, fetches top-level comments (kids), stores each as WaywoComment
- [x] Both tasks accept optional `limit` parameters for testing (e.g., limit_posts=3, limit_comments=3)

### API endpoints
- [x] `POST /api/process-waywo-posts` - triggers the `process_waywo_posts` celery task, accepts optional limit params
- [x] `GET /api/waywo-posts` - returns list of WaywoPost metadata with comment counts
- [x] `GET /api/waywo-posts/{post_id}` - returns a single WaywoPost with its comments

### Frontend
- [x] Page to view metadata of each WaywoPost and count of top-level comments (`/posts`)

### Testing
- [x] Use pytest with function-based tests and decorators
- [x] Mock the HN Firebase API - no real API calls in tests
- [x] Reference HN_FIREBASE_API.md for API structure when creating mocks