<template>
  <div>
    <!-- Thread Sidebar -->
    <ChatThreadSidebar
      :is-open="sidebarOpen"
      :threads="chatThreads.threads.value"
      :active-thread-id="chatThreads.activeThreadId.value"
      :loading="chatThreads.loading.value"
      @close="sidebarOpen = false"
      @new-thread="startNewThread"
      @select-thread="selectThread"
      @delete-thread="handleDeleteThread"
    />

    <!-- Main Chat Area -->
    <div
      class="flex flex-col min-h-[calc(100vh-4rem)]"
      :class="sidebarOpen ? 'lg:ml-72' : ''"
    >
      <!-- Chat Header -->
      <div class="border-b bg-background/80 backdrop-blur-sm px-4 py-3 flex items-center gap-3 sticky top-16 z-10">
        <Button variant="ghost" size="icon" class="h-8 w-8" @click="sidebarOpen = !sidebarOpen">
          <Icon name="lucide:panel-left" class="h-4 w-4" />
        </Button>
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <div class="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center flex-shrink-0">
            <Icon name="lucide:bot" class="h-4 w-4 text-primary" />
          </div>
          <div class="min-w-0">
            <h1 class="text-sm font-semibold truncate">
              {{ activeThread ? activeThread.title : 'Project Assistant' }}
            </h1>
            <p class="text-xs text-muted-foreground">Ask about HN projects</p>
          </div>
        </div>
        <Button v-if="messages.length > 0" variant="ghost" size="sm" class="gap-1.5" @click="startNewThread">
          <Icon name="lucide:plus" class="h-4 w-4" />
          <span class="hidden sm:inline text-xs">New Chat</span>
        </Button>
      </div>

      <!-- Messages / Welcome -->
      <div class="flex-1 flex flex-col pb-24">
        <!-- Welcome State -->
        <div v-if="messages.length === 0" class="flex-1 flex flex-col items-center justify-center px-4">
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center mb-6">
            <Icon name="lucide:sparkles" class="h-8 w-8 text-primary" />
          </div>
          <h2 class="text-2xl font-bold mb-2 text-center">What would you like to know?</h2>
          <p class="text-muted-foreground text-center max-w-md mb-10">
            Explore thousands of projects from Hacker News "What are you working on?" threads.
          </p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
            <button
              v-for="(suggestion, i) in suggestionCards"
              :key="i"
              class="group text-left p-4 rounded-xl border bg-card hover:bg-accent/50 hover:border-primary/20 transition-all duration-200 cursor-pointer"
              @click="askSuggestion(suggestion.query)"
            >
              <div class="flex items-start gap-3">
                <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                  <Icon :name="suggestion.icon" class="h-4 w-4 text-primary" />
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-medium">{{ suggestion.label }}</p>
                  <p class="text-xs text-muted-foreground mt-0.5">{{ suggestion.description }}</p>
                </div>
              </div>
            </button>
          </div>
        </div>

        <!-- Message List -->
        <div v-else class="max-w-3xl mx-auto px-4 py-6 space-y-6">
          <div v-for="(message, index) in messages" :key="index">
            <!-- User Message -->
            <div v-if="message.role === 'user'" class="flex justify-end">
              <div class="bg-primary text-primary-foreground rounded-2xl rounded-br-md px-4 py-2.5 max-w-[85%] shadow-sm">
                <p class="text-sm leading-relaxed">{{ message.content }}</p>
              </div>
            </div>

            <!-- Assistant Message -->
            <div v-else class="flex gap-3">
              <div class="w-8 h-8 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                <Icon name="lucide:bot" class="h-4 w-4 text-primary" />
              </div>
              <div class="flex-1 min-w-0 max-w-[85%]">
                <!-- Agent Steps -->
                <ChatAgentSteps
                  v-if="message.agentSteps && message.agentSteps.length > 0"
                  :steps="message.agentSteps"
                />

                <!-- Message Content -->
                <div
                  v-if="message.content"
                  class="bg-muted/50 border border-border/50 rounded-2xl rounded-tl-md px-4 py-3 prose prose-sm max-w-none dark:prose-invert"
                  v-html="renderMarkdown(message.content)"
                />

                <!-- Streaming indicator -->
                <div v-if="message.isStreaming && !message.content" class="bg-muted/50 border border-border/50 rounded-2xl rounded-tl-md px-4 py-4">
                  <div class="flex items-center gap-2.5">
                    <div class="flex gap-1">
                      <span class="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <span class="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <span class="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" />
                    </div>
                    <span class="text-muted-foreground text-sm">Thinking...</span>
                  </div>
                </div>

                <!-- RAG indicator -->
                <div v-if="message.ragTriggered" class="mt-1.5">
                  <Badge variant="outline" class="text-[10px] gap-1 font-normal">
                    <Icon name="lucide:database" class="h-3 w-3" />
                    RAG Enhanced
                  </Badge>
                </div>

                <!-- Source Projects -->
                <div v-if="message.sourceProjects && message.sourceProjects.length > 0" class="mt-3">
                  <p class="text-xs text-muted-foreground mb-2 font-medium">
                    Sources ({{ message.sourceProjects.length }} project{{ message.sourceProjects.length === 1 ? '' : 's' }}):
                  </p>
                  <div class="flex flex-wrap gap-1.5">
                    <NuxtLink
                      v-for="project in message.sourceProjects"
                      :key="project.id"
                      :to="`/projects/${project.id}`"
                      class="inline-flex items-center gap-1.5 text-xs bg-background border rounded-lg px-2.5 py-1.5 hover:border-primary/30 hover:bg-accent/50 transition-all duration-150"
                    >
                      <Icon name="lucide:lightbulb" class="h-3 w-3 text-amber-500" />
                      <span class="truncate max-w-[150px]">{{ project.title }}</span>
                      <Badge variant="secondary" class="text-[10px] px-1 font-mono">
                        {{ (project.similarity * 100).toFixed(0) }}%
                      </Badge>
                    </NuxtLink>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div ref="messagesEnd" />
        </div>
      </div>

      <!-- Sticky Input Area -->
      <div class="sticky bottom-0 border-t bg-background/80 backdrop-blur-lg px-4 py-4">
        <form @submit.prevent="sendMessage" class="max-w-3xl mx-auto">
          <div class="flex gap-2 items-center">
            <Input
              v-model="inputMessage"
              type="text"
              placeholder="Ask about projects..."
              class="flex-1 h-11 rounded-xl"
              :disabled="isLoading"
              @keydown.enter.prevent="sendMessage"
            />
            <Button
              type="submit"
              size="icon"
              class="h-11 w-11 rounded-xl shrink-0"
              :disabled="isLoading || !inputMessage.trim()"
            >
              <Icon
                :name="isLoading ? 'lucide:loader-2' : 'lucide:arrow-up'"
                :class="isLoading ? 'animate-spin' : ''"
                class="h-4 w-4"
              />
            </Button>
          </div>
          <p class="text-[11px] text-muted-foreground/50 text-center mt-2">
            Powered by RAG with semantic search over project descriptions
          </p>
        </form>
      </div>

      <!-- Error Alert -->
      <Alert v-if="error" variant="destructive" class="mx-4 mb-4 max-w-3xl">
        <Icon name="lucide:alert-circle" class="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import type { SourceProject, ChatMessage, AgentStep } from '~/types/models'
