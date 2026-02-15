<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <WaywoPageHeader
        icon="lucide:settings-2"
        title="Admin Panel"
        description="System status and database management"
      />

      <!-- Services Health Card -->
      <Card class="p-6 mb-8">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-semibold">External Services</h2>
          <Button variant="outline" size="sm" @click="fetchServicesHealth" :disabled="isLoadingServices">
            <Icon
              :name="isLoadingServices ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoadingServices ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>

        <div v-if="isLoadingServices" class="flex justify-center py-8">
          <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
        </div>

        <div v-else-if="servicesHealth" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- LLM Server -->
          <div class="p-4 border rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <Icon
                :name="servicesHealth.llm?.status === 'healthy' ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="servicesHealth.llm?.status === 'healthy' ? 'text-green-500' : 'text-destructive'"
                class="h-5 w-5"
              />
              <span class="font-medium">LLM Server</span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p class="truncate" :title="servicesHealth.llm?.url">{{ servicesHealth.llm?.url }}</p>
              <p v-if="servicesHealth.llm?.status === 'healthy' && servicesHealth.llm?.configured_model">
                Model: <span class="font-mono text-xs">{{ servicesHealth.llm.configured_model }}</span>
              </p>
              <p v-if="servicesHealth.llm?.error" class="text-destructive">
                Error: {{ servicesHealth.llm.error }}
              </p>
            </div>
          </div>

          <!-- Embedder Server -->
          <div class="p-4 border rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <Icon
                :name="servicesHealth.embedder?.status === 'healthy' ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="servicesHealth.embedder?.status === 'healthy' ? 'text-green-500' : 'text-destructive'"
                class="h-5 w-5"
              />
              <span class="font-medium">Embedding Server</span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p class="truncate" :title="servicesHealth.embedder?.url">{{ servicesHealth.embedder?.url }}</p>
              <p v-if="servicesHealth.embedder?.error" class="text-destructive">
                Error: {{ servicesHealth.embedder.error }}
              </p>
            </div>
          </div>

          <!-- Reranker Server -->
          <div class="p-4 border rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <Icon
                :name="servicesHealth.reranker?.status === 'healthy' ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="servicesHealth.reranker?.status === 'healthy' ? 'text-green-500' : 'text-destructive'"
                class="h-5 w-5"
              />
              <span class="font-medium">Rerank Server</span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p class="truncate" :title="servicesHealth.reranker?.url">{{ servicesHealth.reranker?.url }}</p>
              <p v-if="servicesHealth.reranker?.status === 'healthy' && servicesHealth.reranker?.device">
                Device: <span class="font-mono text-xs">{{ servicesHealth.reranker.device }}</span>
              </p>
              <p v-if="servicesHealth.reranker?.error" class="text-destructive">
                Error: {{ servicesHealth.reranker.error }}
              </p>
            </div>
          </div>

          <!-- InvokeAI Server -->
          <div class="p-4 border rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <Icon
                :name="servicesHealth.invokeai?.status === 'healthy' ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="servicesHealth.invokeai?.status === 'healthy' ? 'text-green-500' : 'text-destructive'"
                class="h-5 w-5"
              />
              <span class="font-medium">InvokeAI</span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p class="truncate" :title="servicesHealth.invokeai?.url">{{ servicesHealth.invokeai?.url }}</p>
              <p v-if="servicesHealth.invokeai?.status === 'healthy' && servicesHealth.invokeai?.queue_size != null">
                Queue: <span class="font-mono text-xs">{{ servicesHealth.invokeai.queue_size }}</span>
              </p>
              <p v-if="servicesHealth.invokeai?.error" class="text-destructive">
                Error: {{ servicesHealth.invokeai.error }}
              </p>
            </div>
          </div>

          <!-- TTS Server -->
          <div class="p-4 border rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <Icon
                :name="servicesHealth.tts?.status === 'healthy' ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="servicesHealth.tts?.status === 'healthy' ? 'text-green-500' : 'text-destructive'"
                class="h-5 w-5"
              />
              <span class="font-medium">Text-to-Speech</span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p class="truncate" :title="servicesHealth.tts?.url">{{ servicesHealth.tts?.url }}</p>
              <p v-if="servicesHealth.tts?.status === 'healthy' && servicesHealth.tts?.voices != null">
                Voices: <span class="font-mono text-xs">{{ servicesHealth.tts.voices }}</span>
              </p>
              <p v-if="servicesHealth.tts?.error" class="text-destructive">
                Error: {{ servicesHealth.tts.error }}
              </p>
            </div>
          </div>

          <!-- STT Server -->
          <div class="p-4 border rounded-lg">
            <div class="flex items-center gap-2 mb-2">
              <Icon
                :name="servicesHealth.stt?.status === 'healthy' ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="servicesHealth.stt?.status === 'healthy' ? 'text-green-500' : 'text-destructive'"
                class="h-5 w-5"
              />
              <span class="font-medium">Speech-to-Text</span>
            </div>
            <div class="text-sm text-muted-foreground space-y-1">
              <p class="truncate" :title="servicesHealth.stt?.url">{{ servicesHealth.stt?.url }}</p>
              <p v-if="servicesHealth.stt?.error" class="text-destructive">
                Error: {{ servicesHealth.stt.error }}
              </p>
            </div>
          </div>
        </div>
      </Card>

      <!-- Stats Card -->
      <Card class="p-6 mb-8">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-semibold">Database Statistics</h2>
          <Button variant="outline" size="sm" @click="fetchStats" :disabled="isLoadingStats">
            <Icon
              :name="isLoadingStats ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoadingStats ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>

        <div v-if="isLoadingStats" class="flex justify-center py-8">
          <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
        </div>

        <div v-else-if="stats" class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <!-- SQLite Stats -->
          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:database" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Posts</span>
            </div>
            <p class="text-2xl font-bold">{{ stats.posts_count }}</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:message-square" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Comments</span>
            </div>
            <p class="text-2xl font-bold">{{ stats.comments_count }}</p>
            <p class="text-xs text-muted-foreground">{{ stats.processed_comments_count }} processed</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:lightbulb" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Projects</span>
            </div>
            <p class="text-2xl font-bold">{{ stats.projects_count }}</p>
            <p class="text-xs text-muted-foreground">{{ stats.valid_projects_count }} valid</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:brain" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Embeddings</span>
            </div>
            <p class="text-2xl font-bold">{{ stats.projects_with_embeddings_count }}</p>
          </div>

          <!-- Redis Stats -->
          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:server" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Redis Keys</span>
            </div>
            <p class="text-2xl font-bold">{{ stats.redis_keys_count }}</p>
            <p class="text-xs text-muted-foreground">{{ stats.redis_memory_used }} memory</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon
                :name="stats.redis_connected ? 'lucide:check-circle' : 'lucide:x-circle'"
                :class="stats.redis_connected ? 'text-green-500' : 'text-destructive'"
                class="h-4 w-4"
              />
              <span class="text-sm text-muted-foreground">Redis Status</span>
            </div>
            <p class="text-2xl font-bold">{{ stats.redis_connected ? 'Connected' : 'Disconnected' }}</p>
          </div>
        </div>
      </Card>

      <!-- Celery Tasks Card -->
      <Card class="p-6 mb-8">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-semibold">Celery Tasks</h2>
          <Button variant="outline" size="sm" @click="fetchCeleryStats" :disabled="isLoadingCelery">
            <Icon
              :name="isLoadingCelery ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoadingCelery ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>

        <div v-if="isLoadingCelery && !celeryStats" class="flex justify-center py-8">
          <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
        </div>

        <div v-else-if="celeryStats" class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:play" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Active</span>
            </div>
            <p class="text-2xl font-bold">{{ celeryStats.active }}</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:pause" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Reserved</span>
            </div>
            <p class="text-2xl font-bold">{{ celeryStats.reserved }}</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:list" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Queued</span>
            </div>
            <p class="text-2xl font-bold">{{ celeryStats.queued }}</p>
          </div>

          <div class="p-4 bg-muted rounded-lg">
            <div class="flex items-center gap-2 mb-1">
              <Icon name="lucide:cpu" class="h-4 w-4 text-muted-foreground" />
              <span class="text-sm text-muted-foreground">Workers</span>
            </div>
            <p class="text-2xl font-bold">{{ celeryStats.worker_count }}</p>
          </div>
        </div>
      </Card>

      <!-- Maintenance Actions -->
      <Card class="p-6 mb-8">
        <h2 class="text-xl font-semibold mb-4">Maintenance</h2>

        <!-- View Workflow Prompts -->
        <a href="/prompts" class="flex items-center justify-between p-4 border rounded-lg mb-4 hover:bg-accent transition-colors">
          <div class="flex items-center gap-3">
            <Icon name="lucide:file-text" class="h-5 w-5 text-muted-foreground" />
            <div>
              <h3 class="font-medium">Workflow Prompts</h3>
              <p class="text-sm text-muted-foreground">
                View and inspect all prompt templates used in the processing pipeline
              </p>
            </div>
          </div>
          <Icon name="lucide:arrow-right" class="h-5 w-5 text-muted-foreground" />
        </a>

        <div class="flex items-center justify-between p-4 border rounded-lg mb-4">
          <div class="flex items-center gap-3">
            <Icon name="lucide:search" class="h-5 w-5 text-muted-foreground" />
            <div>
              <h3 class="font-medium">Rebuild Vector Index</h3>
              <p class="text-sm text-muted-foreground">
                Rebuild the search index after adding new embeddings
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            @click="rebuildVectorIndex"
            :disabled="isRebuilding"
          >
            <Icon
              :name="isRebuilding ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isRebuilding ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Rebuild
          </Button>
        </div>

        <div class="flex items-center justify-between p-4 border rounded-lg">
          <div class="flex items-center gap-3">
            <Icon name="lucide:scatter-chart" class="h-5 w-5 text-muted-foreground" />
            <div>
              <h3 class="font-medium">Compute Clusters</h3>
              <p class="text-sm text-muted-foreground">
                Run UMAP + HDBSCAN to generate the project cluster map
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            @click="computeClusters"
            :disabled="isComputingClusters"
          >
            <Icon
              :name="isComputingClusters ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isComputingClusters ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Compute
          </Button>
        </div>
      </Card>

      <!-- Danger Zone -->
      <div class="mt-4">
        <div class="flex items-center gap-3 mb-4">
          <div class="flex items-center justify-center w-10 h-10 rounded-full bg-destructive/10">
            <Icon name="lucide:alert-triangle" class="h-5 w-5 text-destructive" />
          </div>
          <div>
            <h2 class="text-xl font-semibold text-destructive">Danger Zone</h2>
            <p class="text-sm text-muted-foreground">Destructive actions that cannot be undone</p>
          </div>
        </div>

        <div class="border-2 border-destructive/30 rounded-lg overflow-hidden">
          <!-- Reset SQLite -->
          <div class="flex items-center justify-between p-4 bg-background hover:bg-destructive/5 transition-colors">
            <div class="flex items-center gap-3">
              <Icon name="lucide:database" class="h-5 w-5 text-muted-foreground" />
              <div>
                <h3 class="font-medium">Reset SQLite Database</h3>
                <p class="text-sm text-muted-foreground">
                  Delete all posts, comments, and projects
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              :class="[
                btnFeedback.getFeedback('reset-sqlite') === 'confirming'
                  ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90 border-destructive'
                  : 'border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground'
              ]"
              @click="resetSqlite"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'sqlite' ? 'lucide:loader-2' : btnFeedback.getFeedback('reset-sqlite') === 'confirming' ? 'lucide:alert-triangle' : 'lucide:trash-2'"
                :class="isResetting === 'sqlite' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              {{ btnFeedback.getFeedback('reset-sqlite') === 'confirming' ? 'Sure?' : 'Reset' }}
            </Button>
          </div>

          <Separator />

          <!-- Reset Redis -->
          <div class="flex items-center justify-between p-4 bg-background hover:bg-destructive/5 transition-colors">
            <div class="flex items-center gap-3">
              <Icon name="lucide:server" class="h-5 w-5 text-muted-foreground" />
              <div>
                <h3 class="font-medium">Reset Redis</h3>
                <p class="text-sm text-muted-foreground">
                  Flush all keys including Celery task data
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              :class="[
                btnFeedback.getFeedback('reset-redis') === 'confirming'
                  ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90 border-destructive'
                  : 'border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground'
              ]"
              @click="resetRedis"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'redis' ? 'lucide:loader-2' : btnFeedback.getFeedback('reset-redis') === 'confirming' ? 'lucide:alert-triangle' : 'lucide:trash-2'"
                :class="isResetting === 'redis' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              {{ btnFeedback.getFeedback('reset-redis') === 'confirming' ? 'Sure?' : 'Reset' }}
            </Button>
          </div>

          <Separator />

          <!-- Reset All -->
          <div class="flex items-center justify-between p-4 bg-destructive/5">
            <div class="flex items-center gap-3">
              <Icon name="lucide:bomb" class="h-5 w-5 text-destructive" />
              <div>
                <h3 class="font-medium text-destructive">Reset Everything</h3>
                <p class="text-sm text-muted-foreground">
                  Delete ALL data from both SQLite and Redis
                </p>
              </div>
            </div>
            <Button
              variant="destructive"
              @click="resetAll"
              :disabled="isResetting"
              :class="{
                'bg-destructive/80 animate-pulse': btnFeedback.getFeedback('reset-all') === 'confirming',
              }"
            >
              <Icon
                :name="isResetting === 'all' ? 'lucide:loader-2' : btnFeedback.getFeedback('reset-all') === 'confirming' ? 'lucide:alert-triangle' : 'lucide:flame'"
                :class="isResetting === 'all' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              {{ btnFeedback.getFeedback('reset-all') === 'confirming' ? 'Click again to confirm' : 'Reset All' }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Result Messages -->
      <div v-if="lastResult" class="mt-6">
        <Alert :variant="lastResult.success ? 'default' : 'destructive'">
          <Icon :name="lastResult.success ? 'lucide:check-circle' : 'lucide:x-circle'" class="h-4 w-4" />
          <AlertTitle>{{ lastResult.success ? 'Success' : 'Error' }}</AlertTitle>
          <AlertDescription>
            {{ lastResult.message }}
            <div v-if="lastResult.details" class="mt-2 text-xs font-mono bg-muted p-2 rounded">
              <pre>{{ JSON.stringify(lastResult.details, null, 2) }}</pre>
            </div>
          </AlertDescription>
        </Alert>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CeleryStats, DatabaseStats, ServicesHealth, ResultMessage } from '~/types/models'

