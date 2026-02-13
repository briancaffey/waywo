<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <WaywoPageHeader
        icon="lucide:message-square"
        title="Comments"
        description='Browse project submissions from "What are you working on?" posts'
      >
        <div v-if="postId">
          <Badge variant="outline" class="text-sm">
            Filtered by Post ID: {{ postId }}
            <button @click="clearFilter" class="ml-2 hover:text-destructive">
              <Icon name="lucide:x" class="h-3 w-3" />
            </button>
          </Badge>
        </div>
      </WaywoPageHeader>

      <!-- Stats & Processing Card -->
      <Card class="p-6 mb-8">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p class="text-sm text-muted-foreground">Total Comments</p>
            <p class="text-3xl font-bold">{{ total }}</p>
          </div>
          <div class="flex gap-3">
            <Button variant="outline" @click="fetchComments" :disabled="isLoading">
              <Icon
                :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
                :class="isLoading ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Refresh
            </Button>
            <div class="flex items-center gap-2">
              <input
                v-model="maxComments"
                type="number"
                min="1"
                placeholder="All"
                class="w-20 h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
              <Button @click="processComments" :disabled="isProcessing">
                <Icon
                  :name="isProcessing ? 'lucide:loader-2' : 'lucide:sparkles'"
                  :class="isProcessing ? 'animate-spin' : ''"
                  class="mr-2 h-4 w-4"
                />
                {{ isProcessing ? 'Processing...' : 'Extract Projects' }}
              </Button>
            </div>
          </div>
        </div>

        <!-- Processing Status Messages -->
        <Alert v-if="processSuccess" class="mt-4 border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950">
          <Icon name="lucide:check-circle" class="h-4 w-4 text-green-600 dark:text-green-400" />
          <AlertTitle class="text-green-800 dark:text-green-200">Task Queued</AlertTitle>
          <AlertDescription class="text-green-700 dark:text-green-300">
            Project extraction task has been queued. Task ID: {{ taskId }}
          </AlertDescription>
        </Alert>

        <Alert v-if="processError" variant="destructive" class="mt-4">
          <Icon name="lucide:alert-circle" class="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{{ processError }}</AlertDescription>
        </Alert>
      </Card>

      <!-- Comments List -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <div v-else-if="fetchError" class="text-center py-12">
        <Icon name="lucide:alert-circle" class="h-12 w-12 text-destructive mx-auto mb-4" />
        <p class="text-destructive">{{ fetchError }}</p>
        <Button variant="outline" @click="fetchComments" class="mt-4">
          Try Again
        </Button>
      </div>

      <div v-else-if="comments.length === 0" class="text-center py-12">
        <Icon name="lucide:inbox" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p class="text-muted-foreground">No comments stored yet</p>
        <p class="text-sm text-muted-foreground mt-2">
          Process some posts first to fetch comments
        </p>
        <a href="/posts">
          <Button class="mt-4">
            Go to Posts
            <Icon name="lucide:arrow-right" class="ml-2 h-4 w-4" />
          </Button>
        </a>
      </div>

      <div v-else class="space-y-4">
        <Card
          v-for="comment in comments"
          :key="comment.id"
          class="p-6 cursor-pointer hover:border-primary/50 transition-colors"
          @click="viewComment(comment.id)"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
              <div class="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <span class="text-sm font-medium text-primary">
                  {{ comment.by?.charAt(0).toUpperCase() || '?' }}
                </span>
              </div>
              <div>
                <a
                  :href="`https://news.ycombinator.com/user?id=${comment.by}`"
                  target="_blank"
                  class="font-medium hover:underline"
                  @click.stop
                >
                  {{ comment.by || 'Unknown' }}
                </a>
                <p class="text-sm text-muted-foreground">
                  {{ formatUnixTime(comment.time) }}
                </p>
              </div>
            </div>
            <a
              :href="`https://news.ycombinator.com/item?id=${comment.id}`"
              target="_blank"
              class="text-muted-foreground hover:text-primary"
              @click.stop
            >
              <Icon name="lucide:external-link" class="h-4 w-4" />
            </a>
          </div>

          <div
            class="prose prose-sm max-w-none dark:prose-invert"
            v-html="comment.text || '<em>No content</em>'"
            @click.stop
          />

          <div class="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
            <span>
              ID: {{ comment.id }}
              <span v-if="comment.kids?.length" class="ml-2">
                | {{ comment.kids.length }} {{ comment.kids.length === 1 ? 'reply' : 'replies' }}
              </span>
            </span>
            <div class="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                @click.stop="processSingleComment(comment.id)"
                :disabled="processingCommentId === comment.id"
              >
                <Icon
                  :name="processingCommentId === comment.id ? 'lucide:loader-2' : 'lucide:sparkles'"
                  :class="processingCommentId === comment.id ? 'animate-spin' : ''"
                  class="mr-1 h-3 w-3"
                />
                {{ processingCommentId === comment.id ? 'Processing...' : 'Process' }}
              </Button>
              <a
                :href="`/projects?comment_id=${comment.id}`"
                class="text-primary hover:underline flex items-center gap-1"
                @click.stop
              >
                Projects
                <Icon name="lucide:arrow-right" class="h-3 w-3" />
              </a>
              <a
                :href="`/comments/${comment.id}`"
                class="text-primary hover:underline flex items-center gap-1"
                @click.stop
              >
                Details
                <Icon name="lucide:arrow-right" class="h-3 w-3" />
              </a>
            </div>
          </div>
        </Card>

        <!-- Pagination -->
        <div class="flex items-center justify-between pt-6">
          <Button
            variant="outline"
            @click="prevPage"
            :disabled="offset === 0"
          >
            <Icon name="lucide:chevron-left" class="mr-2 h-4 w-4" />
            Previous
          </Button>

          <span class="text-sm text-muted-foreground">
            Showing {{ offset + 1 }} - {{ Math.min(offset + limit, total) }} of {{ total }}
          </span>

          <Button
            variant="outline"
            @click="nextPage"
            :disabled="offset + limit >= total"
          >
            Next
            <Icon name="lucide:chevron-right" class="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WaywoComment } from '~/types/models'

