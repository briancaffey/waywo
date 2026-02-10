<template>
  <!-- Toggle button (always visible on right edge) -->
  <button
    class="fixed right-0 top-1/2 -translate-y-1/2 z-40 bg-muted border border-r-0 rounded-l-md px-1.5 py-3 hover:bg-accent transition-colors"
    :class="{ 'right-[400px]': isOpen }"
    @click="toggle"
    title="Toggle debug panel"
  >
    <Icon
      :name="isOpen ? 'lucide:panel-right-close' : 'lucide:panel-right-open'"
      class="h-4 w-4 text-muted-foreground"
    />
  </button>

  <!-- Panel -->
  <Transition name="slide">
    <div
      v-if="isOpen"
      class="fixed right-0 top-0 bottom-0 w-[400px] z-30 bg-background border-l flex flex-col"
    >
      <!-- Header -->
      <div class="border-b px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div class="flex items-center gap-2">
          <Icon name="lucide:bug" class="h-4 w-4 text-muted-foreground" />
          <span class="text-sm font-semibold">Debug</span>
          <Badge variant="secondary" class="text-xs">
            {{ eventCount }}
          </Badge>
        </div>
        <div class="flex items-center gap-1">
          <Button variant="ghost" size="sm" class="h-7 px-2" @click="clearEvents" title="Clear events">
            <Icon name="lucide:trash-2" class="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="sm" class="h-7 px-2" @click="autoScroll = !autoScroll" :title="autoScroll ? 'Auto-scroll ON' : 'Auto-scroll OFF'">
            <Icon :name="autoScroll ? 'lucide:arrow-down-to-line' : 'lucide:pause'" class="h-3.5 w-3.5" :class="autoScroll ? 'text-primary' : 'text-muted-foreground'" />
          </Button>
        </div>
      </div>

      <!-- Metrics bar -->
      <div v-if="hasMetrics" class="border-b px-4 py-2 flex-shrink-0">
        <div class="flex gap-3 text-xs">
          <div v-if="metrics.sttDurationMs != null" class="flex items-center gap-1">
            <span class="text-blue-400 font-medium">STT</span>
            <span class="text-muted-foreground">{{ metrics.sttDurationMs }}ms</span>
          </div>
          <div v-if="metrics.llmDurationMs != null" class="flex items-center gap-1">
            <span class="text-purple-400 font-medium">LLM</span>
            <span class="text-muted-foreground">{{ metrics.llmDurationMs }}ms</span>
          </div>
          <div v-if="metrics.ttsDurationMs != null" class="flex items-center gap-1">
            <span class="text-green-400 font-medium">TTS</span>
            <span class="text-muted-foreground">{{ metrics.ttsDurationMs }}ms</span>
          </div>
          <div v-if="metrics.totalDurationMs != null" class="flex items-center gap-1 ml-auto">
            <span class="font-medium">Total</span>
            <span class="text-muted-foreground">{{ metrics.totalDurationMs }}ms</span>
          </div>
        </div>
      </div>

      <!-- Category filters -->
      <div class="border-b px-4 py-2 flex gap-1.5 flex-wrap flex-shrink-0">
        <button
          v-for="(cfg, cat) in categoryConfig"
          :key="cat"
          class="text-xs px-2 py-0.5 rounded-full border transition-colors"
          :class="enabledCategories.has(cat as DebugCategory)
            ? `${cfg.bgColor} ${cfg.color} border-current`
            : 'text-muted-foreground border-transparent opacity-40'"
          @click="toggleCategory(cat as DebugCategory)"
        >
          {{ cfg.label }}
        </button>
      </div>

      <!-- Event log -->
      <ScrollArea class="flex-1" ref="scrollAreaRef">
        <div class="p-2 space-y-0.5">
          <div
            v-for="event in filteredEvents"
            :key="event.id"
            class="text-xs font-mono px-2 py-1 rounded hover:bg-muted/50 group"
          >
            <!-- Timestamp + category + event name -->
            <div class="flex items-center gap-1.5">
              <span class="text-muted-foreground/60 tabular-nums">
                {{ formatTime(event.ts) }}
              </span>
              <span
                class="font-semibold uppercase text-[10px] tracking-wider"
                :class="getCategoryColor(event.category)"
              >
                {{ event.category }}
              </span>
              <span class="text-foreground/80">
                {{ event.event }}
              </span>
            </div>

            <!-- Data (collapsed by default, show key details inline) -->
            <div
              v-if="hasRelevantData(event)"
              class="mt-0.5 pl-[72px] text-muted-foreground/70 truncate"
            >
              {{ formatData(event) }}
            </div>
          </div>

          <!-- Empty state -->
          <div v-if="filteredEvents.length === 0" class="text-center py-8">
            <Icon name="lucide:radio" class="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
            <p class="text-xs text-muted-foreground/50">No events yet</p>
          </div>
        </div>
      </ScrollArea>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import type { DebugEvent, DebugCategory, TurnMetrics } from '~/types/voice'