import type { ChatThread } from '~/types/chat'

marked.setOptions({
  breaks: true,
  gfm: true
})

useHead({
  title: 'Project Assistant - waywo',
  meta: [
    { name: 'description', content: 'Chat with an AI assistant about projects from What are you working on.' }
  ]
})

const config = useRuntimeConfig()

// Thread management
const chatThreads = useChatThreads()
const sidebarOpen = ref(false)

// Chat state
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesEnd = ref<HTMLElement | null>(null)
const activeThreadId = ref<string | null>(null)

const activeThread = computed(() => {
  if (!activeThreadId.value) return null
  return chatThreads.threads.value.find((t) => t.id === activeThreadId.value) ?? null
})

const suggestionCards = [
  {
    icon: 'lucide:cpu',
    label: 'AI & Machine Learning',
    description: 'What AI projects are people building?',
    query: 'What AI projects are people building?',
  },
  {
    icon: 'lucide:wrench',
    label: 'Developer Tools',
    description: 'Show me useful productivity tools',
    query: 'Show me productivity tools',
  },
  {
    icon: 'lucide:code-2',
    label: 'Open Source',
    description: 'Discover community-driven projects',
    query: 'Any interesting open source projects?',
  },
  {
    icon: 'lucide:rocket',
    label: 'SaaS Ideas',
    description: 'Explore popular business ideas',
    query: 'What SaaS ideas are popular?',
  },
]

// Load threads on mount
onMounted(() => {
  chatThreads.fetchThreads()
})

