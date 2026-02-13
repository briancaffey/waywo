<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <WaywoPageHeader
        icon="lucide:audio-waveform"
        title="Voice Mode"
        description="Talk to the AI assistant using your voice"
      />

      <!-- Controls bar -->
      <div class="flex items-center justify-center gap-4 mb-8">
        <!-- Thread sidebar toggle -->
        <Button
          variant="ghost"
          size="sm"
          @click="sidebarOpen = !sidebarOpen"
          class="gap-1.5"
        >
          <Icon name="lucide:panel-left" class="h-4 w-4" />
          <span class="text-xs">Threads</span>
        </Button>
        <Separator orientation="vertical" class="h-4" />
        <!-- Connection status -->
        <div class="flex items-center gap-2 text-sm">
          <div
            class="w-2 h-2 rounded-full"
            :class="{
              'bg-green-500': connectionState === 'connected',
              'bg-yellow-500 animate-pulse': connectionState === 'connecting',
              'bg-red-500': connectionState === 'error',
              'bg-gray-400': connectionState === 'disconnected',
            }"
          />
          <span class="text-muted-foreground capitalize">{{ connectionState }}</span>
        </div>
        <Separator orientation="vertical" class="h-4" />
        <!-- Show text toggle -->
        <Button
          variant="ghost"
          size="sm"
          @click="showText = !showText"
          class="gap-1.5"
        >
          <Icon :name="showText ? 'lucide:eye' : 'lucide:eye-off'" class="h-4 w-4" />
          <span class="text-xs">{{ showText ? 'Text on' : 'Text off' }}</span>
        </Button>
        <Separator orientation="vertical" class="h-4" />
        <!-- Voice selector -->
        <Select v-model="selectedVoice" @update:model-value="onVoiceChange">
          <SelectTrigger class="w-[200px] h-8 text-xs">
            <SelectValue placeholder="Default voice" />
          </SelectTrigger>
          <SelectContent class="max-h-[300px]">
            <SelectItem value="__default__">Default voice</SelectItem>
            <template v-for="(group, lang) in voicesByLanguage" :key="lang">
              <SelectSeparator />
              <SelectGroup>
                <SelectLabel class="text-[10px] uppercase tracking-wider text-muted-foreground">{{ lang }}</SelectLabel>
                <SelectItem
                  v-for="voice in group"
                  :key="voice.id"
                  :value="voice.id"
                >
                  {{ voice.label }}
                </SelectItem>
              </SelectGroup>
            </template>
          </SelectContent>
        </Select>
        <Separator orientation="vertical" class="h-4" />
        <!-- Debug panel toggle -->
        <Button
          variant="ghost"
          size="sm"
          @click="debugPanel.toggle()"
          class="gap-1.5"
        >
          <Icon name="lucide:bug" class="h-4 w-4" />
          <span class="text-xs">Debug</span>
          <Badge v-if="debugPanel.eventCount.value > 0" variant="secondary" class="text-[10px] px-1 min-w-[20px]">
            {{ debugPanel.eventCount.value }}
          </Badge>
        </Button>
      </div>

      <!-- Conversation area -->
      <Card class="mb-6">
        <ScrollArea class="h-[400px]">
          <div ref="messagesContainer" class="p-6 space-y-4">
            <!-- Persisted + live messages -->
            <template v-if="showText && messages.length > 0">
              <div
                v-for="(msg, i) in messages"
                :key="i"
                :class="msg.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'"
              >
                <div
                  :class="[
                    'rounded-2xl px-4 py-2 max-w-[80%]',
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground rounded-br-md'
                      : 'bg-muted rounded-bl-md',
                  ]"
                >
                  <p class="text-sm">{{ msg.text }}</p>
                </div>
                <div class="flex items-center gap-1.5 mt-0.5 px-1">
                  <button
                    v-if="msg.audioUrl"
                    @click="togglePlayback(i)"
                    class="text-muted-foreground hover:text-foreground transition-colors p-0.5"
                  >
                    <Icon
                      :name="playingIndex === i ? 'lucide:pause' : 'lucide:play'"
                      class="h-3 w-3"
                    />
                  </button>
                  <span class="text-[10px] text-muted-foreground">
                    {{ formatTime(msg.ts) }}
                  </span>
                </div>
              </div>
            </template>

            <!-- Partial transcription while listening (live, not yet in messages) -->
            <div
              v-if="voiceState === 'listening' && partialTranscription"
              class="flex justify-end"
            >
              <div class="bg-primary/20 text-primary rounded-2xl rounded-br-md px-4 py-2 max-w-[80%] italic">
                <p class="text-sm">{{ partialTranscription }}</p>
              </div>
            </div>

            <!-- Agent steps during processing -->
            <div v-if="voiceState === 'processing' && agentSteps.length > 0" class="flex flex-col items-start">
              <div class="bg-muted/50 rounded-2xl rounded-bl-md px-4 py-3 max-w-[80%]">
                <ChatAgentSteps :steps="agentSteps" />
                <div class="flex items-center gap-2 mt-1">
                  <Icon name="lucide:loader-2" class="h-3 w-3 animate-spin text-muted-foreground" />
                  <span class="text-xs text-muted-foreground">Processing...</span>
                </div>
              </div>
            </div>

            <!-- Empty state -->
            <div
              v-if="showText && voiceState === 'idle' && messages.length === 0"
              class="text-center py-8"
            >
              <Icon name="lucide:mic" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p class="text-muted-foreground">Press and hold the button below to speak</p>
            </div>
          </div>
        </ScrollArea>
      </Card>

      <!-- Voice button -->
      <div class="flex justify-center mb-6">
        <VoiceButton
          :state="voiceState"
          :disabled="connectionState !== 'connected'"
          @press="startListening"
          @release="stopListening"
        />
      </div>

      <!-- Error message -->
      <Alert v-if="errorMessage" variant="destructive" class="mb-4">
        <Icon name="lucide:alert-circle" class="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{{ errorMessage }}</AlertDescription>
      </Alert>
    </div>

    <!-- Thread sidebar -->
    <VoiceThreadSidebar
      :is-open="sidebarOpen"
      :threads="threadManager.threads.value"
      :active-thread-id="threadManager.activeThreadId.value"
      :loading="threadManager.loading.value"
      @close="sidebarOpen = false"
      @new-thread="onNewThread"
      @select-thread="onSelectThread"
      @delete-thread="onDeleteThread"
    />

    <!-- Debug panel -->
    <VoiceDebugPanel
      :filtered-events="debugPanel.filteredEvents.value"
      :event-count="debugPanel.eventCount.value"
      :is-open="debugPanel.isOpen.value"
      :auto-scroll="debugPanel.autoScroll.value"
      :enabled-categories="debugPanel.enabledCategories.value"
      :metrics="debugPanel.currentTurnMetrics.value"
      @toggle="debugPanel.toggle()"
      @clear="debugPanel.clearEvents()"
      @toggle-category="debugPanel.toggleCategory"
      @update:auto-scroll="debugPanel.autoScroll.value = $event"
    />
  </div>
