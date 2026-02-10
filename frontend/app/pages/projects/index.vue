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
            <button @click="clearCommentFilter" class="ml-2 hover:text-destructive">
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
          <div class="flex gap-2">
            <Button :variant="sortOrder === 'random' ? 'default' : 'outline'" @click="shuffleProjects" :disabled="isLoading">
              <Icon
                name="lucide:shuffle"
                class="mr-2 h-4 w-4"
              />
              Shuffle
            </Button>
            <Button variant="outline" @click="refreshProjects" :disabled="isLoading">
              <Icon
                :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
                :class="isLoading ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      <!-- Filter Section -->
      <Collapsible v-model:open="isFilterOpen" class="mb-6">
        <div class="flex items-center justify-between mb-4">
          <CollapsibleTrigger as-child>
            <Button variant="outline" class="gap-2">
              <Icon name="lucide:filter" class="h-4 w-4" />
              Filters
              <Badge v-if="activeFilterCount > 0" variant="secondary" class="ml-1">
                {{ activeFilterCount }}
              </Badge>
              <Icon
                :name="isFilterOpen ? 'lucide:chevron-up' : 'lucide:chevron-down'"
                class="h-4 w-4"
              />
            </Button>
          </CollapsibleTrigger>
          <Button
            v-if="activeFilterCount > 0"
            variant="ghost"
            size="sm"
            @click="clearAllFilters"
          >
            <Icon name="lucide:x" class="mr-1 h-3 w-3" />
            Clear All Filters
          </Button>
        </div>

        <CollapsibleContent>
          <Card class="p-6">
            <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              <!-- Tags Filter -->
              <div class="space-y-2 lg:col-span-1">
                <Label>Tags</Label>
                <Combobox v-model="selectedTags" multiple>
                  <ComboboxAnchor class="w-full">
                    <div class="relative">
                      <div class="flex flex-wrap gap-1 min-h-[38px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                        <Badge
                          v-for="tag in selectedTags"
                          :key="tag"
                          variant="secondary"
                          class="text-xs"
                        >
                          #{{ tag }}
                          <button
                            @click.stop="removeTag(tag)"
                            class="ml-1 hover:text-destructive"
                          >
                            <Icon name="lucide:x" class="h-3 w-3" />
                          </button>
                        </Badge>
                        <ComboboxInput
                          v-model="tagSearchQuery"
                          placeholder="Search tags..."
                          class="flex-1 min-w-[100px] bg-transparent outline-none placeholder:text-muted-foreground"
                          @keydown.enter.prevent
                        />
                      </div>
                    </div>
                  </ComboboxAnchor>
                  <ComboboxList class="w-[var(--reka-combobox-trigger-width)] max-h-[200px] overflow-y-auto rounded-md border bg-popover p-1 shadow-md">
                    <ComboboxEmpty class="py-6 text-center text-sm text-muted-foreground">
                      No tags found
                    </ComboboxEmpty>
                    <ComboboxItem
                      v-for="tag in filteredTags"
                      :key="tag"
                      :value="tag"
                      class="cursor-pointer"
                    >
                      <ComboboxItemIndicator class="mr-2">
                        <Icon name="lucide:check" class="h-4 w-4" />
                      </ComboboxItemIndicator>
                      #{{ tag }}
                    </ComboboxItem>
                  </ComboboxList>
                </Combobox>
              </div>

              <!-- Idea Score Range -->
              <div class="space-y-2">
                <Label>Idea Score: {{ ideaScoreRange[0] }} - {{ ideaScoreRange[1] }}</Label>
                <Slider
                  v-model="ideaScoreRange"
                  :min="1"
                  :max="10"
                  :step="1"
                  class="w-full"
                />
                <div class="flex justify-between text-xs text-muted-foreground">
                  <span>1</span>
                  <span>10</span>
                </div>
              </div>

              <!-- Complexity Score Range -->
              <div class="space-y-2">
                <Label>Complexity Score: {{ complexityScoreRange[0] }} - {{ complexityScoreRange[1] }}</Label>
                <Slider
                  v-model="complexityScoreRange"
                  :min="1"
                  :max="10"
                  :step="1"
                  class="w-full"
                />
                <div class="flex justify-between text-xs text-muted-foreground">
                  <span>1</span>
                  <span>10</span>
                </div>
              </div>

              <!-- Date From -->
              <div class="space-y-2">
                <Label>Date From</Label>
                <Input
                  v-model="dateFrom"
                  type="date"
                  class="w-full"
                />
              </div>

              <!-- Date To -->
              <div class="space-y-2">
                <Label>Date To</Label>
                <Input
                  v-model="dateTo"
                  type="date"
                  class="w-full"
                />
              </div>

              <!-- Apply Filters Button -->
              <div class="flex items-end">
                <Button @click="applyFilters" class="w-full">
                  <Icon name="lucide:search" class="mr-2 h-4 w-4" />
                  Apply Filters
                </Button>
              </div>
            </div>
          </Card>
        </CollapsibleContent>
      </Collapsible>

      <!-- Filter Tabs (Bookmarked) -->
      <div class="flex gap-2 mb-6">
        <Button
          :variant="!showBookmarkedOnly ? 'default' : 'outline'"
          @click="showBookmarkedOnly && toggleBookmarkedFilter()"
        >
          All Projects
        </Button>
        <Button
          :variant="showBookmarkedOnly ? 'default' : 'outline'"
          @click="!showBookmarkedOnly && toggleBookmarkedFilter()"
        >
          <Icon name="lucide:star" class="mr-2 h-4 w-4" />
          Bookmarked
          <Badge v-if="bookmarkedCount > 0" variant="secondary" class="ml-2">
            {{ bookmarkedCount }}
          </Badge>
        </Button>
      </div>

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
          {{ activeFilterCount > 0 ? 'Try adjusting your filters' : 'Process some comments to extract projects' }}
        </p>
        <a v-if="activeFilterCount === 0" href="/comments">
          <Button class="mt-4">
            Go to Comments
            <Icon name="lucide:arrow-right" class="ml-2 h-4 w-4" />
          </Button>
        </a>
        <Button v-else variant="outline" @click="clearAllFilters" class="mt-4">
          Clear All Filters
        </Button>
      </div>

      <div v-else class="space-y-4">
        <Card
          v-for="project in projects"
          :key="project.id"
          class="p-6 cursor-pointer hover:border-primary/50 transition-colors"
          @click="viewProject(project.id)"
        >
          <div class="flex gap-4">
            <!-- Thumbnail -->
            <div class="flex-shrink-0 w-[160px] h-[96px] rounded-md overflow-hidden bg-muted flex items-center justify-center">
              <img
                v-if="project.screenshot_path"
                :src="`${config.public.apiBase}/media/${project.screenshot_path.replace('.jpg', '_thumb.jpg')}`"
                :alt="`Screenshot of ${project.title}`"
                class="w-full h-full object-cover"
                loading="lazy"
              />
              <Icon v-else name="lucide:image" class="h-8 w-8 text-muted-foreground/40" />
            </div>

            <div class="flex-1 min-w-0">
          <div class="flex justify-between items-start mb-3">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1">
                <button
                  @click.stop="toggleBookmark(project.id)"
                  :disabled="togglingBookmarkId === project.id"
                  class="hover:scale-110 transition-transform"
                  :title="project.is_bookmarked ? 'Remove bookmark' : 'Add bookmark'"
                >
                  <Icon
                    :name="project.is_bookmarked ? 'lucide:star' : 'lucide:star'"
                    :class="[
                      'h-5 w-5 transition-colors',
                      project.is_bookmarked ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground hover:text-yellow-500',
                      togglingBookmarkId === project.id ? 'animate-pulse' : ''
                    ]"
                  />
                </button>
                <h3 class="text-lg font-semibold">{{ project.title }}</h3>
                <a
                  v-if="project.primary_url"
                  :href="project.primary_url"
                  target="_blank"
                  class="text-xs text-muted-foreground hover:text-primary flex items-center gap-1 flex-shrink-0"
                  @click.stop
                >
                  <Icon name="lucide:external-link" class="h-3 w-3" />
                  {{ getHostname(project.primary_url) }}
                </a>
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
            <div class="flex items-center gap-2">
              <a
                :href="`https://news.ycombinator.com/item?id=${project.source_comment_id}`"
                target="_blank"
                class="inline-flex items-center justify-center w-5 h-5 rounded-sm bg-orange-500 text-white text-xs font-bold leading-none hover:bg-orange-600 transition-colors"
                title="View on Hacker News"
                @click.stop
              >Y</a>
              <span>
                {{ project.comment_time ? formatUnixTime(project.comment_time, false) : formatISODate(project.created_at) }}
              </span>
            </div>
            <div class="flex items-center gap-3">
              <Button
                variant="outline"
                size="sm"
                @click.stop="reprocessProject(project)"
                :disabled="reprocessingProjectId === project.id"
                :class="{
                  'border-amber-500 bg-amber-500/10 text-amber-600 hover:bg-amber-500/20': btnFeedback.getFeedback('reprocess-' + project.id) === 'confirming',
                  'border-green-500 bg-green-500/10 text-green-600': btnFeedback.getFeedback('reprocess-' + project.id) === 'success',
                  'border-destructive bg-destructive/10 text-destructive': btnFeedback.getFeedback('reprocess-' + project.id) === 'error',
                }"
              >
                <Icon
                  :name="reprocessingProjectId === project.id ? 'lucide:loader-2' : btnFeedback.getFeedback('reprocess-' + project.id) === 'confirming' ? 'lucide:alert-triangle' : btnFeedback.getFeedback('reprocess-' + project.id) === 'success' ? 'lucide:check' : btnFeedback.getFeedback('reprocess-' + project.id) === 'error' ? 'lucide:x' : 'lucide:rotate-cw'"
                  :class="reprocessingProjectId === project.id ? 'animate-spin' : ''"
                  class="mr-1 h-3 w-3"
                />
                {{ reprocessingProjectId === project.id ? 'Queuing...' : btnFeedback.getFeedback('reprocess-' + project.id) === 'confirming' ? 'Sure?' : btnFeedback.getFeedback('reprocess-' + project.id) === 'success' ? 'Queued' : btnFeedback.getFeedback('reprocess-' + project.id) === 'error' ? 'Failed' : 'Reprocess' }}
              </Button>
              <Button
                variant="outline"
                size="sm"
                @click.stop="generateVideoForProject(project.id)"
                :disabled="generatingVideoProjectId === project.id"
                :class="{
                  'border-green-500 bg-green-500/10 text-green-600': btnFeedback.getFeedback('genvideo-' + project.id) === 'success',
                  'border-destructive bg-destructive/10 text-destructive': btnFeedback.getFeedback('genvideo-' + project.id) === 'error',
                }"
              >
                <Icon
                  :name="generatingVideoProjectId === project.id ? 'lucide:loader-2' : btnFeedback.getFeedback('genvideo-' + project.id) === 'success' ? 'lucide:check' : btnFeedback.getFeedback('genvideo-' + project.id) === 'error' ? 'lucide:x' : 'lucide:video'"
                  :class="generatingVideoProjectId === project.id ? 'animate-spin' : ''"
                  class="mr-1 h-3 w-3"
                />
                {{ generatingVideoProjectId === project.id ? 'Starting...' : btnFeedback.getFeedback('genvideo-' + project.id) === 'success' ? 'Started' : btnFeedback.getFeedback('genvideo-' + project.id) === 'error' ? 'Failed' : 'Video' }}
              </Button>
              <Button
                variant="outline"
                size="sm"
                :class="[
                  btnFeedback.getFeedback('delete-' + project.id) === 'confirming'
                    ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90 border-destructive'
                    : btnFeedback.getFeedback('delete-' + project.id) === 'error'
                      ? 'border-destructive bg-destructive/10 text-destructive'
                      : 'text-destructive hover:bg-destructive hover:text-destructive-foreground'
                ]"
                @click.stop="deleteProject(project.id)"
                :disabled="deletingProjectId === project.id"
              >
                <Icon
                  :name="deletingProjectId === project.id ? 'lucide:loader-2' : btnFeedback.getFeedback('delete-' + project.id) === 'confirming' ? 'lucide:alert-triangle' : btnFeedback.getFeedback('delete-' + project.id) === 'error' ? 'lucide:x' : 'lucide:trash-2'"
                  :class="deletingProjectId === project.id ? 'animate-spin' : ''"
                  class="mr-1 h-3 w-3"
                />
                {{ deletingProjectId === project.id ? 'Deleting...' : btnFeedback.getFeedback('delete-' + project.id) === 'confirming' ? 'Sure?' : btnFeedback.getFeedback('delete-' + project.id) === 'error' ? 'Failed' : 'Delete' }}
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
import type { WaywoProject } from '~/types/models'

