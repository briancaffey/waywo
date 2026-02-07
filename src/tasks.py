import asyncio
import os
from datetime import datetime
from pathlib import Path

import yaml

from src.celery_app import celery_app
from src.db_client import (
    comment_exists,
    delete_projects_for_comment,
    get_comment,
    get_unprocessed_comments,
    mark_comment_processed,
    save_comment,
    save_post,
    save_project,
    update_project_screenshot,
)
from src.screenshot_client import (
    ScreenshotError,
    capture_screenshot,
    save_screenshot_to_disk,
)
from src.hn_client import fetch_item
from src.models import WaywoComment, WaywoPost, WaywoProject, WaywoYamlEntry


def load_waywo_yaml() -> list[WaywoYamlEntry]:
    """Load and parse the waywo.yml file."""
    yaml_path = Path(__file__).parent.parent / "waywo.yml"
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return [WaywoYamlEntry(**entry) for entry in data]


@celery_app.task(name="process_waywo_posts")
def process_waywo_posts(
    limit_posts: int | None = None,
    limit_comments: int | None = None,
) -> dict:
    """
    Process all WaywoPost entries from waywo.yml.

    Args:
        limit_posts: Maximum number of posts to process (for testing).
        limit_comments: Maximum comments per post (passed to process_waywo_post).

    Returns:
        Summary of processing results.
    """
    entries = load_waywo_yaml()

    if limit_posts is not None:
        entries = entries[:limit_posts]

    task_ids = []
    for entry in entries:
        task = process_waywo_post.delay(
            post_id=entry.id,
            year=entry.year,
            month=entry.month,
            limit_comments=limit_comments,
        )
        task_ids.append(task.id)

    return {
        "status": "queued",
        "posts_queued": len(entries),
        "task_ids": task_ids,
    }


@celery_app.task(name="process_waywo_post")
def process_waywo_post(
    post_id: int,
    year: int | None = None,
    month: int | None = None,
    limit_comments: int | None = None,
) -> dict:
    """
    Process a single WaywoPost and its top-level comments.

    Args:
        post_id: The HN item ID for the post.
        year: The year of the post (from waywo.yml).
        month: The month of the post (from waywo.yml).
        limit_comments: Maximum number of comments to fetch (for testing).

    Returns:
        Summary of processing results.
    """
    post_data = fetch_item(post_id)
    if post_data is None:
        return {"status": "error", "message": f"Could not fetch post {post_id}"}

    post = WaywoPost(
        **post_data,
        year=year,
        month=month,
    )
    save_post(post)

    kids = post.kids or []
    if limit_comments is not None:
        kids = kids[:limit_comments]

    comments_saved = 0
    comments_skipped = 0
    for comment_id in kids:
        # Skip if comment already exists
        if comment_exists(comment_id):
            comments_skipped += 1
            continue

        comment_data = fetch_item(comment_id)
        if comment_data is None:
            continue

        comment = WaywoComment(**comment_data)
        save_comment(comment)
        comments_saved += 1

    return {
        "status": "success",
        "post_id": post_id,
        "title": post.title,
        "total_kids": len(post.kids) if post.kids else 0,
        "comments_saved": comments_saved,
        "comments_skipped": comments_skipped,
    }


async def run_workflow_async(
    comment_id: int,
    comment_text: str,
    comment_author: str | None,
    comment_time: int | None,
    parent_post_id: int | None,
    firecrawl_url: str,
    embedding_url: str,
) -> dict:
    """Run the WaywoProjectWorkflow asynchronously."""
    from src.workflows.waywo_project_workflow import WaywoProjectWorkflow

    workflow = WaywoProjectWorkflow(
        timeout=180,
        firecrawl_url=firecrawl_url,
        embedding_url=embedding_url,
    )
    return await workflow.run(
        comment_id=comment_id,
        comment_text=comment_text,
        comment_author=comment_author,
        comment_time=comment_time,
        parent_post_id=parent_post_id,
    )


