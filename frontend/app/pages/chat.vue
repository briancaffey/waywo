<template>
  <div class="flex h-screen">
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
    <div class="flex-1 flex flex-col" :class="sidebarOpen ? 'lg:ml-72' : ''">
      <!-- Header -->
      <div class="border-b px-4 py-3 flex items-center gap-3">
        <Button variant="ghost" size="icon" class="h-8 w-8" @click="sidebarOpen = !sidebarOpen">
          <Icon name="lucide:panel-left" class="h-4 w-4" />
        </Button>
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Icon name="lucide:bot" class="h-4 w-4 text-primary" />
          </div>
          <div class="min-w-0">
            <h1 class="text-sm font-semibold truncate">
              {{ activeThread ? activeThread.title : 'Project Assistant' }}
            </h1>
            <p class="text-xs text-muted-foreground">Ask about HN projects</p>
          </div>
        </div>
        <Button v-if="messages.length > 0" variant="ghost" size="icon" class="h-8 w-8" @click="startNewThread">
          <Icon name="lucide:plus" class="h-4 w-4" />
        </Button>
      </div>

      <!-- Messages -->
      <div ref="messagesContainer" class="flex-1 overflow-y-auto p-6 space-y-4">
        <!-- Welcome Message -->
        <div v-if="messages.length === 0" class="text-center py-16">
          <Icon name="lucide:message-square" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p class="text-muted-foreground mb-2">Ask me anything about the projects!</p>
          <p class="text-sm text-muted-foreground">Examples:</p>
          <div class="flex flex-wrap justify-center gap-2 mt-3">
            <Button
              v-for="suggestion in suggestions"
              :key="suggestion"
              variant="outline"
              size="sm"
              @click="askSuggestion(suggestion)"
            >
              {{ suggestion }}
            </Button>
          </div>
        </div>

        <!-- Message List -->
        <div v-for="(message, index) in messages" :key="index" class="flex gap-3">
          <!-- User Message -->
          <div v-if="message.role === 'user'" class="flex gap-3 justify-end w-full">
            <div class="bg-primary text-primary-foreground rounded-lg px-4 py-2 max-w-[80%]">
              <p>{{ message.content }}</p>
            </div>
            <div class="w-8 h-8 rounded-full bg-muted flex items-center justify-center flex-shrink-0">
              <Icon name="lucide:user" class="h-4 w-4" />
            </div>
          </div>

          <!-- Assistant Message -->
          <div v-else class="flex gap-3 w-full">
            <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Icon name="lucide:bot" class="h-4 w-4 text-primary" />
            </div>
            <div class="flex-1 max-w-[80%]">
              <div class="bg-muted rounded-lg px-4 py-2 prose prose-sm max-w-none" v-html="renderMarkdown(message.content)">
              </div>

              <!-- RAG indicator -->
              <div v-if="message.ragTriggered" class="mt-1">
                <Badge variant="outline" class="text-[10px] gap-1">
                  <Icon name="lucide:database" class="h-3 w-3" />
                  RAG
                </Badge>
              </div>

              <!-- Source Projects -->
              <div v-if="message.sourceProjects && message.sourceProjects.length > 0" class="mt-3">
                <p class="text-xs text-muted-foreground mb-2">
                  Based on {{ message.sourceProjects.length }} relevant project{{ message.sourceProjects.length === 1 ? '' : 's' }}:
                </p>
                <div class="flex flex-wrap gap-2">
                  <a
                    v-for="project in message.sourceProjects"
                    :key="project.id"
                    :href="`/projects/${project.id}`"
                    class="inline-flex items-center gap-1 text-xs bg-background border rounded-md px-2 py-1 hover:border-primary transition-colors"
                  >
                    <Icon name="lucide:lightbulb" class="h-3 w-3" />
                    {{ project.title }}
                    <Badge variant="secondary" class="text-[10px] px-1">
                      {{ (project.similarity * 100).toFixed(0) }}%
                    </Badge>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Loading Indicator -->
        <div v-if="isLoading" class="flex gap-3">
          <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Icon name="lucide:bot" class="h-4 w-4 text-primary" />
          </div>
          <div class="bg-muted rounded-lg px-4 py-2">
            <div class="flex items-center gap-2">
              <Icon name="lucide:loader-2" class="h-4 w-4 animate-spin" />
              <span class="text-muted-foreground">Thinking...</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="border-t p-4">
        <form @submit.prevent="sendMessage" class="flex gap-3 max-w-4xl mx-auto">
          <Input
            v-model="inputMessage"
            type="text"
            placeholder="Ask about projects..."
            class="flex-1"
            :disabled="isLoading"
            @keydown.enter.prevent="sendMessage"
          />
          <Button type="submit" :disabled="isLoading || !inputMessage.trim()">
            <Icon
              :name="isLoading ? 'lucide:loader-2' : 'lucide:send'"
              :class="isLoading ? 'animate-spin' : ''"
              class="h-4 w-4"
            />
          </Button>
        </form>
      </div>

      <!-- Error Alert -->
      <Alert v-if="error" variant="destructive" class="mx-4 mb-4">
        <Icon name="lucide:alert-circle" class="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'
import type { SourceProject, ChatMessage } from '~/types/models'
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
const messagesContainer = ref<HTMLElement | null>(null)
const activeThreadId = ref<string | null>(null)

const activeThread = computed(() => {
  if (!activeThreadId.value) return null
  return chatThreads.threads.value.find((t) => t.id === activeThreadId.value) ?? null
})

const suggestions = [
  "What AI projects are people building?",
  "Show me productivity tools",
  "Any interesting open source projects?",
  "What SaaS ideas are popular?"
]

// Load threads on mount
onMounted(() => {
  chatThreads.fetchThreads()
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
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

  isLoading.value = true

  try {
    const response = await $fetch<{
      response: string
      source_projects: SourceProject[]
      thread_id: string
      rag_triggered: boolean
      llm_duration_ms: number
    }>(`${config.public.apiBase}/api/chat/threads/${threadId}/message`, {
      method: 'POST',
      body: {
        message: userMessage,
        top_k: 5
      }
    })

    messages.value.push({
      role: 'assistant',
      content: response.response,
      sourceProjects: response.source_projects,
      ragTriggered: response.rag_triggered,
    })

    // Refresh thread title (may have been auto-titled)
    setTimeout(() => {
      if (threadId) {
        chatThreads.refreshThread(threadId)
      }
    }, 3000)
  } catch (err: any) {
    console.error('Chat failed:', err)
    error.value = err.data?.detail || 'Failed to get response. Please try again.'
    messages.value.push({
      role: 'assistant',
      content: 'Sorry, I encountered an error processing your request. Please try again.'
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
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
  return marked.parse(content) as string
}
</script>
