<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:lightbulb" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Projects</h1>
        <p class="text-xl text-muted-foreground">
          Extracted projects from "What are you working on?" submissions
        </p>
        <!-- Filter indicator -->
        <div v-if="commentId" class="mt-4">
          <Badge variant="outline" class="text-sm">
            Filtered by Comment ID: {{ commentId }}
            <button @click="clearFilter" class="ml-2 hover:text-destructive">
              <Icon name="lucide:x" class="h-3 w-3" />
            </button>
          </Badge>
        </div>
      </div>

      <!-- Stats Card -->
      <Card class="p-6 mb-8">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Total Projects</p>
            <p class="text-3xl font-bold">{{ total }}</p>
          </div>
          <Button variant="outline" @click="fetchProjects" :disabled="isLoading">
            <Icon
              :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoading ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>
      </Card>

      <!-- Projects List -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <div v-else-if="fetchError" class="text-center py-12">
        <Icon name="lucide:alert-circle" class="h-12 w-12 text-destructive mx-auto mb-4" />
        <p class="text-destructive">{{ fetchError }}</p>
        <Button variant="outline" @click="fetchProjects" class="mt-4">
          Try Again
        </Button>
      </div>

      <div v-else-if="projects.length === 0" class="text-center py-12">
        <Icon name="lucide:inbox" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p class="text-muted-foreground">No projects found</p>
        <p class="text-sm text-muted-foreground mt-2">
          Process some comments to extract projects
        </p>
        <a href="/comments">
          <Button class="mt-4">
            Go to Comments
            <Icon name="lucide:arrow-right" class="ml-2 h-4 w-4" />
          </Button>
        </a>
      </div>

      <div v-else class="space-y-4">
        <Card
          v-for="project in projects"
          :key="project.id"
          class="p-6 cursor-pointer hover:border-primary/50 transition-colors"
          @click="viewProject(project.id)"
        >
          <div class="flex justify-between items-start mb-3">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1">
                <h3 class="text-lg font-semibold">{{ project.title }}</h3>
                <Badge v-if="!project.is_valid_project" variant="destructive" class="text-xs">
                  Invalid
                </Badge>
              </div>
              <p class="text-muted-foreground">{{ project.short_description }}</p>
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

          <p class="text-sm text-muted-foreground mb-3">{{ project.description }}</p>

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

          <div class="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {{ formatDate(project.created_at) }}
            </span>
            <div class="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                class="text-destructive hover:bg-destructive hover:text-destructive-foreground"
                @click.stop="deleteProject(project.id)"
                :disabled="deletingProjectId === project.id"
              >
                <Icon
                  :name="deletingProjectId === project.id ? 'lucide:loader-2' : 'lucide:trash-2'"
                  :class="deletingProjectId === project.id ? 'animate-spin' : ''"
                  class="mr-1 h-3 w-3"
                />
                {{ deletingProjectId === project.id ? 'Deleting...' : 'Delete' }}
              </Button>
              <a
                :href="`/projects/${project.id}`"
                class="text-primary hover:underline flex items-center gap-1"
                @click.stop
              >
                View Details
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

// Set page metadata
useHead({
  title: 'Projects - waywo',
  meta: [
    { name: 'description', content: 'Browse extracted projects from What are you working on submissions.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()
const route = useRoute()

// Get comment_id from query params
const commentId = computed(() => {
  const id = route.query.comment_id
  return id ? Number(id) : null
})

// Reactive state
const projects = ref<WaywoProject[]>([])
const total = ref(0)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)

const limit = ref(20)
const offset = ref(0)

// Delete state
const deletingProjectId = ref<number | null>(null)

// Format date
function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Fetch projects from API
async function fetchProjects() {
  isLoading.value = true
  fetchError.value = null

  try {
    const params: Record<string, number | undefined> = {
      limit: limit.value,
      offset: offset.value
    }
    if (commentId.value) {
      params.comment_id = commentId.value
    }

    const response = await $fetch<{
      projects: WaywoProject[]
      total: number
      limit: number
      offset: number
    }>(`${config.public.apiBase}/api/waywo-projects`, { params })
    projects.value = response.projects
    total.value = response.total
  } catch (err) {
    console.error('Failed to fetch projects:', err)
    fetchError.value = 'Failed to fetch projects. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
}

// View project details
function viewProject(projectId: number) {
  window.location.href = `/projects/${projectId}`
}

// Delete project
async function deleteProject(projectId: number) {
  if (deletingProjectId.value === projectId) return

  if (!confirm('Are you sure you want to delete this project?')) {
    return
  }

  deletingProjectId.value = projectId

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-projects/${projectId}`, {
      method: 'DELETE'
    })
    // Remove from local list
    projects.value = projects.value.filter(p => p.id !== projectId)
    total.value -= 1
  } catch (err) {
    console.error('Failed to delete project:', err)
    alert('Failed to delete project. Please try again.')
  } finally {
    deletingProjectId.value = null
  }
}

// Clear comment filter
function clearFilter() {
  window.location.href = '/projects'
}

// Pagination
function nextPage() {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchProjects()
  }
}

function prevPage() {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit.value)
    fetchProjects()
  }
}

// Fetch projects on mount
onMounted(() => {
  fetchProjects()
})
</script>
