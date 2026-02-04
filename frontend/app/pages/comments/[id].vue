<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <!-- Loading State -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <!-- Error State -->
      <div v-else-if="fetchError" class="text-center py-12">
        <Icon name="lucide:alert-circle" class="h-12 w-12 text-destructive mx-auto mb-4" />
        <p class="text-destructive">{{ fetchError }}</p>
        <a href="/comments">
          <Button variant="outline" class="mt-4">
            <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
            Back to Comments
          </Button>
        </a>
      </div>

      <!-- Comment Details -->
      <div v-else-if="comment">
        <!-- Back Button -->
        <a href="/comments" class="inline-flex items-center text-muted-foreground hover:text-primary mb-6">
          <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
          Back to Comments
        </a>

        <!-- Header Card -->
        <Card class="p-6 mb-6">
          <div class="flex items-start justify-between mb-4">
            <div class="flex items-center gap-3">
              <div class="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                <span class="text-lg font-medium text-primary">
                  {{ comment.by?.charAt(0).toUpperCase() || '?' }}
                </span>
              </div>
              <div>
                <a
                  :href="`https://news.ycombinator.com/user?id=${comment.by}`"
                  target="_blank"
                  class="text-lg font-semibold hover:underline"
                >
                  {{ comment.by || 'Unknown' }}
                </a>
                <p class="text-sm text-muted-foreground">
                  {{ formatTime(comment.time) }}
                </p>
              </div>
            </div>
            <div class="flex gap-2">
              <a
                :href="`https://news.ycombinator.com/item?id=${comment.id}`"
                target="_blank"
              >
                <Button variant="outline" size="sm">
                  <Icon name="lucide:external-link" class="mr-2 h-4 w-4" />
                  View on HN
                </Button>
              </a>
              <Button
                @click="processComment"
                :disabled="isProcessing"
                size="sm"
              >
                <Icon
                  :name="isProcessing ? 'lucide:loader-2' : 'lucide:sparkles'"
                  :class="isProcessing ? 'animate-spin' : ''"
                  class="mr-2 h-4 w-4"
                />
                {{ isProcessing ? 'Processing...' : 'Process Comment' }}
              </Button>
            </div>
          </div>

          <!-- Processing Status -->
          <Alert v-if="processSuccess" class="mb-4 border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950">
            <Icon name="lucide:check-circle" class="h-4 w-4 text-green-600 dark:text-green-400" />
            <AlertTitle class="text-green-800 dark:text-green-200">Task Queued</AlertTitle>
            <AlertDescription class="text-green-700 dark:text-green-300">
              Processing task queued. Task ID: {{ taskId }}
              <br />
              <span class="text-sm">Refresh the page in a moment to see extracted projects.</span>
            </AlertDescription>
          </Alert>

          <Alert v-if="processError" variant="destructive" class="mb-4">
            <Icon name="lucide:alert-circle" class="h-4 w-4" />
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{{ processError }}</AlertDescription>
          </Alert>

          <!-- Comment Content -->
          <div
            class="prose prose-sm max-w-none dark:prose-invert"
            v-html="comment.text || '<em>No content</em>'"
          />
        </Card>

        <!-- Parent Post Info -->
        <Card v-if="parentPost" class="p-6 mb-6">
          <h2 class="text-lg font-semibold mb-3">Parent Post</h2>
          <div class="flex items-center justify-between">
            <div>
              <a
                :href="`https://news.ycombinator.com/item?id=${parentPost.id}`"
                target="_blank"
                class="text-primary hover:underline font-medium"
              >
                {{ parentPost.title || `Post ${parentPost.id}` }}
              </a>
              <p class="text-sm text-muted-foreground mt-1">
                {{ formatDate(parentPost.year, parentPost.month) }}
              </p>
            </div>
            <a :href="`/comments?post_id=${parentPost.id}`">
              <Button variant="outline" size="sm">
                <Icon name="lucide:message-square" class="mr-2 h-4 w-4" />
                View All Comments
              </Button>
            </a>
          </div>
        </Card>

        <!-- Extracted Projects -->
        <Card class="p-6 mb-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold">Extracted Projects</h2>
            <Badge variant="outline">{{ projects.length }} project(s)</Badge>
          </div>

          <div v-if="projects.length === 0" class="text-center py-8">
            <Icon name="lucide:inbox" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p class="text-muted-foreground">No projects extracted yet</p>
            <p class="text-sm text-muted-foreground mt-2">
              Click "Process Comment" to extract projects from this comment
            </p>
          </div>

          <div v-else class="space-y-4">
            <div
              v-for="project in projects"
              :key="project.id"
              class="border rounded-lg p-4 hover:border-primary/50 transition-colors cursor-pointer"
              @click="viewProject(project.id)"
            >
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center gap-2">
                  <h3 class="font-semibold">{{ project.title }}</h3>
                  <Badge v-if="!project.is_valid_project" variant="destructive" class="text-xs">
                    Invalid
                  </Badge>
                </div>
                <div class="flex gap-2">
                  <Badge variant="outline" class="flex items-center gap-1">
                    <Icon name="lucide:lightbulb" class="h-3 w-3" />
                    {{ project.idea_score }}
                  </Badge>
                  <Badge variant="outline" class="flex items-center gap-1">
                    <Icon name="lucide:settings" class="h-3 w-3" />
                    {{ project.complexity_score }}
                  </Badge>
                </div>
              </div>
              <p class="text-sm text-muted-foreground mb-2">{{ project.short_description }}</p>
              <div class="flex flex-wrap gap-2">
                <Badge
                  v-for="tag in project.hashtags"
                  :key="tag"
                  variant="secondary"
                  class="text-xs"
                >
                  #{{ tag }}
                </Badge>
              </div>
            </div>
          </div>
        </Card>

        <!-- Metadata -->
        <Card class="p-6">
          <h2 class="text-lg font-semibold mb-3">Metadata</h2>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-muted-foreground">Comment ID:</span>
              <span class="ml-2 font-medium">{{ comment.id }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Parent ID:</span>
              <span class="ml-2 font-medium">{{ comment.parent || 'N/A' }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Replies:</span>
              <span class="ml-2 font-medium">{{ comment.kids?.length || 0 }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Type:</span>
              <span class="ml-2 font-medium">{{ comment.type }}</span>
            </div>
          </div>
        </Card>
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

interface WaywoPost {
  id: number
  title: string | null
  year: number | null
  month: number | null
}

interface WaywoProject {
  id: number
  source_comment_id: number
  is_valid_project: boolean
  invalid_reason: string | null
  title: string
  short_description: string
  description: string
  hashtags: string[]
  project_urls: string[]
  url_summaries: Record<string, string>
  idea_score: number
  complexity_score: number
  created_at: string
  processed_at: string
  workflow_logs: string[]
}

// Get route params
const route = useRoute()
const commentId = computed(() => Number(route.params.id))

// Set page metadata
useHead({
  title: computed(() => comment.value ? `Comment by ${comment.value.by} - waywo` : 'Comment - waywo'),
  meta: [
    { name: 'description', content: 'View comment details and extracted projects.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const comment = ref<WaywoComment | null>(null)
const parentPost = ref<WaywoPost | null>(null)
const projects = ref<WaywoProject[]>([])
const isLoading = ref(false)
const fetchError = ref<string | null>(null)

// Processing state
const isProcessing = ref(false)
const processError = ref<string | null>(null)
const processSuccess = ref(false)
const taskId = ref<string | null>(null)

// Format Unix timestamp
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

// Format date from year/month
function formatDate(year: number | null, month: number | null): string {
  if (!year || !month) return 'Unknown'
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${monthNames[month - 1]} ${year}`
}

// Fetch comment from API
async function fetchComment() {
  isLoading.value = true
  fetchError.value = null

  try {
    const response = await $fetch<{
      comment: WaywoComment
      parent_post: WaywoPost | null
      projects: WaywoProject[]
    }>(`${config.public.apiBase}/api/waywo-comments/${commentId.value}`)

    comment.value = response.comment
    parentPost.value = response.parent_post
    projects.value = response.projects
  } catch (err) {
    console.error('Failed to fetch comment:', err)
    fetchError.value = 'Failed to fetch comment. It may not exist.'
  } finally {
    isLoading.value = false
  }
}

// Process this comment
async function processComment() {
  if (isProcessing.value) return

  isProcessing.value = true
  processError.value = null
  processSuccess.value = false
  taskId.value = null

  try {
    const response = await $fetch<{ task_id: string; status: string }>(
      `${config.public.apiBase}/api/waywo-comments/${commentId.value}/process`,
      {
        method: 'POST'
      }
    )

    taskId.value = response.task_id
    processSuccess.value = true

    // Refresh after a delay to show new projects
    setTimeout(() => {
      fetchComment()
    }, 5000)
  } catch (err) {
    console.error('Failed to process comment:', err)
    processError.value = 'Failed to trigger processing. Make sure the backend is running.'
  } finally {
    isProcessing.value = false
  }
}

// Navigate to project detail
function viewProject(projectId: number) {
  window.location.href = `/projects/${projectId}`
}

// Fetch comment on mount
onMounted(() => {
  fetchComment()
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