import { CATEGORY_CONFIG } from '~/composables/useDebugPanel'

const props = defineProps<{
  filteredEvents: DebugEvent[]
  eventCount: number
  isOpen: boolean
  autoScroll: boolean
  enabledCategories: ReadonlySet<DebugCategory>
  metrics: TurnMetrics
}>()

const emit = defineEmits<{
  toggle: []
  clear: []
  toggleCategory: [cat: DebugCategory]
  'update:autoScroll': [val: boolean]
}>()

const categoryConfig = CATEGORY_CONFIG

const scrollAreaRef = ref<{ $el: HTMLElement } | null>(null)

const hasMetrics = computed(() => {
  const m = props.metrics
  return m.sttDurationMs != null || m.llmDurationMs != null || m.ttsDurationMs != null
})

// Local re-emitters
function toggle() { emit('toggle') }
function clearEvents() { emit('clear') }
function toggleCategory(cat: DebugCategory) { emit('toggleCategory', cat) }

const autoScroll = computed({
  get: () => props.autoScroll,
  set: (val: boolean) => emit('update:autoScroll', val),
})

function getViewport(): HTMLElement | null {
  const el = scrollAreaRef.value?.$el as HTMLElement | undefined
  return el?.querySelector('[data-slot="scroll-area-viewport"]') ?? null
}

// Auto-scroll to bottom on new events
watch(
  () => props.filteredEvents.length,
  () => {
    if (!props.autoScroll) return
    nextTick(() => {
      const viewport = getViewport()
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    })
  }
)

function getCategoryColor(cat: DebugCategory): string {
  return CATEGORY_CONFIG[cat]?.color ?? 'text-muted-foreground'
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }) + '.' + String(d.getMilliseconds()).padStart(3, '0')
  } catch {
    return ts
  }
}

function hasRelevantData(event: DebugEvent): boolean {
  const d = event.data
  if (!d || Object.keys(d).length === 0) return false
  // Skip events where the only data is the transition target (already shown)
  if (event.event === 'transition' && Object.keys(d).length === 1 && 'to' in d) return false
  return true
}

function formatData(event: DebugEvent): string {
  const d = event.data
  const parts: string[] = []

  // Show the most useful fields for each event type
  if ('text' in d && typeof d.text === 'string') {
    const t = d.text as string
    parts.push(t.length > 60 ? t.slice(0, 60) + '...' : t)
  }
  if ('duration_ms' in d) parts.push(`${d.duration_ms}ms`)
  if ('connect_ms' in d) parts.push(`connect: ${d.connect_ms}ms`)
  if ('audio_bytes' in d) parts.push(`${((d.audio_bytes as number) / 1024).toFixed(1)}KB`)
  if ('bytes' in d) parts.push(`${((d.bytes as number) / 1024).toFixed(1)}KB`)
  if ('output_chars' in d) parts.push(`${d.output_chars} chars`)
  if ('input_chars' in d) parts.push(`${d.input_chars} chars`)
  if ('count' in d) parts.push(`${d.count} chunks`)
  if ('total_bytes' in d) parts.push(`${((d.total_bytes as number) / 1024).toFixed(1)}KB`)
  if ('output_preview' in d && !('text' in d)) {
    const p = d.output_preview as string
    parts.push(p.length > 60 ? p.slice(0, 60) + '...' : p)
  }
  if ('turn_total_ms' in d) parts.push(`total: ${d.turn_total_ms}ms`)
  if ('stt_ms' in d && event.event === 'transition') parts.push(`stt: ${d.stt_ms}ms`)
  if ('llm_ms' in d && event.event === 'transition') parts.push(`llm: ${d.llm_ms}ms`)
  if ('tts_ms' in d && event.event === 'transition') parts.push(`tts: ${d.tts_ms}ms`)
  if ('error' in d) parts.push(`error: ${d.error}`)
  if ('reason' in d) parts.push(`reason: ${d.reason}`)
  if ('to' in d && event.event === 'transition' && parts.length > 0) {
    // Prepend the target state
    return `→ ${d.to}  ${parts.join(' · ')}`
  }
  if ('to' in d && event.event === 'transition') {
    return `→ ${d.to}`
  }

  return parts.join(' · ')
}
</script>

<style scoped>
.slide-enter-active,
.slide-leave-active {
  transition: transform 0.2s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
