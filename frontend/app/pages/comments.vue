<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:message-square" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Comments</h1>
        <p class="text-xl text-muted-foreground">
          Browse project submissions from "What are you working on?" posts
        </p>
      </div>

      <!-- Stats Card -->
      <Card class="p-6 mb-8">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Total Comments</p>
            <p class="text-3xl font-bold">{{ total }}</p>
          </div>
          <Button variant="outline" @click="fetchComments" :disabled="isLoading">
            <Icon
              :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoading ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>
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
        <NuxtLink to="/posts">
          <Button class="mt-4">
            Go to Posts
            <Icon name="lucide:arrow-right" class="ml-2 h-4 w-4" />
          </Button>
        </NuxtLink>
      </div>

      <div v-else class="space-y-4">
        <Card v-for="comment in comments" :key="comment.id" class="p-6">
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
                >
                  {{ comment.by || 'Unknown' }}
                </a>
                <p class="text-sm text-muted-foreground">
                  {{ formatTime(comment.time) }}
                </p>
              </div>
            </div>
            <a
              :href="`https://news.ycombinator.com/item?id=${comment.id}`"
              target="_blank"
              class="text-muted-foreground hover:text-primary"
            >
              <Icon name="lucide:external-link" class="h-4 w-4" />
            </a>
          </div>

          <div
            class="prose prose-sm max-w-none dark:prose-invert"
            v-html="comment.text || '<em>No content</em>'"
          />

          <div class="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
            <span>
              ID: {{ comment.id }}
            </span>
            <span v-if="comment.kids?.length">
              {{ comment.kids.length }} {{ comment.kids.length === 1 ? 'reply' : 'replies' }}
            </span>
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
interface WaywoComment {
  id: number
  type: string
  by: string | null
  time: number | null
  text: string | null
  parent: number | null
  kids: number[] | null
}

// Set page metadata
useHead({
  title: 'Comments - waywo',
  meta: [
    { name: 'description', content: 'Browse project submissions from What are you working on posts.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const comments = ref<WaywoComment[]>([])
const total = ref(0)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)

const limit = ref(20)
const offset = ref(0)

// Format Unix timestamp to readable date
function formatTime(timestamp: number | null): string {
  if (!timestamp) return 'Unknown date'
  const date = new Date(timestamp * 1000)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// Fetch comments from API
async function fetchComments() {
  isLoading.value = true
  fetchError.value = null

  try {
    const response = await $fetch<{
      comments: WaywoComment[]
      total: number
      limit: number
      offset: number
    }>(`${config.public.apiBase}/api/waywo-comments`, {
      params: {
        limit: limit.value,
        offset: offset.value
      }
    })
    comments.value = response.comments
    total.value = response.total
  } catch (err) {
    console.error('Failed to fetch comments:', err)
    fetchError.value = 'Failed to fetch comments. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
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