// Set page metadata
useHead({
  title: 'Projects - waywo',
  meta: [
    { name: 'description', content: 'Browse extracted projects from What are you working on submissions.' }
  ]
})

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
const bookmarkedCount = ref(0)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)

const limit = ref(20)
const offset = ref(0)

// Filter state
const isFilterOpen = ref(false)
const showBookmarkedOnly = ref(false)
const selectedTags = ref<string[]>([])
const ideaScoreRange = ref<number[]>([1, 10])
const complexityScoreRange = ref<number[]>([1, 10])
const dateFrom = ref('')
const dateTo = ref('')

// Tag autocomplete state
const tagSearchQuery = ref('')
const availableTags = ref<string[]>([])

// Computed: filtered tags for autocomplete
const filteredTags = computed(() => {
  const query = tagSearchQuery.value.toLowerCase()
  return availableTags.value
    .filter(tag => !selectedTags.value.includes(tag))
    .filter(tag => tag.toLowerCase().includes(query))
    .slice(0, 20)
})

// Computed: active filter count
const activeFilterCount = computed(() => {
  let count = 0
  if (selectedTags.value.length > 0) count++
  if (ideaScoreRange.value[0] > 1 || ideaScoreRange.value[1] < 10) count++
  if (complexityScoreRange.value[0] > 1 || complexityScoreRange.value[1] < 10) count++
  if (dateFrom.value) count++
  if (dateTo.value) count++
  if (showBookmarkedOnly.value) count++
  return count
})

