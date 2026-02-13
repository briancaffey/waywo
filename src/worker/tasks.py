import ast
import asyncio
from datetime import datetime
from pathlib import Path

import yaml

from src.settings import DEDUP_SIMILARITY_THRESHOLD, EMBEDDING_URL, FIRECRAWL_URL, MEDIA_DIR
from src.worker.app import celery_app
from src.db.client import (
    comment_exists,
    delete_projects_for_comment,
    delete_submissions_for_comment,
    get_comment,
    get_unprocessed_comments,
    mark_comment_processed,
    save_comment,
    save_post,
    save_project,
    save_submission,
    update_project_screenshot,
)
from src.clients.screenshot import (
    ScreenshotError,
    capture_screenshot,
    save_screenshot_to_disk,
)
from src.clients.hn import fetch_item
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
    dedup_similarity_threshold: float = 0.85,
) -> dict:
    """Run the WaywoProjectWorkflow asynchronously."""
    from src.workflows.waywo_project_workflow import WaywoProjectWorkflow

    workflow = WaywoProjectWorkflow(
        timeout=180,
        firecrawl_url=firecrawl_url,
        embedding_url=embedding_url,
        dedup_similarity_threshold=dedup_similarity_threshold,
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

    # Delete existing projects and submissions for this comment (allows reprocessing)
    deleted_subs = delete_submissions_for_comment(comment_id)
    deleted_count = delete_projects_for_comment(comment_id)
    if deleted_count > 0 or deleted_subs > 0:
        print(
            f"🗑️ Deleted {deleted_count} project(s) and {deleted_subs} submission(s) "
            f"for comment {comment_id}"
        )

    # Get service URLs from settings
    firecrawl_url = FIRECRAWL_URL
    embedding_url = EMBEDDING_URL

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
                dedup_similarity_threshold=DEDUP_SIMILARITY_THRESHOLD,
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

    # Save only valid projects to database, handle duplicates
    saved_project_ids = []
    skipped_invalid = 0
    duplicates_linked = 0
    for proj_data in projects_data:
        # Handle duplicates — create submission link, skip project save
        if proj_data.get("is_duplicate"):
            existing_id = proj_data["existing_project_id"]
            similarity = proj_data.get("similarity_score", 0.0)
            raw_text = proj_data.get("raw_text", "")
            sub_id = save_submission(
                project_id=existing_id,
                comment_id=comment_id,
                extracted_text=raw_text,
                similarity_score=similarity,
            )
            duplicates_linked += 1
            print(
                f"🔄 Linked duplicate to project #{existing_id} "
                f"(similarity: {similarity:.2f}, submission #{sub_id})"
            )
            continue

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
            source="hn",
            is_valid_project=True,
            invalid_reason=None,
            title=proj_data.get("title", "Untitled"),
            short_description=proj_data.get("short_description", ""),
            description=proj_data.get("description", ""),
            hashtags=proj_data.get("hashtags", []),
            project_urls=proj_data.get("urls", []),
            url_summaries=proj_data.get("url_summaries", {}),
            primary_url=proj_data.get("primary_url"),
            url_contents=proj_data.get("url_contents", {}),
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

        # Create initial submission record for this new project
        save_submission(
            project_id=project_id,
            comment_id=comment_id,
            extracted_text=proj_data.get("raw_text"),
            similarity_score=1.0,
        )

        # Capture screenshot for first URL (non-fatal)
        project_urls = proj_data.get("urls", [])
        if project_urls and project_id:
            try:
                media_dir = MEDIA_DIR
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
        "duplicates_linked": duplicates_linked,
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


def _extract_judge_score(quality: dict, score_name: str, default: int = 5) -> int:
    """Extract an integer score from the NDD judge output.

    Judge columns return: {score_name: {"score": N, "reasoning": "..."}}
    """
    val = quality.get(score_name, default)
    if isinstance(val, dict):
        val = val.get("score", default)
    return max(1, min(10, int(val)))


@celery_app.task(name="generate_ideas", bind=True)
def generate_ideas(
    self,
    num_ideas: int = 5,
    seed_tags: list[str] | None = None,
    creativity: float = 0.85,
) -> dict:
    """Generate synthetic project ideas using NeMo DataDesigner.

    This task:
    1. Builds tag co-occurrence from existing projects
    2. Configures DataDesigner provider + models
    3. Builds and runs the pipeline
    4. Post-processes each row: generate embedding, save to DB

    Args:
        num_ideas: Number of project ideas to generate.
        seed_tags: Optional list of tags to seed generation.
        creativity: Temperature for the creative model (0.1-1.5).

    Returns:
        Summary of generated projects.
    """
    import json
    import nest_asyncio

    nest_asyncio.apply()

    from src.clients.embedding import create_embedding_text, get_single_embedding
    from src.db.projects import get_all_hashtags, get_all_projects, save_project
    from src.ndd_config import build_ndd_models, build_ndd_provider
    from src.ndd_pipeline import build_pipeline_config, build_tag_cooccurrence
    from src.settings import EMBEDDING_URL

    print(f"🧪 Starting NDD generation: {num_ideas} ideas, "
          f"seed_tags={seed_tags}, creativity={creativity}")

    # Update task state to STARTED with progress info
    self.update_state(
        state="STARTED",
        meta={"stage": "building_pipeline", "progress": 0, "total": num_ideas},
    )

    # 1. Build tag co-occurrence from existing projects
    projects = get_all_projects(is_valid=True)
    all_tags = get_all_hashtags()
    tag_cooccurrence = build_tag_cooccurrence(projects)

    # 2. Configure DataDesigner
    provider = build_ndd_provider()
    models = build_ndd_models(creativity=creativity)

    from data_designer.interface.data_designer import DataDesigner

    dd = DataDesigner(
        model_providers=[provider],
        artifact_path="/app/data/ndd_artifacts",
    )

    # 3. Build pipeline config
    config = build_pipeline_config(
        models=models,
        seed_tags=seed_tags,
        tag_cooccurrence=tag_cooccurrence,
        all_tags=all_tags,
    )

    # 4. Run the pipeline
    self.update_state(
        state="STARTED",
        meta={"stage": "generating", "progress": 0, "total": num_ideas},
    )

    print(f"🚀 Running DataDesigner.create() for {num_ideas} records...")
    result = dd.create(config, num_records=num_ideas)
    df = result.load_dataset()
    print(f"✅ Generated {len(df)} records")

    # 5. Post-process and save each row
    self.update_state(
        state="STARTED",
        meta={"stage": "saving", "progress": 0, "total": len(df)},
    )

    saved_ids = []
    errors = []

    for i, (_, row) in enumerate(df.iterrows()):
        try:
            # Parse hashtags — the expression column renders Python list
            # repr with single quotes (e.g. "['ios', 'web']") which
            # json.loads cannot handle, so we use ast.literal_eval.
            hashtags = row.get("hashtags", [])
            if isinstance(hashtags, str):
                try:
                    hashtags = ast.literal_eval(hashtags)
                except (ValueError, SyntaxError):
                    try:
                        hashtags = json.loads(hashtags)
                    except json.JSONDecodeError:
                        hashtags = [hashtags]
            if not isinstance(hashtags, list):
                hashtags = []

            # Parse scores
            quality = row.get("idea_quality", {})
            if isinstance(quality, str):
                try:
                    quality = json.loads(quality)
                except json.JSONDecodeError:
                    quality = {}

            idea_score = _extract_judge_score(quality, "idea_score")
            complexity_score = _extract_judge_score(quality, "complexity_score")

            now = datetime.utcnow()
            project = WaywoProject(
                id=0,
                source_comment_id=None,
                source="nemo_data_designer",
                is_valid_project=True,
                title=str(row.get("title", "Untitled")),
                short_description=str(row.get("short_description", "")),
                description=str(row.get("description", "")),
                hashtags=hashtags,
                project_urls=[],
                url_summaries={},
                primary_url=None,
                url_contents={},
                idea_score=idea_score,
                complexity_score=complexity_score,
                workflow_logs=["Generated by NeMo DataDesigner"],
                created_at=now,
                processed_at=now,
            )

            # Generate embedding
            embedding = None
            try:
                emb_text = create_embedding_text(
                    title=project.title,
                    description=project.description,
                    hashtags=project.hashtags,
                )
                embedding = asyncio.run(
                    get_single_embedding(emb_text, embedding_url=EMBEDDING_URL)
                )
            except Exception as e:
                print(f"⚠️ Embedding failed for row {i} (non-fatal): {e}")

            project_id = save_project(project, embedding=embedding)
            saved_ids.append(project_id)
            has_emb = "with embedding" if embedding else "without embedding"
            print(f"💾 Saved project {project_id}: {project.title} ({has_emb})")

            # Update progress
            self.update_state(
                state="STARTED",
                meta={
                    "stage": "saving",
                    "progress": i + 1,
                    "total": len(df),
                },
            )

        except Exception as e:
            print(f"❌ Failed to save row {i}: {e}")
            errors.append({"row": i, "error": str(e)})

    print(f"🎉 NDD generation complete: {len(saved_ids)} saved, {len(errors)} errors")

    return {
        "status": "success",
        "num_requested": num_ideas,
        "num_generated": len(df),
        "num_saved": len(saved_ids),
        "project_ids": saved_ids,
        "errors": errors,
        "seed_tags": seed_tags or [],
    }