// Set page metadata
useHead({
  title: 'Comments - waywo',
  meta: [
    { name: 'description', content: 'Browse project submissions from What are you working on posts.' }
  ]
})

const config = useRuntimeConfig()
const route = useRoute()

// Get post_id from query params
const postId = computed(() => {
  const id = route.query.post_id
  return id ? Number(id) : null
})

// Reactive state
const comments = ref<WaywoComment[]>([])
const total = ref(0)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)

const limit = ref(20)
const offset = ref(0)

// Processing state (batch)
const isProcessing = ref(false)
const processError = ref<string | null>(null)
const processSuccess = ref(false)
const taskId = ref<string | null>(null)

// Max comments for batch processing
const maxComments = ref<string>('')

// Processing state (single comment)
const processingCommentId = ref<number | null>(null)

// Fetch comments from API
async function fetchComments() {
  isLoading.value = true
  fetchError.value = null

  try {
    const params: Record<string, number | undefined> = {
      limit: limit.value,
      offset: offset.value
    }
    if (postId.value) {
      params.post_id = postId.value
    }

    const response = await $fetch<{
      comments: WaywoComment[]
      total: number
      limit: number
      offset: number
    }>(`${config.public.apiBase}/api/waywo-comments`, { params })
    comments.value = response.comments
    total.value = response.total
  } catch (err) {
    console.error('Failed to fetch comments:', err)
    fetchError.value = 'Failed to fetch comments. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
}

// View comment detail
function viewComment(commentId: number) {
  window.location.href = `/comments/${commentId}`
}

// Process a single comment
async function processSingleComment(commentId: number) {
  if (processingCommentId.value === commentId) return

  processingCommentId.value = commentId

  try {
    await $fetch<{ task_id: string; status: string }>(
      `${config.public.apiBase}/api/waywo-comments/${commentId}/process`,
      {
        method: 'POST'
      }
    )
  } catch (err) {
    console.error('Failed to process comment:', err)
  } finally {
    // Keep the loading state for a moment to indicate task was queued
    setTimeout(() => {
      processingCommentId.value = null
    }, 2000)
  }
}

// Trigger processing of comments to extract projects
async function processComments() {
  if (isProcessing.value) return

  isProcessing.value = true
  processError.value = null
  processSuccess.value = false
  taskId.value = null

  try {
    const limit = maxComments.value ? parseInt(maxComments.value, 10) : null
    const response = await $fetch<{ task_id: string; status: string }>(
      `${config.public.apiBase}/api/process-waywo-comments`,
      {
        method: 'POST',
        body: limit ? { limit } : {}
      }
    )

    taskId.value = response.task_id
    processSuccess.value = true

    // Clear success message after 10 seconds
    setTimeout(() => {
      processSuccess.value = false
    }, 10000)
  } catch (err) {
    console.error('Failed to trigger processing:', err)
    processError.value = 'Failed to trigger processing. Make sure the backend is running.'
  } finally {
    isProcessing.value = false
  }
}

// Clear post filter
function clearFilter() {
  window.location.href = '/comments'
}

// Pagination
function nextPage() {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchComments()
  }
}

function prevPage() {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit.value)
    fetchComments()
  }
}

// Fetch comments on mount
onMounted(() => {
  fetchComments()
})
</script>

<style>
/* Style for HTML content from HN */
.prose a {
  color: hsl(var(--primary));
}
.prose a:hover {
  text-decoration: underline;
}
.prose code {
  background-color: hsl(var(--muted));
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}
.prose pre {
  background-color: hsl(var(--muted));
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
}
</style>
