<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-6xl mx-auto">
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

          <!-- Search Options -->
          <div class="flex items-center gap-6 mt-4 pt-4 border-t">
            <div class="flex items-center gap-2">
              <Switch id="use-rerank" v-model:checked="useRerank" />
              <label for="use-rerank" class="text-sm cursor-pointer">
                Use Rerank
              </label>
              <span class="text-xs text-muted-foreground">(improves relevance)</span>
            </div>

            <div v-if="useRerank" class="flex items-center gap-2">
              <Switch id="compare-mode" v-model:checked="compareMode" />
              <label for="compare-mode" class="text-sm cursor-pointer">
                Compare Mode
              </label>
              <span class="text-xs text-muted-foreground">(show side-by-side)</span>
            </div>
          </div>
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
          <div class="flex items-center gap-2">
            <Badge v-if="embeddingHealthy" variant="outline" class="text-green-600">
              <Icon name="lucide:check-circle" class="h-3 w-3 mr-1" />
              Embedding
            </Badge>
            <Badge v-else variant="destructive">
              <Icon name="lucide:alert-circle" class="h-3 w-3 mr-1" />
              Embedding Offline
            </Badge>
            <Badge v-if="rerankHealthy" variant="outline" class="text-green-600">
              <Icon name="lucide:check-circle" class="h-3 w-3 mr-1" />
              Rerank
            </Badge>
            <Badge v-else variant="outline" class="text-yellow-600">
              <Icon name="lucide:alert-circle" class="h-3 w-3 mr-1" />
              Rerank Offline
            </Badge>
          </div>
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
          <!-- Results Header -->
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold">
              {{ results.length }} Result{{ results.length === 1 ? '' : 's' }}
              <Badge v-if="wasReranked" variant="secondary" class="ml-2">
                <Icon name="lucide:sparkles" class="h-3 w-3 mr-1" />
                Reranked
              </Badge>
            </h2>
            <span class="text-sm text-muted-foreground">
              Query: "{{ lastQuery }}"
            </span>
          </div>

          <!-- Compare Mode: Side-by-Side -->
          <div v-if="compareMode && wasReranked && originalResults.length > 0" class="grid grid-cols-2 gap-6">
            <!-- Original Results Column -->
            <div>
              <div class="flex items-center gap-2 mb-4 pb-2 border-b">
                <Icon name="lucide:list-ordered" class="h-5 w-5 text-muted-foreground" />
                <h3 class="font-semibold">By Similarity</h3>
                <span class="text-xs text-muted-foreground">(embedding distance)</span>
              </div>
              <div class="space-y-4">
                <SearchResultCard
                  v-for="(result, index) in originalResults"
                  :key="`original-${result.project.id}`"
                  :result="result"
                  :rank="index + 1"
                  :show-rerank-score="false"
                  @click="viewProject(result.project.id)"
                />
              </div>
            </div>

            <!-- Reranked Results Column -->
            <div>
              <div class="flex items-center gap-2 mb-4 pb-2 border-b">
                <Icon name="lucide:sparkles" class="h-5 w-5 text-primary" />
                <h3 class="font-semibold">By Relevance</h3>
                <span class="text-xs text-muted-foreground">(reranked)</span>
              </div>
              <div class="space-y-4">
                <SearchResultCard
                  v-for="(result, index) in results"
                  :key="`reranked-${result.project.id}`"
                  :result="result"
                  :rank="index + 1"
                  :show-rerank-score="true"
                  @click="viewProject(result.project.id)"
                />
              </div>
            </div>
          </div>

          <!-- Standard Results (Single Column) -->
          <div v-else class="space-y-4">
            <SearchResultCard
              v-for="(result, index) in results"
              :key="result.project.id"
              :result="result"
              :rank="index + 1"
              :show-rerank-score="wasReranked"
              @click="viewProject(result.project.id)"
            />
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
  rerank_score?: number
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
const originalResults = ref<SearchResult[]>([])
const isSearching = ref(false)
const searchError = ref<string | null>(null)
const hasSearched = ref(false)
const lastQuery = ref('')
const wasReranked = ref(false)

// Search options
const useRerank = ref(true)
const compareMode = ref(false)

// Stats
const stats = ref<SearchStats | null>(null)
const embeddingHealthy = ref(false)
const rerankHealthy = ref(false)

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
      original_results?: SearchResult[]
      query: string
      total: number
      reranked: boolean
    }>(`${config.public.apiBase}/api/semantic-search`, {
      method: 'POST',
      body: {
        query: query.value,
        limit: 10,
        use_rerank: useRerank.value
      }
    })
    results.value = response.results
    originalResults.value = response.original_results || []
    wasReranked.value = response.reranked
  } catch (err: any) {
    console.error('Search failed:', err)
    searchError.value = err.data?.detail || 'Search failed. Please try again.'
    results.value = []
    originalResults.value = []
    wasReranked.value = false
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
    const [statsResponse, embeddingHealth, rerankHealth] = await Promise.all([
      $fetch<SearchStats>(`${config.public.apiBase}/api/semantic-search/stats`),
      $fetch<{ status: string }>(`${config.public.apiBase}/api/embedding/health`).catch(() => ({ status: 'unhealthy' })),
      $fetch<{ status: string }>(`${config.public.apiBase}/api/rerank/health`).catch(() => ({ status: 'unhealthy' }))
    ])
    stats.value = statsResponse
    embeddingHealthy.value = embeddingHealth.status === 'healthy'
    rerankHealthy.value = rerankHealth.status === 'healthy'
  } catch (err) {
    console.error('Failed to fetch stats:', err)
  }
}

// Fetch stats on mount
onMounted(() => {
  fetchStats()
})
</script>