// Delete state
const deletingProjectId = ref<number | null>(null)

// Sort state
const sortOrder = ref<'default' | 'random'>('default')

// Reprocess state
const reprocessingProjectId = ref<number | null>(null)

// Bookmark state
const togglingBookmarkId = ref<number | null>(null)

// Generate video state
const generatingVideoProjectId = ref<number | null>(null)

// Button feedback
const btnFeedback = useButtonFeedback()

// Extract hostname from URL
function getHostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

// Remove tag from selection
function removeTag(tag: string) {
  selectedTags.value = selectedTags.value.filter(t => t !== tag)
}

// Fetch available tags for autocomplete
async function fetchTags() {
  try {
    const response = await $fetch<{ hashtags: string[]; total: number }>(
      `${config.public.apiBase}/api/waywo-projects/hashtags`
    )
    availableTags.value = response.hashtags
  } catch (err) {
    console.error('Failed to fetch tags:', err)
  }
}

// Build URL params from current filter state
function buildUrlParams(): Record<string, string> {
  const params: Record<string, string> = {}

  if (selectedTags.value.length > 0) {
    params.tags = selectedTags.value.join(',')
  }
  if (ideaScoreRange.value[0] > 1) {
    params.min_idea = String(ideaScoreRange.value[0])
  }
  if (ideaScoreRange.value[1] < 10) {
    params.max_idea = String(ideaScoreRange.value[1])
  }
  if (complexityScoreRange.value[0] > 1) {
    params.min_complexity = String(complexityScoreRange.value[0])
  }
  if (complexityScoreRange.value[1] < 10) {
    params.max_complexity = String(complexityScoreRange.value[1])
  }
  if (dateFrom.value) {
    params.date_from = dateFrom.value
  }
  if (dateTo.value) {
    params.date_to = dateTo.value
  }
  if (showBookmarkedOnly.value) {
    params.bookmarked = 'true'
  }
  if (commentId.value) {
    params.comment_id = String(commentId.value)
  }

  return params
}

