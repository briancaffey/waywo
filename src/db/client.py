"""
Database client facade - re-exports all DB operations for backwards compatibility.

Individual modules:
- src.db.posts: Post CRUD operations
- src.db.comments: Comment CRUD operations
- src.db.projects: Project CRUD, bookmarks, similar projects
- src.db.search: Semantic search, vector similarity
- src.db.stats: Admin stats, database management
"""

from src.db.posts import (  # noqa: F401
    get_all_post_ids,
    get_post,
    save_post,
)

from src.db.comments import (  # noqa: F401
    comment_exists,
    get_all_comment_ids,
    get_all_comments,
    get_comment,
    get_comment_count_for_post,
    get_comments_for_post,
    get_total_comment_count,
    get_unprocessed_comments,
    is_comment_processed,
    mark_comment_processed,
    save_comment,
)

from src.db.projects import (  # noqa: F401
    compute_umap_clusters,
    delete_project,
    delete_projects_for_comment,
    get_all_hashtags,
    get_all_projects,
    get_bookmarked_count,
    get_cluster_map_data,
    get_project,
    get_projects_for_comment,
    get_total_project_count,
    save_project,
    toggle_bookmark,
    update_project_screenshot,
)

from src.db.search import (  # noqa: F401
    get_projects_with_embeddings_count,
    get_similar_projects,
    semantic_search,
)

from src.db.stats import (  # noqa: F401
    get_database_stats,
    reset_all_data,
)

from src.db.videos import (  # noqa: F401
    append_video_workflow_log,
    get_all_videos,
    create_segments,
    create_video,
    delete_segment,
    delete_video,
    get_segment,
    get_segments_for_video,
    get_video,
    get_video_count,
    get_video_feed,
    get_videos_for_project,
    increment_video_view_count,
    toggle_video_favorite,
    update_segment_audio,
    update_segment_image,
    update_segment_image_prompt,
    update_segment_narration,
    update_segment_status,
    update_video_output,
    update_video_script,
    update_video_status,
)