// Set page metadata
useHead({
  title: 'Admin - waywo',
  meta: [
    { name: 'description', content: 'Admin panel for database management.' }
  ]
})

const config = useRuntimeConfig()

// Reactive state
const stats = ref<DatabaseStats | null>(null)
const servicesHealth = ref<ServicesHealth | null>(null)
const isLoadingStats = ref(false)
const isLoadingServices = ref(false)
const isResetting = ref<string | null>(null)
const isRebuilding = ref(false)
const isComputingClusters = ref(false)
const celeryStats = ref<CeleryStats | null>(null)
const isLoadingCelery = ref(false)
let celeryPollInterval: ReturnType<typeof setInterval> | null = null
const lastResult = ref<ResultMessage | null>(null)
const btnFeedback = useButtonFeedback()

// Fetch services health
async function fetchServicesHealth() {
  isLoadingServices.value = true
  try {
    servicesHealth.value = await $fetch<ServicesHealth>(`${config.public.apiBase}/api/admin/services-health`)
  } catch (err) {
    console.error('Failed to fetch services health:', err)
  } finally {
    isLoadingServices.value = false
  }
}

// Fetch database stats
async function fetchStats() {
  isLoadingStats.value = true
  try {
    stats.value = await $fetch<DatabaseStats>(`${config.public.apiBase}/api/admin/stats`)
  } catch (err) {
    console.error('Failed to fetch stats:', err)
  } finally {
    isLoadingStats.value = false
  }
}

