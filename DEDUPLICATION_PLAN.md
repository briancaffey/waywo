# Deduplication Plan

## Overview

Prevent duplicate projects from being stored when the same author posts about the same project across multiple monthly "What are you working on?" threads (or even within the same thread). When a duplicate is detected, skip expensive LLM processing and instead link the new comment as an additional submission on the existing project.

**Scope**: Same-author only. Two different authors posting about the same open-source project are treated as separate entries.

**Approach**: After project extraction and validation (but before metadata/scoring/URL-fetching LLM calls), generate a preliminary embedding from the raw extracted text and compare it against existing project embeddings by the same author. If similarity exceeds a configurable threshold, treat it as a duplicate.

---

## 1. Database Schema Changes

### New Table: `waywo_project_submissions`

Tracks every time a project appears in a comment, including the original.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-incremented |
| `project_id` | INTEGER FK | References `waywo_projects.id` |
| `comment_id` | INTEGER FK | References `waywo_comments.id` |
| `extracted_text` | TEXT | The raw project text extracted from this specific comment |
| `similarity_score` | REAL | Cosine similarity to the original (1.0 for the first submission) |
| `created_at` | DATETIME | When this submission was recorded |

**Relationships**:
- `WaywoProjectDB` has many `WaywoProjectSubmissionDB`
- `WaywoCommentDB` has many `WaywoProjectSubmissionDB`

### Existing Table Changes

No changes to `waywo_projects`. The existing `source_comment_id` continues to reference the original/first comment. The submissions table provides the full history.

---

## 2. Pipeline Changes

### Current Flow
```
Extract → Validate → Fetch URLs → Generate Metadata → Score → Generate Embedding → Finalize
```

### New Flow
```
Extract → Validate → Check Duplicate → [if new] Fetch URLs → Generate Metadata → Score → Generate Embedding → Finalize
                         ↓
                    [if duplicate] → Link Submission → Finalize (skip all LLM steps)
```

### New Workflow Step: `check_duplicate`

**Placement**: After `validate_project`, before `fetch_urls`.

**Logic**:

1. Look up the comment author (`by` field from the source comment)
2. Generate a preliminary embedding from the raw extracted project text using the embedding service
3. Query existing project embeddings filtered to the same author using vector similarity search
4. If the top match has cosine similarity >= threshold (default: `0.85`):
   - Create a `WaywoProjectSubmission` linking the existing project to this new comment
   - Emit a `DuplicateFoundEvent` which routes to `finalize` (skipping fetch_urls, metadata, scoring, embedding steps)
   - Log: `🔄 Duplicate detected (similarity: X.XX) — linked to project #{id}`
5. If no match or below threshold:
   - Continue pipeline as normal via `DeduplicationPassedEvent` → `fetch_urls`
   - Log: `✅ No duplicate found — proceeding with processing`

### New Workflow Step: On First-Time Project Save

When a project is saved for the first time (not a duplicate), also create its initial `WaywoProjectSubmission` record with `similarity_score=1.0`. This ensures every project has at least one submission, making the submissions list complete.

### New Workflow Events

| Event | From → To | Payload |
|-------|-----------|---------|
| `DeduplicationCheckEvent` | `validate_project` → `check_duplicate` | Validated project data |
| `DuplicateFoundEvent` | `check_duplicate` → `finalize` | Existing project ID, similarity score, submission record |
| `DeduplicationPassedEvent` | `check_duplicate` → `fetch_urls` | Project data (unchanged) |

---

## 3. API Changes

### Existing Endpoint: `GET /api/waywo-projects/{id}`

Add a `submissions` field to the project detail response:

```json
{
  "project": { ... },
  "submissions": [
    {
      "id": 1,
      "comment_id": 123456,
      "comment_by": "username",
      "comment_time": 1699900000,
      "post_id": 789012,
      "post_title": "Ask HN: Who is hiring? (November 2024)",
      "year": 2024,
      "month": 11,
      "extracted_text": "Working on my API tool...",
      "similarity_score": 1.0,
      "hn_comment_url": "https://news.ycombinator.com/item?id=123456",
      "created_at": "2024-11-15T10:30:00Z"
    },
    {
      "id": 2,
      "comment_id": 234567,
      "comment_by": "username",
      "comment_time": 1702500000,
      "post_id": 890123,
      "post_title": "Ask HN: Who is hiring? (December 2024)",
      "year": 2024,
      "month": 12,
      "extracted_text": "Still working on my API tool, now with GraphQL...",
      "similarity_score": 0.91,
      "hn_comment_url": "https://news.ycombinator.com/item?id=234567",
      "created_at": "2024-12-15T10:30:00Z"
    }
  ]
}
```

### Existing Endpoint: `GET /api/waywo-projects`

Add `submission_count` to project list items so the UI can show how many times a project has been posted.

---

## 4. Frontend Changes

### Project Detail Page (`projects/[id].vue`)

Add a new collapsible section **"Submissions"** (between "Similar Projects" and "Original Comment", or replacing "Original Comment" since submissions now covers that):

- Header: "Submissions (N)" with count badge
- Each submission shows:
  - Month/Year badge (e.g., "Nov 2024")
  - Similarity score (if not the original)
  - Truncated extracted text (expandable)
  - Link to HN comment (external link icon)
  - Timestamp

### Project List Page (`projects/index.vue`)

- Add a small badge or indicator on project cards showing submission count when > 1 (e.g., "3x posted")

---

## 5. Configuration

Add to the workflow or environment config:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEDUP_SIMILARITY_THRESHOLD` | `0.85` | Cosine similarity threshold for duplicate detection |

---

## 6. Implementation Order

1. **Database**: Add `waywo_project_submissions` table and SQLAlchemy model
2. **Workflow events**: Add `DeduplicationCheckEvent`, `DuplicateFoundEvent`, `DeduplicationPassedEvent`
3. **Workflow step**: Implement `check_duplicate` step, wire into workflow between validate and fetch_urls
4. **Project save**: Create initial submission record when saving a new project
5. **API**: Add submissions to project detail endpoint, submission_count to list endpoint
6. **Frontend**: Add submissions section to project detail page, badge to project cards
