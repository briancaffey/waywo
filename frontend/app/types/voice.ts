/** Voice chat WebSocket message types and state */

export type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking'

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

export type DebugCategory = 'stt' | 'llm' | 'tts' | 'audio' | 'ws' | 'state' | 'rag' | 'agent'

/** Messages sent from client to server */
export interface ClientMessage {
  type: 'start_listening' | 'stop_listening' | 'cancel' | 'set_voice'
  voice?: string | null
}

/** Messages received from server */
export interface ServerStateMessage {
  type: 'state'
  state: VoiceState
  thread_id?: string
}

export interface ServerSttPartialMessage {
  type: 'stt_partial'
  text: string
}

export interface ServerSttFinalMessage {
  type: 'stt_final'
  text: string
}

export interface ServerLlmCompleteMessage {
  type: 'llm_complete'
  text: string
}

export interface ServerTurnCompleteMessage {
  type: 'turn_complete'
}

export interface ServerErrorMessage {
  type: 'error'
  message: string
}

export interface ServerDebugMessage {
  type: 'debug'
  category: DebugCategory
  event: string
  data: Record<string, unknown>
  ts: string
}

export interface ServerAgentThinkingMessage {
  type: 'agent_thinking'
  thought: string
}

export interface ServerAgentToolCallMessage {
  type: 'agent_tool_call'
  tool: string
  input: string
}

export interface ServerAgentToolResultMessage {
  type: 'agent_tool_result'
  tool: string
  projects_found: number
}

export type ServerMessage =
  | ServerStateMessage
  | ServerSttPartialMessage
  | ServerSttFinalMessage
  | ServerLlmCompleteMessage
  | ServerTurnCompleteMessage
  | ServerErrorMessage
  | ServerDebugMessage
  | ServerAgentThinkingMessage
  | ServerAgentToolCallMessage
  | ServerAgentToolResultMessage

/** Voice thread from the API */
export interface VoiceThread {
  id: string
  title: string
  system_prompt: string | null
  created_at: string
  updated_at: string
  turns: readonly VoiceTurnRecord[]
}

/** A persisted voice turn */
export interface VoiceTurnRecord {
  id: number
  thread_id: string
  role: 'user' | 'assistant'
  text: string
  audio_duration_seconds: number | null
  tts_voice: string | null
  token_count: number | null
  llm_duration_ms: number | null
  tts_duration_ms: number | null
  stt_duration_ms: number | null
  created_at: string
}

/** Debug event stored in the panel */
export interface DebugEvent {
  id: number
  category: DebugCategory
  event: string
  data: Record<string, unknown>
  ts: string
  localTs: number
}

/** Timing metrics for a single voice turn */
export interface TurnMetrics {
  sttDurationMs: number | null
  llmDurationMs: number | null
  ttsDurationMs: number | null
  totalDurationMs: number | null
}