// Fetch celery stats
async function fetchCeleryStats() {
  isLoadingCelery.value = true
  try {
    celeryStats.value = await $fetch<CeleryStats>(`${config.public.apiBase}/api/admin/celery-stats`)
    // Auto-poll when there are active or queued tasks
    if (celeryStats.value.active > 0 || celeryStats.value.queued > 0 || celeryStats.value.reserved > 0) {
      startCeleryPolling()
    } else {
      stopCeleryPolling()
    }
  } catch (err) {
    console.error('Failed to fetch celery stats:', err)
  } finally {
    isLoadingCelery.value = false
  }
}

function startCeleryPolling() {
  if (celeryPollInterval) return
  celeryPollInterval = setInterval(fetchCeleryStats, 3000)
}

function stopCeleryPolling() {
  if (celeryPollInterval) {
    clearInterval(celeryPollInterval)
    celeryPollInterval = null
  }
}

// Rebuild vector index
async function rebuildVectorIndex() {
  isRebuilding.value = true
  lastResult.value = null

  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/rebuild-vector-index`, {
      method: 'POST'
    })
    lastResult.value = {
      success: true,
      message: response.message || 'Vector index rebuilt successfully'
    }
  } catch (err: any) {
    lastResult.value = {
      success: false,
      message: err.data?.detail || 'Failed to rebuild vector index'
    }
  } finally {
    isRebuilding.value = false
  }
}

// Compute Clusters
async function computeClusters() {
  isComputingClusters.value = true
  lastResult.value = null

  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/compute-clusters`, {
      method: 'POST'
    })
    lastResult.value = {
      success: true,
      message: response.message || 'Clusters computed successfully',
      details: { projects_updated: response.projects_updated }
    }
  } catch (err: any) {
    lastResult.value = {
      success: false,
      message: err.data?.detail || 'Failed to compute clusters'
    }
  } finally {
    isComputingClusters.value = false
  }
}