// Update URL with current filters (without page reload)
function updateUrl() {
  const params = buildUrlParams()
  const searchParams = new URLSearchParams(params)
  const newUrl = searchParams.toString()
    ? `${window.location.pathname}?${searchParams.toString()}`
    : window.location.pathname
  window.history.replaceState({}, '', newUrl)
}

// Read filters from URL on mount
function readFiltersFromUrl() {
  const query = route.query

  if (query.tags && typeof query.tags === 'string') {
    selectedTags.value = query.tags.split(',').filter(t => t.trim())
  }
  if (query.min_idea) {
    ideaScoreRange.value[0] = Math.max(1, Math.min(10, Number(query.min_idea)))
  }
  if (query.max_idea) {
    ideaScoreRange.value[1] = Math.max(1, Math.min(10, Number(query.max_idea)))
  }
  if (query.min_complexity) {
    complexityScoreRange.value[0] = Math.max(1, Math.min(10, Number(query.min_complexity)))
  }
  if (query.max_complexity) {
    complexityScoreRange.value[1] = Math.max(1, Math.min(10, Number(query.max_complexity)))
  }
  if (query.date_from && typeof query.date_from === 'string') {
    dateFrom.value = query.date_from
  }
  if (query.date_to && typeof query.date_to === 'string') {
    dateTo.value = query.date_to
  }
  if (query.bookmarked === 'true') {
    showBookmarkedOnly.value = true
  }

  // Open filter panel if there are active filters
  if (activeFilterCount.value > 0) {
    isFilterOpen.value = true
  }
}

