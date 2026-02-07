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
        <a href="/projects">
          <Button variant="outline" class="mt-4">
            <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
            Back to Projects
          </Button>
        </a>
      </div>

      <!-- Project Details -->
      <div v-else-if="project">
        <!-- Back Button -->
        <a href="/projects" class="inline-flex items-center text-muted-foreground hover:text-primary mb-6">
          <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
          Back to Projects
        </a>

        <!-- Header -->
        <div class="mb-8">
          <div class="flex items-start justify-between mb-4">
            <div>
              <div class="flex items-center gap-3 mb-2">
                <button
                  @click="toggleBookmark"
                  :disabled="isTogglingBookmark"
                  class="hover:scale-110 transition-transform"
                  :title="project.is_bookmarked ? 'Remove bookmark' : 'Add bookmark'"
                >
                  <Icon
                    name="lucide:star"
                    :class="[
                      'h-7 w-7 transition-colors',
                      project.is_bookmarked ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground hover:text-yellow-500',
                      isTogglingBookmark ? 'animate-pulse' : ''
                    ]"
                  />
                </button>
                <h1 class="text-3xl font-bold">{{ project.title }}</h1>
                <Badge v-if="!project.is_valid_project" variant="destructive">
                  Invalid
                </Badge>
              </div>
              <p class="text-xl text-muted-foreground">{{ project.short_description }}</p>
            </div>
            <div class="flex gap-3">
              <div class="text-center">
                <div class="text-2xl font-bold text-primary">{{ project.idea_score }}</div>
                <div class="text-xs text-muted-foreground">Idea Score</div>
              </div>
              <div class="text-center">
                <div class="text-2xl font-bold text-primary">{{ project.complexity_score }}</div>
                <div class="text-xs text-muted-foreground">Complexity</div>
              </div>
            </div>
          </div>

          <!-- Tags -->
          <div class="flex flex-wrap gap-2 mb-4">
            <Badge
              v-for="tag in project.hashtags"
              :key="tag"
              variant="secondary"
            >
              #{{ tag }}
            </Badge>
          </div>

          <!-- Delete Button -->
          <button
            @click="deleteProject"
            :disabled="isDeleting"
            class="text-xs text-muted-foreground hover:text-destructive flex items-center gap-1 mb-4"
          >
            <Icon
              :name="isDeleting ? 'lucide:loader-2' : 'lucide:trash-2'"
              :class="isDeleting ? 'animate-spin' : ''"
              class="h-3 w-3"
            />
            {{ isDeleting ? 'Deleting...' : 'Delete project' }}
          </button>

          <!-- Invalid Reason -->
          <Alert v-if="!project.is_valid_project && project.invalid_reason" variant="destructive" class="mb-4">
            <Icon name="lucide:alert-circle" class="h-4 w-4" />
            <AlertTitle>Invalid Project</AlertTitle>
            <AlertDescription>{{ project.invalid_reason }}</AlertDescription>
          </Alert>
        </div>

        <!-- Description -->
        <Card class="p-6 mb-6">
          <h2 class="text-lg font-semibold mb-3">Description</h2>
          <p class="text-muted-foreground">{{ project.description }}</p>
        </Card>

        <!-- Screenshot -->
        <Card v-if="project.screenshot_path" class="p-6 mb-6">
          <h2 class="text-lg font-semibold mb-3">Screenshot</h2>
          <div class="rounded-lg overflow-hidden border">
            <img
              :src="`${config.public.apiBase}/media/${project.screenshot_path}`"
              :alt="`Screenshot of ${project.title}`"
              class="w-full"
              loading="lazy"
            />
          </div>
          <p v-if="project.project_urls?.length" class="text-sm text-muted-foreground mt-2">
            Source: {{ project.project_urls[0] }}
          </p>
        </Card>

        <!-- URLs & Content (Collapsible) -->
        <Collapsible v-if="project.project_urls?.length" class="mb-6">
          <Card class="p-6">
            <CollapsibleTrigger class="flex items-center justify-between w-full">
              <h2 class="text-lg font-semibold">URLs & Scraped Content</h2>
              <Icon name="lucide:chevron-down" class="h-5 w-5 text-muted-foreground" />
            </CollapsibleTrigger>
            <CollapsibleContent class="mt-4 space-y-4">
              <div v-for="url in project.project_urls" :key="url" class="border rounded-lg p-4">
                <a
                  :href="url"
                  target="_blank"
                  class="text-primary hover:underline flex items-center gap-2 mb-2"
                >
                  <Icon name="lucide:external-link" class="h-4 w-4" />
                  {{ url }}
                </a>
                <div v-if="project.url_summaries?.[url]" class="text-sm text-muted-foreground bg-muted p-3 rounded">
                  {{ project.url_summaries[url] }}
                </div>
                <div v-else class="text-sm text-muted-foreground italic">
                  No content summary available
                </div>
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>

        <!-- Original Comment (Collapsible) -->
        <Collapsible v-if="sourceComment" class="mb-6">
          <Card class="p-6">
            <CollapsibleTrigger class="flex items-center justify-between w-full">
              <h2 class="text-lg font-semibold">Original Comment</h2>
              <Icon name="lucide:chevron-down" class="h-5 w-5 text-muted-foreground" />
            </CollapsibleTrigger>
            <CollapsibleContent class="mt-4">
              <div class="flex items-center gap-3 mb-4">
                <div class="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <span class="text-sm font-medium text-primary">
                    {{ sourceComment.by?.charAt(0).toUpperCase() || '?' }}
                  </span>
                </div>
                <div>
                  <a
                    :href="`https://news.ycombinator.com/user?id=${sourceComment.by}`"
                    target="_blank"
                    class="font-medium hover:underline"
                  >
                    {{ sourceComment.by || 'Unknown' }}
                  </a>
                  <p class="text-sm text-muted-foreground">
                    {{ formatTime(sourceComment.time) }}
                  </p>
                </div>
              </div>
              <div
                class="prose prose-sm max-w-none dark:prose-invert bg-muted p-4 rounded-lg"
                v-html="sourceComment.text || '<em>No content</em>'"
              />
              <div class="mt-4 flex gap-4">
                <a
                  :href="`https://news.ycombinator.com/item?id=${sourceComment.id}`"
                  target="_blank"
                  class="text-sm text-primary hover:underline flex items-center gap-1"
                >
                  <Icon name="lucide:external-link" class="h-3 w-3" />
                  View on HN
                </a>
                <a
                  v-if="parentPost"
                  :href="`/comments?post_id=${parentPost.id}`"
                  class="text-sm text-primary hover:underline flex items-center gap-1"
                >
                  <Icon name="lucide:file-text" class="h-3 w-3" />
                  View Post Comments
                </a>
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>

        <!-- Workflow Logs (Collapsible) -->
        <Collapsible v-if="project.workflow_logs?.length" class="mb-6">
          <Card class="p-6">
            <CollapsibleTrigger class="flex items-center justify-between w-full">
              <h2 class="text-lg font-semibold">Processing Logs</h2>
              <Icon name="lucide:chevron-down" class="h-5 w-5 text-muted-foreground" />
            </CollapsibleTrigger>
            <CollapsibleContent class="mt-4">
              <div class="bg-muted rounded-lg p-4 font-mono text-sm space-y-1 max-h-96 overflow-y-auto">
                <div v-for="(log, index) in project.workflow_logs" :key="index" class="text-muted-foreground">
                  {{ log }}
                </div>
              </div>
            </CollapsibleContent>
          </Card>
        </Collapsible>

        <!-- Metadata -->
        <Card class="p-6 mb-6">
          <h2 class="text-lg font-semibold mb-3">Metadata</h2>
          <div class="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span class="text-muted-foreground">Project ID:</span>
              <span class="ml-2 font-medium">{{ project.id }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Source Comment ID:</span>
              <span class="ml-2 font-medium">{{ project.source_comment_id }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Comment Date:</span>
              <span class="ml-2 font-medium">{{ project.comment_time ? formatTime(project.comment_time) : 'Unknown' }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Processed:</span>
              <span class="ml-2 font-medium">{{ formatDate(project.processed_at) }}</span>
            </div>
          </div>
        </Card>

        <!-- Similar Projects -->
        <Card class="p-6">
          <h2 class="text-lg font-semibold mb-3">Similar Projects</h2>
          <div v-if="isLoadingSimilar" class="flex items-center gap-2 text-muted-foreground">
            <Icon name="lucide:loader-2" class="h-4 w-4 animate-spin" />
            <span class="text-sm">Finding similar projects...</span>
          </div>
          <div v-else-if="similarProjects.length === 0" class="text-sm text-muted-foreground">
            No similar projects found.
          </div>
          <div v-else class="space-y-3">
            <a
              v-for="item in similarProjects"
              :key="item.project.id"
              :href="`/projects/${item.project.id}`"
              class="flex items-center gap-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
            >
              <div
                v-if="item.project.screenshot_path"
                class="w-16 h-10 rounded overflow-hidden flex-shrink-0 bg-muted"
              >
                <img
                  :src="`${config.public.apiBase}/media/${item.project.screenshot_path.replace('.jpg', '_thumb.jpg')}`"
                  :alt="item.project.title"
                  class="w-full h-full object-cover"
                  loading="lazy"
                />
              </div>
              <div
                v-else
                class="w-16 h-10 rounded flex-shrink-0 bg-muted flex items-center justify-center"
              >
                <Icon name="lucide:image-off" class="h-4 w-4 text-muted-foreground" />
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-medium text-sm truncate">{{ item.project.title }}</div>
                <div class="text-xs text-muted-foreground truncate">{{ item.project.short_description }}</div>
              </div>
              <div class="flex-shrink-0 text-right">
                <div class="text-sm font-medium text-primary">{{ Math.round(item.similarity * 100) }}%</div>
                <div class="text-xs text-muted-foreground">match</div>
              </div>
            </a>
          </div>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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
  is_bookmarked: boolean
  screenshot_path: string | null
  created_at: string
  processed_at: string
  comment_time: number | null
  workflow_logs: string[]
}

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

// Get route params
const route = useRoute()
const projectId = computed(() => Number(route.params.id))

// Set page metadata
useHead({
  title: computed(() => project.value ? `${project.value.title} - waywo` : 'Project - waywo'),
  meta: [
    { name: 'description', content: 'View project details.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const project = ref<WaywoProject | null>(null)
const sourceComment = ref<WaywoComment | null>(null)
const parentPost = ref<WaywoPost | null>(null)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)
const isDeleting = ref(false)
const isTogglingBookmark = ref(false)
const similarProjects = ref<{ project: WaywoProject; similarity: number }[]>([])
const isLoadingSimilar = ref(false)

// Format date
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

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

// Fetch project from API
async function fetchProject() {
  isLoading.value = true
  fetchError.value = null

  try {
    const response = await $fetch<{
      project: WaywoProject
      source_comment: WaywoComment | null
      parent_post: WaywoPost | null
    }>(`${config.public.apiBase}/api/waywo-projects/${projectId.value}`)

    project.value = response.project
    sourceComment.value = response.source_comment
    parentPost.value = response.parent_post

    // Fetch similar projects in parallel (non-blocking)
    fetchSimilarProjects()
  } catch (err) {
    console.error('Failed to fetch project:', err)
    fetchError.value = 'Failed to fetch project. It may not exist.'
  } finally {
    isLoading.value = false
  }
}

// Fetch similar projects
async function fetchSimilarProjects() {
  isLoadingSimilar.value = true
  try {
    const response = await $fetch<{
      similar_projects: { project: WaywoProject; similarity: number }[]
      project_id: number
    }>(`${config.public.apiBase}/api/waywo-projects/${projectId.value}/similar?limit=5`)
    similarProjects.value = response.similar_projects
  } catch (err) {
    console.error('Failed to fetch similar projects:', err)
  } finally {
    isLoadingSimilar.value = false
  }
}

// Delete project
async function deleteProject() {
  if (isDeleting.value) return

  if (!confirm('Are you sure you want to delete this project?')) {
    return
  }

  isDeleting.value = true

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-projects/${projectId.value}`, {
      method: 'DELETE'
    })
    // Redirect to projects list after deletion
    window.location.href = '/projects'
  } catch (err) {
    console.error('Failed to delete project:', err)
    alert('Failed to delete project. Please try again.')
    isDeleting.value = false
  }
}

// Toggle bookmark
async function toggleBookmark() {
  if (isTogglingBookmark.value || !project.value) return

  isTogglingBookmark.value = true

  try {
    const response = await $fetch<{ is_bookmarked: boolean; project_id: number }>(
      `${config.public.apiBase}/api/waywo-projects/${projectId.value}/bookmark`,
      { method: 'POST' }
    )
    project.value.is_bookmarked = response.is_bookmarked
  } catch (err) {
    console.error('Failed to toggle bookmark:', err)
  } finally {
    isTogglingBookmark.value = false
  }
}

// Fetch project on mount
onMounted(() => {
  fetchProject()
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