</template>

<script setup lang="ts">
useHead({
  title: 'Voice Mode - waywo',
  meta: [
    { name: 'description', content: 'Talk to the AI assistant using your voice.' },
  ],
})

interface VoiceOption {
  id: string
  language: string
  speaker: string
  emotion: string | null
  label: string
}

const showText = ref(true)
const sidebarOpen = ref(false)
const voices = ref<VoiceOption[]>([])
const selectedVoice = ref('__default__')

const voicesByLanguage = computed(() => {
  const groups: Record<string, VoiceOption[]> = {}
  for (const v of voices.value) {
    if (!groups[v.language]) groups[v.language] = []
    groups[v.language]!.push(v)
  }
  const sorted: Record<string, VoiceOption[]> = {}
  for (const lang of Object.keys(groups).sort((a, b) => {
    if (a === 'EN-US') return -1
    if (b === 'EN-US') return 1
    return a.localeCompare(b)
  })) {
    sorted[lang] = groups[lang]!
  }
  return sorted
})

const debugPanel = useDebugPanel()
const threadManager = useVoiceThreads()
const messagesContainer = ref<HTMLElement | null>(null)

// ── Audio playback per message ──
const playingIndex = ref<number | null>(null)
let currentAudio: HTMLAudioElement | null = null

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function togglePlayback(index: number) {
  const msg = messages.value[index]
  if (!msg?.audioUrl) return

  if (playingIndex.value === index) {
    currentAudio?.pause()
    playingIndex.value = null
    return
  }

  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }

  currentAudio = new Audio(msg.audioUrl)
  currentAudio.onended = () => {
    playingIndex.value = null
    currentAudio = null
  }
  currentAudio.play()
  playingIndex.value = index
}