// Fetch projects from API
async function fetchProjects() {
  isLoading.value = true
  fetchError.value = null

  try {
    const params: Record<string, string | number | boolean | undefined> = {
      limit: limit.value,
      offset: offset.value
    }

    // Add sort order
    if (sortOrder.value === 'random') {
      params.sort = 'random'
    }

    // Add comment_id filter
    if (commentId.value) {
      params.comment_id = commentId.value
    }

    // Add bookmarked filter
    if (showBookmarkedOnly.value) {
      params.bookmarked = true
    }

    // Add tag filter
    if (selectedTags.value.length > 0) {
      params.tags = selectedTags.value.join(',')
    }

    // Add score filters
    if (ideaScoreRange.value[0] > 1) {
      params.min_idea_score = ideaScoreRange.value[0]
    }
    if (ideaScoreRange.value[1] < 10) {
      params.max_idea_score = ideaScoreRange.value[1]
    }
    if (complexityScoreRange.value[0] > 1) {
      params.min_complexity_score = complexityScoreRange.value[0]
    }
    if (complexityScoreRange.value[1] < 10) {
      params.max_complexity_score = complexityScoreRange.value[1]
    }

    // Add date filters
    if (dateFrom.value) {
      params.date_from = dateFrom.value
    }
    if (dateTo.value) {
      params.date_to = dateTo.value
    }

    const response = await $fetch<{
      projects: WaywoProject[]
      total: number
      bookmarked_count: number
      limit: number
      offset: number
    }>(`${config.public.apiBase}/api/waywo-projects`, { params })
    projects.value = response.projects
    total.value = response.total
    bookmarkedCount.value = response.bookmarked_count
  } catch (err) {
    console.error('Failed to fetch projects:', err)
    fetchError.value = 'Failed to fetch projects. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
}

// Apply filters and update URL
function applyFilters() {
  offset.value = 0
  updateUrl()
  fetchProjects()
}

// Clear all filters
function clearAllFilters() {
  selectedTags.value = []
  ideaScoreRange.value = [1, 10]
  complexityScoreRange.value = [1, 10]
  dateFrom.value = ''
  dateTo.value = ''
  showBookmarkedOnly.value = false
  offset.value = 0
  updateUrl()
  fetchProjects()
}

// Shuffle projects (fetch in random order)
function shuffleProjects() {
  sortOrder.value = 'random'
  offset.value = 0
  fetchProjects()
}

// Refresh projects (reset to default sort)
function refreshProjects() {
  sortOrder.value = 'default'
  fetchProjects()
}

// View project details
function viewProject(projectId: number) {
  window.location.href = `/projects/${projectId}`
}

// Delete project
async function deleteProject(projectId: number) {
  if (deletingProjectId.value === projectId) return
  if (!btnFeedback.confirmOrProceed('delete-' + projectId)) return

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
    btnFeedback.showError('delete-' + projectId)
  } finally {
    deletingProjectId.value = null
  }
}

