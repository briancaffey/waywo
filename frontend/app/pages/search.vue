<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:search" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Semantic Search</h1>
        <p class="text-xl text-muted-foreground">
          Find projects by meaning, not just keywords
        </p>
      </div>

      <!-- Search Box -->
      <Card class="p-6 mb-8">
        <form @submit.prevent="performSearch">
          <div class="flex gap-4">
            <Input
              v-model="query"
              type="text"
              placeholder="Search for projects... (e.g., 'AI tools for productivity')"
              class="flex-1"
              :disabled="isSearching"
            />
            <Button type="submit" :disabled="isSearching || !query.trim()">
              <Icon
                :name="isSearching ? 'lucide:loader-2' : 'lucide:search'"
                :class="isSearching ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              {{ isSearching ? 'Searching...' : 'Search' }}
            </Button>
          </div>
          <p class="text-sm text-muted-foreground mt-2">
            Uses AI embeddings to find semantically similar projects
          </p>
        </form>
      </Card>

      <!-- Stats Card -->
      <Card v-if="stats" class="p-4 mb-8">
        <div class="flex items-center justify-between text-sm">
          <div class="flex items-center gap-4">
            <div>
              <span class="text-muted-foreground">Searchable Projects:</span>
              <span class="font-semibold ml-1">{{ stats.projects_with_embeddings }}</span>
            </div>
            <div>
              <span class="text-muted-foreground">Coverage:</span>
              <span class="font-semibold ml-1">{{ stats.embedding_coverage }}%</span>
            </div>
          </div>
          <Badge v-if="embeddingHealthy" variant="outline" class="text-green-600">
            <Icon name="lucide:check-circle" class="h-3 w-3 mr-1" />
            Embedding Service Online
          </Badge>
          <Badge v-else variant="destructive">
            <Icon name="lucide:alert-circle" class="h-3 w-3 mr-1" />
            Embedding Service Offline
          </Badge>
        </div>
      </Card>

      <!-- Search Error -->
      <div v-if="searchError" class="mb-8">
        <Alert variant="destructive">
          <Icon name="lucide:alert-circle" class="h-4 w-4" />
          <AlertTitle>Search Error</AlertTitle>
          <AlertDescription>{{ searchError }}</AlertDescription>
        </Alert>
      </div>

      <!-- Search Results -->
      <div v-if="hasSearched">
        <div v-if="isSearching" class="flex justify-center py-12">
          <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
        </div>

        <div v-else-if="results.length === 0" class="text-center py-12">
          <Icon name="lucide:search-x" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p class="text-muted-foreground">No matching projects found</p>
          <p class="text-sm text-muted-foreground mt-2">
            Try a different search query or check if projects have embeddings
          </p>
        </div>

        <div v-else>
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold">
              {{ results.length }} Result{{ results.length === 1 ? '' : 's' }}
            </h2>
            <span class="text-sm text-muted-foreground">
              Query: "{{ lastQuery }}"
            </span>
          </div>

          <div class="space-y-4">
            <Card
              v-for="result in results"
              :key="result.project.id"
              class="p-6 cursor-pointer hover:border-primary/50 transition-colors"
              @click="viewProject(result.project.id)"
            >
              <div class="flex justify-between items-start mb-3">
                <div class="flex-1">
                  <div class="flex items-center gap-2 mb-1">
                    <h3 class="text-lg font-semibold">{{ result.project.title }}</h3>
                    <Badge
                      variant="secondary"
                      class="text-xs"
                      :class="getSimilarityClass(result.similarity)"
                    >
                      {{ formatSimilarity(result.similarity) }} match
                    </Badge>
                  </div>
                  <p class="text-muted-foreground">{{ result.project.short_description }}</p>
                </div>
                <div class="flex gap-2">
                  <Badge variant="outline" class="flex items-center gap-1">
                    <Icon name="lucide:lightbulb" class="h-3 w-3" />
                    {{ result.project.idea_score }}
                  </Badge>
                  <Badge variant="outline" class="flex items-center gap-1">
                    <Icon name="lucide:settings" class="h-3 w-3" />
                    {{ result.project.complexity_score }}
                  </Badge>
                </div>
              </div>

              <p class="text-sm text-muted-foreground mb-3">{{ result.project.description }}</p>

              <div class="flex flex-wrap gap-2">
                <Badge
                  v-for="tag in result.project.hashtags"
                  :key="tag"
                  variant="secondary"
                  class="text-xs"
                >
                  #{{ tag }}
                </Badge>
              </div>

              <div class="mt-4 pt-4 border-t flex items-center justify-between text-sm text-muted-foreground">
                <div class="flex items-center gap-2">
                  <Icon name="lucide:target" class="h-4 w-4" />
                  <span>Similarity: {{ (result.similarity * 100).toFixed(1) }}%</span>
                </div>
                <a
                  :href="`/projects/${result.project.id}`"
                  class="text-primary hover:underline flex items-center gap-1"
                  @click.stop
                >
                  View Details
                  <Icon name="lucide:arrow-right" class="h-3 w-3" />
                </a>
              </div>
            </Card>
          </div>
        </div>
      </div>

      <!-- Initial State -->
      <div v-else class="text-center py-12">
        <Icon name="lucide:sparkles" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p class="text-muted-foreground">Enter a search query to find similar projects</p>
        <p class="text-sm text-muted-foreground mt-2">
          Example: "machine learning tools", "web scraping", "productivity app"
        </p>
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

