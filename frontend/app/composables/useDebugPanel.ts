import type {
  DebugEvent,
  DebugCategory,
  TurnMetrics,
  ServerDebugMessage,
} from '~/types/voice'

const MAX_EVENTS = 500

/** Category display configuration */
export const CATEGORY_CONFIG: Record<DebugCategory, { label: string; color: string; bgColor: string }> = {
  stt: { label: 'STT', color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
  llm: { label: 'LLM', color: 'text-purple-400', bgColor: 'bg-purple-500/10' },
  tts: { label: 'TTS', color: 'text-green-400', bgColor: 'bg-green-500/10' },
  audio: { label: 'Audio', color: 'text-orange-400', bgColor: 'bg-orange-500/10' },
  ws: { label: 'WS', color: 'text-gray-400', bgColor: 'bg-gray-500/10' },
  state: { label: 'State', color: 'text-yellow-400', bgColor: 'bg-yellow-500/10' },
}

/**
 * Composable for collecting and managing debug events from the voice chat WebSocket.
 */
export function useDebugPanel() {
  const events = ref<DebugEvent[]>([])
  const isOpen = ref(false)
  const enabledCategories = ref<Set<DebugCategory>>(
    new Set(['stt', 'llm', 'tts', 'audio', 'ws', 'state'])
  )
  const autoScroll = ref(true)

  let nextId = 0

  // ── Current turn timing tracking ────────────────────────────────
  const currentTurnMetrics = ref<TurnMetrics>({
    sttDurationMs: null,
    llmDurationMs: null,
    ttsDurationMs: null,
    totalDurationMs: null,
  })

  // ── Computed ────────────────────────────────────────────────────
  const filteredEvents = computed(() =>
    events.value.filter(e => enabledCategories.value.has(e.category))
  )

  const eventCount = computed(() => events.value.length)

  // ── Actions ─────────────────────────────────────────────────────

  function addEvent(msg: ServerDebugMessage) {
    const event: DebugEvent = {
      id: nextId++,
      category: msg.category,
      event: msg.event,
      data: msg.data,
      ts: msg.ts,
      localTs: Date.now(),
    }

    events.value.push(event)

    // Trim buffer if too large
    if (events.value.length > MAX_EVENTS) {
      events.value = events.value.slice(-MAX_EVENTS)
    }

    // Extract timing metrics from state transitions
    _updateMetrics(event)
  }

  function _updateMetrics(event: DebugEvent) {
    if (event.category !== 'state' || event.event !== 'transition') return

    const data = event.data
    // The final transition back to idle has all the timing info
    if (data.to === 'idle' && data.turn_total_ms != null) {
      currentTurnMetrics.value = {
        sttDurationMs: (data.stt_ms as number) ?? null,
        llmDurationMs: (data.llm_ms as number) ?? null,
        ttsDurationMs: (data.tts_ms as number) ?? null,
        totalDurationMs: (data.turn_total_ms as number) ?? null,
      }
    } else if (data.to === 'listening') {
      // Reset metrics when a new turn starts
      currentTurnMetrics.value = {
        sttDurationMs: null,
        llmDurationMs: null,
        ttsDurationMs: null,
        totalDurationMs: null,
      }
    }
  }

  function clearEvents() {
    events.value = []
    nextId = 0
    currentTurnMetrics.value = {
      sttDurationMs: null,
      llmDurationMs: null,
      ttsDurationMs: null,
      totalDurationMs: null,
    }
  }

  function toggleCategory(cat: DebugCategory) {
    const s = new Set(enabledCategories.value)
    if (s.has(cat)) {
      s.delete(cat)
    } else {
      s.add(cat)
    }
    enabledCategories.value = s
  }

  function toggle() {
    isOpen.value = !isOpen.value
  }

  return {
    events: readonly(events),
    filteredEvents,
    eventCount,
    isOpen,
    autoScroll,
    enabledCategories: readonly(enabledCategories),
    currentTurnMetrics: readonly(currentTurnMetrics),

    addEvent,
    clearEvents,
    toggleCategory,
    toggle,
  }
}