// Reprocess project (reprocess the source comment)
async function reprocessProject(project: WaywoProject) {
  if (reprocessingProjectId.value === project.id) return
  if (!btnFeedback.confirmOrProceed('reprocess-' + project.id)) return

  reprocessingProjectId.value = project.id

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-comments/${project.source_comment_id}/process`, {
      method: 'POST'
    })
    // Remove all projects with this source_comment_id from the local list
    const removedIds = projects.value.filter(p => p.source_comment_id === project.source_comment_id).map(p => p.id)
    projects.value = projects.value.filter(p => p.source_comment_id !== project.source_comment_id)
    total.value -= removedIds.length
    btnFeedback.showSuccess('reprocess-' + project.id)
  } catch (err) {
    console.error('Failed to reprocess project:', err)
    btnFeedback.showError('reprocess-' + project.id)
  } finally {
    reprocessingProjectId.value = null
  }
}

// Generate video for a project
async function generateVideoForProject(projectId: number) {
  if (generatingVideoProjectId.value === projectId) return

  generatingVideoProjectId.value = projectId

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-projects/${projectId}/generate-video`, {
      method: 'POST'
    })
    btnFeedback.showSuccess('genvideo-' + projectId)
  } catch (err) {
    console.error('Failed to generate video:', err)
    btnFeedback.showError('genvideo-' + projectId)
  } finally {
    generatingVideoProjectId.value = null
  }
}

// Toggle bookmark
async function toggleBookmark(projectId: number) {
  if (togglingBookmarkId.value === projectId) return

  togglingBookmarkId.value = projectId

  try {
    const response = await $fetch<{ is_bookmarked: boolean; project_id: number }>(
      `${config.public.apiBase}/api/waywo-projects/${projectId}/bookmark`,
      { method: 'POST' }
    )
    // Update local state
    const project = projects.value.find(p => p.id === projectId)
    if (project) {
      project.is_bookmarked = response.is_bookmarked
    }
    // Update bookmarked count
    bookmarkedCount.value += response.is_bookmarked ? 1 : -1

    // If viewing bookmarked only and we unbookmarked, remove from list
    if (showBookmarkedOnly.value && !response.is_bookmarked) {
      projects.value = projects.value.filter(p => p.id !== projectId)
      total.value -= 1
    }
  } catch (err) {
    console.error('Failed to toggle bookmark:', err)
  } finally {
    togglingBookmarkId.value = null
  }
}

// Toggle bookmarked filter
function toggleBookmarkedFilter() {
  showBookmarkedOnly.value = !showBookmarkedOnly.value
  offset.value = 0
  updateUrl()
  fetchProjects()
}

// Clear comment filter
function clearCommentFilter() {
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

// Initialize on mount
onMounted(() => {
  readFiltersFromUrl()
  fetchTags()
  fetchProjects()
})
</script>