interface SearchResult {
  project: WaywoProject
  similarity: number
}

interface SearchStats {
  total_projects: number
  projects_with_embeddings: number
  embedding_coverage: number
}

// Set page metadata
useHead({
  title: 'Semantic Search - waywo',
  meta: [
    { name: 'description', content: 'Search projects using AI-powered semantic similarity.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const query = ref('')
const results = ref<SearchResult[]>([])
const isSearching = ref(false)
const searchError = ref<string | null>(null)
const hasSearched = ref(false)
const lastQuery = ref('')

// Stats
const stats = ref<SearchStats | null>(null)
const embeddingHealthy = ref(false)

// Format similarity percentage
function formatSimilarity(similarity: number): string {
  const percent = similarity * 100
  if (percent >= 90) return 'Excellent'
  if (percent >= 75) return 'Great'
  if (percent >= 60) return 'Good'
  if (percent >= 45) return 'Fair'
  return 'Partial'
}

// Get CSS class based on similarity
function getSimilarityClass(similarity: number): string {
  const percent = similarity * 100
  if (percent >= 75) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  if (percent >= 50) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
}

// Perform semantic search
async function performSearch() {
  if (!query.value.trim()) return

  isSearching.value = true
  searchError.value = null
  hasSearched.value = true
  lastQuery.value = query.value

  try {
    const response = await $fetch<{
      results: SearchResult[]
      query: string
      total: number
    }>(`${config.public.apiBase}/api/semantic-search`, {
      method: 'POST',
      body: {
        query: query.value,
        limit: 20
      }
    })
    results.value = response.results
  } catch (err: any) {
    console.error('Search failed:', err)
    searchError.value = err.data?.detail || 'Search failed. Please try again.'
    results.value = []
  } finally {
    isSearching.value = false
  }
}

// View project details
function viewProject(projectId: number) {
  window.location.href = `/projects/${projectId}`
}

// Fetch stats and health
async function fetchStats() {
  try {
    const [statsResponse, healthResponse] = await Promise.all([
      $fetch<SearchStats>(`${config.public.apiBase}/api/semantic-search/stats`),
      $fetch<{ status: string }>(`${config.public.apiBase}/api/embedding/health`).catch(() => ({ status: 'unhealthy' }))
    ])
    stats.value = statsResponse
    embeddingHealthy.value = healthResponse.status === 'healthy'
  } catch (err) {
    console.error('Failed to fetch stats:', err)
  }
}

// Fetch stats on mount
onMounted(() => {
  fetchStats()
})
</script>