const {
  voiceState,
  connectionState,
  partialTranscription,
  errorMessage,
  messages,
  threadId,
  agentSteps,
  connect,
  disconnect,
  startListening,
  stopListening,
  setVoice,
  loadThreadHistory,
} = useVoiceChat({
  onDebugEvent: (msg) => debugPanel.addEvent(msg),
})

// Auto-scroll messages when new ones arrive
watch(messages, () => {
  nextTick(() => {
    if (!messagesContainer.value) return
    const viewport = messagesContainer.value.closest('[data-slot="scroll-area-viewport"]')
    if (viewport) {
      viewport.scrollTop = viewport.scrollHeight
    }
  })
}, { deep: true })

// When we get a threadId from the WS, mark it active and refresh the list
watch(threadId, (id) => {
  if (id) {
    threadManager.setActive(id)
    // Refresh thread list to pick up the new thread
    threadManager.fetchThreads()
  }
})

// Periodically refresh the active thread title (picks up auto-title)
let titleRefreshTimer: ReturnType<typeof setInterval> | null = null
watch(threadId, (id) => {
  if (titleRefreshTimer) clearInterval(titleRefreshTimer)
  if (id) {
    // Check for title updates a few times after first turn
    let checks = 0
    titleRefreshTimer = setInterval(() => {
      checks++
      threadManager.refreshThread(id)
      if (checks >= 5) {
        clearInterval(titleRefreshTimer!)
        titleRefreshTimer = null
      }
    }, 3000)
  }
})

function onVoiceChange(value: string | number | boolean | Record<string, string> | null) {
  const v = String(value ?? '__default__')
  setVoice(v === '__default__' ? null : v)
}

async function onNewThread() {
  disconnect()
  connect() // No thread_id → backend creates new thread
  sidebarOpen.value = false
}

async function onSelectThread(id: string) {
  if (id === threadManager.activeThreadId.value) {
    sidebarOpen.value = false
    return
  }
  disconnect()
  await loadThreadHistory(id)
  connect(id)
  threadManager.setActive(id)
  sidebarOpen.value = false
}

async function onDeleteThread(id: string) {
  const wasActive = id === threadManager.activeThreadId.value
  await threadManager.deleteThread(id)
  if (wasActive) {
    disconnect()
    connect() // Start fresh
  }
}

const config = useRuntimeConfig()

async function fetchVoices() {
  try {
    const data = await $fetch<{ voices: VoiceOption[] }>(`${config.public.apiBase}/api/voice/voices`)
    if (data.voices && Array.isArray(data.voices)) {
      voices.value = data.voices
    }
  } catch (err) {
    console.error('Failed to fetch voices:', err)
  }
}

onMounted(() => {
  connect()
  fetchVoices()
  threadManager.fetchThreads()
})

onUnmounted(() => {
  if (titleRefreshTimer) clearInterval(titleRefreshTimer)
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
})
</script>