function scrollToBottom() {
  nextTick(() => {
    messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

async function sendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''
  error.value = null

  // Create thread on first message if none active
  let threadId = activeThreadId.value
  if (!threadId) {
    const thread = await chatThreads.createThread()
    if (!thread) {
      error.value = 'Failed to create conversation thread.'
      return
    }
    threadId = thread.id
    activeThreadId.value = threadId
    chatThreads.setActive(threadId)
  }

  // Add user message to UI
  messages.value.push({
    role: 'user',
    content: userMessage
  })
  scrollToBottom()

  // Add placeholder assistant message
  const assistantIdx = messages.value.length
  messages.value.push({
    role: 'assistant',
    content: '',
    agentSteps: [],
    isStreaming: true,
  })
  scrollToBottom()

  isLoading.value = true

  try {
    const response = await fetch(
      `${config.public.apiBase}/api/chat/threads/${threadId}/message/stream`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, top_k: 5 }),
      }
    )

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Parse SSE events from buffer
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? '' // Keep incomplete line in buffer

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ') && eventType) {
          try {
            const data = JSON.parse(line.slice(6))
            handleSSEEvent(assistantIdx, eventType, data)
          } catch {
            // Skip malformed data
          }
          eventType = ''
        }
      }
    }

    // Refresh thread title (may have been auto-titled)
    setTimeout(() => {
      if (threadId) {
        chatThreads.refreshThread(threadId)
      }
    }, 3000)
  } catch (err: any) {
    console.error('Chat failed:', err)
    error.value = err.message || 'Failed to get response. Please try again.'
    const msg = messages.value[assistantIdx]
    if (msg && !msg.content) {
      msg.content = 'Sorry, I encountered an error processing your request. Please try again.'
    }
  } finally {
    // Ensure streaming flag is cleared
    const msg = messages.value[assistantIdx]
    if (msg) msg.isStreaming = false
    isLoading.value = false
    scrollToBottom()
  }
}

function handleSSEEvent(msgIdx: number, eventType: string, data: Record<string, any>) {
  const msg = messages.value[msgIdx]
  if (!msg) return

  switch (eventType) {
    case 'thinking':
      if (!msg.agentSteps) msg.agentSteps = []
      msg.agentSteps.push({
        type: 'thought',
        text: data.thought,
      })
      scrollToBottom()
      break

    case 'tool_call':
      if (!msg.agentSteps) msg.agentSteps = []
      msg.agentSteps.push({
        type: 'tool_call',
        tool: data.tool,
        input: data.input,
      })
      scrollToBottom()
      break

    case 'tool_result':
      if (!msg.agentSteps) msg.agentSteps = []
      msg.agentSteps.push({
        type: 'tool_result',
        tool: data.tool,
        summary: data.result_summary,
        projects_found: data.projects_found,
      })
      scrollToBottom()
      break

    case 'answer_token':
      msg.content += data.token
      scrollToBottom()
      break

    case 'answer_done':
      msg.content = data.full_text
      msg.sourceProjects = data.source_projects as SourceProject[]
      msg.ragTriggered = data.source_projects?.length > 0
      msg.isStreaming = false
      scrollToBottom()
      break

    case 'done':
      msg.isStreaming = false
      break

    case 'error':
      console.error('Agent error:', data.error)
      break
  }
}

function askSuggestion(suggestion: string) {
  inputMessage.value = suggestion
  sendMessage()
}

async function selectThread(threadId: string) {
  activeThreadId.value = threadId
  chatThreads.setActive(threadId)
  sidebarOpen.value = false

  // Load thread with turns
  try {
    const thread = await $fetch<ChatThread>(
      `${config.public.apiBase}/api/chat/threads/${threadId}`
    )

    // Convert turns to ChatMessage format
    messages.value = thread.turns.map((turn) => ({
      role: turn.role,
      content: turn.text,
      sourceProjects: (turn.source_projects ?? []) as unknown as SourceProject[],
      ragTriggered: turn.rag_triggered ?? undefined,
      agentSteps: (turn.agent_steps ?? []) as unknown as AgentStep[],
    }))
    scrollToBottom()
  } catch (err) {
    console.error('Failed to load thread:', err)
    error.value = 'Failed to load conversation.'
  }
}

function startNewThread() {
  activeThreadId.value = null
  chatThreads.setActive(null)
  messages.value = []
  error.value = null
  sidebarOpen.value = false
}

async function handleDeleteThread(threadId: string) {
  const ok = await chatThreads.deleteThread(threadId)
  if (ok && activeThreadId.value === threadId) {
    startNewThread()
  }
}

function renderMarkdown(content: string): string {
  if (!content) return ''
  return marked.parse(content) as string
}
</script>