// Reset SQLite
async function resetSqlite() {
  if (!btnFeedback.confirmOrProceed('reset-sqlite')) return

  isResetting.value = 'sqlite'
  lastResult.value = null

  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/reset-sqlite`, {
      method: 'DELETE'
    })
    lastResult.value = {
      success: true,
      message: 'SQLite database has been reset',
      details: response
    }
    fetchStats()
  } catch (err: any) {
    lastResult.value = {
      success: false,
      message: err.data?.detail || 'Failed to reset SQLite database'
    }
  } finally {
    isResetting.value = null
  }
}

// Reset Redis
async function resetRedis() {
  if (!btnFeedback.confirmOrProceed('reset-redis')) return

  isResetting.value = 'redis'
  lastResult.value = null

  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/reset-redis`, {
      method: 'DELETE'
    })
    lastResult.value = {
      success: true,
      message: 'Redis has been flushed',
      details: response
    }
    fetchStats()
  } catch (err: any) {
    lastResult.value = {
      success: false,
      message: err.data?.detail || 'Failed to flush Redis'
    }
  } finally {
    isResetting.value = null
  }
}

// Reset All (two-click confirm)
async function resetAll() {
  if (!btnFeedback.confirmOrProceed('reset-all', 5000)) return

  isResetting.value = 'all'
  lastResult.value = null

  try {
    const response = await $fetch<any>(`${config.public.apiBase}/api/admin/reset-all`, {
      method: 'DELETE'
    })
    lastResult.value = {
      success: response.status === 'success',
      message: response.message,
      details: response.results
    }
    fetchStats()
  } catch (err: any) {
    lastResult.value = {
      success: false,
      message: err.data?.detail || 'Failed to reset databases'
    }
  } finally {
    isResetting.value = null
  }
}

// Fetch data on mount
onMounted(() => {
  fetchServicesHealth()
  fetchStats()
  fetchCeleryStats()
})

onUnmounted(() => {
  stopCeleryPolling()
})
</script>
