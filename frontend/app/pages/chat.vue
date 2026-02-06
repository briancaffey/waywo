<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:bot" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Project Assistant</h1>
        <p class="text-xl text-muted-foreground">
          Ask questions about projects from "What are you working on?"
        </p>
      </div>

      <!-- Chat Container -->
      <Card class="mb-4">
        <!-- Messages -->
        <div ref="messagesContainer" class="h-[500px] overflow-y-auto p-6 space-y-4">
          <!-- Welcome Message -->
          <div v-if="messages.length === 0" class="text-center py-8">
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
          <form @submit.prevent="sendMessage" class="flex gap-3">
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
          <p class="text-xs text-muted-foreground mt-2 text-center">
            Powered by RAG with semantic search over project descriptions
          </p>
        </div>
      </Card>

      <!-- Error Alert -->
      <Alert v-if="error" variant="destructive" class="mb-4">
        <Icon name="lucide:alert-circle" class="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <!-- Clear Chat Button -->
      <div v-if="messages.length > 0" class="text-center">
        <Button variant="outline" size="sm" @click="clearChat">
          <Icon name="lucide:trash-2" class="mr-2 h-4 w-4" />
          Clear Chat
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

interface SourceProject {
  id: number
  title: string
  short_description: string
  similarity: number
  hashtags: string[]
  idea_score: number
  complexity_score: number
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sourceProjects?: SourceProject[]
}

// Set page metadata
useHead({
  title: 'Project Assistant - waywo',
  meta: [
    { name: 'description', content: 'Chat with an AI assistant about projects from What are you working on.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const messages = ref<ChatMessage[]>([])
const inputMessage = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)
const messagesContainer = ref<HTMLElement | null>(null)

// Suggestion prompts
const suggestions = [
  "What AI projects are people building?",
  "Show me productivity tools",
  "Any interesting open source projects?",
  "What SaaS ideas are popular?"
]

// Scroll to bottom of messages
function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// Send message to chatbot
async function sendMessage() {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMessage = inputMessage.value.trim()
  inputMessage.value = ''
  error.value = null

  // Add user message
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
      query: string
      projects_found: number
    }>(`${config.public.apiBase}/api/waywo-chatbot`, {
      method: 'POST',
      body: {
        query: userMessage,
        top_k: 5
      }
    })

    // Add assistant message
    messages.value.push({
      role: 'assistant',
      content: response.response,
      sourceProjects: response.source_projects
    })
  } catch (err: any) {
    console.error('Chat failed:', err)
    error.value = err.data?.detail || 'Failed to get response. Please try again.'

    // Add error message to chat
    messages.value.push({
      role: 'assistant',
      content: 'Sorry, I encountered an error processing your request. Please try again.'
    })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

// Ask a suggestion
function askSuggestion(suggestion: string) {
  inputMessage.value = suggestion
  sendMessage()
}

// Clear chat history
function clearChat() {
  messages.value = []
  error.value = null
}

// Render markdown to HTML
function renderMarkdown(content: string): string {
  return marked.parse(content) as string
}
</script>
