export interface WaywoProject {
  id: number
  source_comment_id: number | null
  source: string | null
  is_valid_project: boolean
  invalid_reason: string | null
  title: string
  short_description: string
  description: string
  hashtags: string[]
  project_urls: string[]
  url_summaries: Record<string, string>
  idea_score: number
  complexity_score: number
  created_at: string
  processed_at: string
  workflow_logs: string[]
  // Present in list/detail responses but not search results
  primary_url?: string | null
  is_bookmarked?: boolean
  screenshot_path?: string | null
  comment_time?: number | null
  // Present only in detail response
  url_contents?: Record<string, string>
}

export interface WaywoComment {
  id: number
  type: string
  by: string | null
  time: number | null
  text: string | null
  parent: number | null
  kids: number[] | null
}

export interface WaywoPost {
  id: number
  title: string | null
  year: number | null
  month: number | null
}

export interface WaywoPostSummary {
  id: number
  title: string | null
  year: number | null
  month: number | null
  score: number | null
  comment_count: number
  descendants: number | null
}

export interface SearchResult {
  project: WaywoProject
  similarity: number
  rerank_score?: number
}

export interface SearchStats {
  total_projects: number
  projects_with_embeddings: number
  embedding_coverage: number
}

export interface SourceProject {
  id: number
  title: string
  short_description: string
  similarity: number
  hashtags: string[]
  idea_score: number
  complexity_score: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sourceProjects?: SourceProject[]
  ragTriggered?: boolean
}

export interface DatabaseStats {
  posts_count: number
  comments_count: number
  projects_count: number
  processed_comments_count: number
  valid_projects_count: number
  projects_with_embeddings_count: number
  redis_keys_count: number
  redis_memory_used: string
  redis_connected: boolean
}

export interface ServiceHealth {
  status: 'healthy' | 'unhealthy'
  url: string
  error?: string
  configured_model?: string
  available_models?: string[]
  device?: string
  queue_size?: number
  voices?: number | string
}

export interface ServicesHealth {
  llm: ServiceHealth
  embedder: ServiceHealth
  reranker: ServiceHealth
  invokeai: ServiceHealth
  tts: ServiceHealth
  stt: ServiceHealth
}

export interface GenerateIdeasRequest {
  num_ideas: number
  seed_tags?: string[]
  creativity: number
}

export interface GenerateIdeasResponse {
  task_id: string
  num_requested: number
  seed_tags: string[]
}

export interface GenerateIdeasStatus {
  task_id: string
  state: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE'
  stage?: string
  progress?: number
  total?: number
  result?: {
    status: string
    num_requested: number
    num_generated: number
    num_saved: number
    project_ids: number[]
    errors: { row: number; error: string }[]
    seed_tags: string[]
  }
  error?: string
}

export interface ResultMessage {
  success: boolean
  message: string
  details?: any
}

export interface ClusterMapProject {
  id: number
  title: string
  short_description: string
  hashtags: string[]
  idea_score: number
  complexity_score: number
  cluster_label: number | null
  umap_x: number
  umap_y: number
}

export interface WorkflowStep {
  step: number
  name: string
  title: string
  description: string
  workflow: string
  input_event: string
  output_event: string
  prompt_template: string | null
  template_variables: string[]
}

export interface WaywoVideoSegment {
  id: number
  video_id: number
  segment_index: number
  segment_type: string
  narration_text: string
  scene_description: string
  image_prompt: string
  visual_style: string
  transition: string
  audio_path: string | null
  audio_duration_seconds: number | null
  image_path: string | null
  image_name: string | null
  transcription: Record<string, any> | null
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface WaywoVideo {
  id: number
  project_id: number
  version: number
  video_title: string | null
  video_style: string | null
  script_json: Record<string, any> | null
  voice_name: string | null
  status: string
  error_message: string | null
  video_path: string | null
  thumbnail_path: string | null
  duration_seconds: number | null
  width: number
  height: number
  workflow_logs: string[]
  view_count: number
  is_favorited: boolean
  created_at: string
  completed_at: string | null
  segments: WaywoVideoSegment[]
}