@celery_app.task(name="process_waywo_comment", bind=True, max_retries=3)
def process_waywo_comment(self, comment_id: int) -> dict:
    """
    Process a single comment through the WaywoProjectWorkflow.

    This task:
    1. Fetches the comment from the database
    2. Deletes any existing projects for this comment
    3. Runs the comment through the LlamaIndex workflow
    4. Saves the resulting projects to the database
    5. Marks the comment as processed

    Args:
        comment_id: The HN comment ID to process.

    Returns:
        Summary of processing results.
    """
    import nest_asyncio

    # Apply nest_asyncio to allow nested event loops in Celery worker
    nest_asyncio.apply()

    print(f"🔄 Starting to process comment {comment_id}")

    # Fetch the comment
    comment = get_comment(comment_id)
    if comment is None:
        return {
            "status": "error",
            "comment_id": comment_id,
            "message": "Comment not found in database",
        }

    # Delete existing projects for this comment (allows reprocessing)
    deleted_count = delete_projects_for_comment(comment_id)
    if deleted_count > 0:
        print(
            f"🗑️ Deleted {deleted_count} existing project(s) for comment {comment_id}"
        )

    # Get service URLs from environment
    firecrawl_url = os.environ.get("FIRECRAWL_URL", "http://localhost:3002")
    embedding_url = os.environ.get("EMBEDDING_URL", "http://192.168.5.96:8000")

    try:
        # Run async workflow using asyncio.run() with nest_asyncio
        result = asyncio.run(
            run_workflow_async(
                comment_id=comment.id,
                comment_text=comment.text or "",
                comment_author=comment.by,
                comment_time=comment.time,
                parent_post_id=comment.parent,
                firecrawl_url=firecrawl_url,
                embedding_url=embedding_url,
            )
        )
    except Exception as e:
        print(f"❌ Workflow failed for comment {comment_id}: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2**self.request.retries)

    # Extract projects from result
    projects_data = result.get("projects", [])
    logs = result.get("logs", [])

    print(
        f"✅ Workflow completed for comment {comment_id}, found {len(projects_data)} project(s)"
    )

    # Save only valid projects to database
    saved_project_ids = []
    skipped_invalid = 0
    for proj_data in projects_data:
        # Skip invalid projects - don't create records for them
        if not proj_data.get("is_valid", False):
            invalid_reason = proj_data.get("invalid_reason", "unknown")
            print(
                f"⏭️ Skipping invalid project for comment {comment_id}: {invalid_reason}"
            )
            skipped_invalid += 1
            continue

        project = WaywoProject(
            id=0,  # Will be assigned by database
            source_comment_id=comment_id,
            is_valid_project=True,
            invalid_reason=None,
            title=proj_data.get("title", "Untitled"),
            short_description=proj_data.get("short_description", ""),
            description=proj_data.get("description", ""),
            hashtags=proj_data.get("hashtags", []),
            project_urls=proj_data.get("urls", []),
            url_summaries=proj_data.get("url_summaries", {}),
            idea_score=proj_data.get("idea_score", 5),
            complexity_score=proj_data.get("complexity_score", 5),
            workflow_logs=proj_data.get("workflow_logs", logs),
            created_at=datetime.utcnow(),
            processed_at=datetime.utcnow(),
        )
        # Extract embedding from workflow result (may be None)
        embedding = proj_data.get("embedding")
        project_id = save_project(project, embedding=embedding)
        saved_project_ids.append(project_id)
        has_embedding = "with embedding" if embedding else "without embedding"
        print(f"💾 Saved project {project_id}: {project.title} ({has_embedding})")

        # Capture screenshot for first URL (non-fatal)
        project_urls = proj_data.get("urls", [])
        if project_urls and project_id:
            try:
                media_dir = os.environ.get("MEDIA_DIR", "/app/media")
                image_bytes = asyncio.run(capture_screenshot(url=project_urls[0]))
                screenshot_path = save_screenshot_to_disk(
                    image_bytes, project_id, media_dir=media_dir
                )
                update_project_screenshot(project_id, screenshot_path)
                print(f"📸 Screenshot saved for project {project_id}")
            except ScreenshotError as e:
                print(f"📸 Screenshot failed for project {project_id} (non-fatal): {e}")
            except Exception as e:
                print(f"📸 Screenshot error for project {project_id} (non-fatal): {e}")

    # Mark comment as processed
    mark_comment_processed(comment_id)

    return {
        "status": "success",
        "comment_id": comment_id,
        "projects_extracted": len(projects_data),
        "project_ids": saved_project_ids,
        "valid_projects": len(saved_project_ids),
        "invalid_skipped": skipped_invalid,
    }


@celery_app.task(name="process_waywo_comments")
def process_waywo_comments(
    limit: int | None = None,
    comment_ids: list[int] | None = None,
) -> dict:
    """
    Process multiple comments through the WaywoProjectWorkflow.

    This task dispatches process_waywo_comment tasks for each comment.
    By default, processes all unprocessed comments.

    Args:
        limit: Maximum number of comments to process.
        comment_ids: Specific comment IDs to process (ignores 'processed' flag).

    Returns:
        Summary of queued tasks.
    """
    print("🚀 Starting batch comment processing")

    if comment_ids:
        # Process specific comments
        comments_to_process = []
        for cid in comment_ids:
            comment = get_comment(cid)
            if comment:
                comments_to_process.append(comment)
        print(f"📋 Processing {len(comments_to_process)} specified comment(s)")
    else:
        # Get unprocessed comments
        comments_to_process = get_unprocessed_comments(limit=limit)
        print(f"📋 Found {len(comments_to_process)} unprocessed comment(s)")

    if not comments_to_process:
        return {
            "status": "no_work",
            "message": "No comments to process",
            "comments_queued": 0,
        }

    # Queue individual tasks for each comment
    task_ids = []
    for comment in comments_to_process:
        task = process_waywo_comment.delay(comment_id=comment.id)
        task_ids.append(task.id)
        print(f"📤 Queued task for comment {comment.id}")

    return {
        "status": "queued",
        "comments_queued": len(comments_to_process),
        "task_ids": task_ids,
    }
