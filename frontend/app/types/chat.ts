/** Text chat thread and turn types */

export interface ChatThread {
  id: string
  title: string
  system_prompt: string | null
  created_at: string
  updated_at: string
  turns: readonly ChatTurnRecord[]
}

export interface ChatTurnRecord {
  id: number
  thread_id: string
  role: 'user' | 'assistant'
  text: string
  source_projects: Record<string, unknown>[]
  llm_duration_ms: number | null
  rag_triggered: boolean | null
  agent_steps: Record<string, unknown>[] | null
  created_at: string
}
