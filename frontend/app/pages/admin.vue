<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:settings-2" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Admin Panel</h1>
        <p class="text-xl text-muted-foreground">
          System status and database management
        </p>
      </div>

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

        <div v-else-if="servicesHealth" class="grid grid-cols-1 md:grid-cols-2 gap-4">
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

        <div class="flex items-center justify-between p-4 border rounded-lg">
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
              class="border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground"
              @click="resetSqlite"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'sqlite' ? 'lucide:loader-2' : 'lucide:trash-2'"
                :class="isResetting === 'sqlite' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Reset
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
              class="border-destructive text-destructive hover:bg-destructive hover:text-destructive-foreground"
              @click="resetRedis"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'redis' ? 'lucide:loader-2' : 'lucide:trash-2'"
                :class="isResetting === 'redis' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Reset
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
            >
              <Icon
                :name="isResetting === 'all' ? 'lucide:loader-2' : 'lucide:flame'"
                :class="isResetting === 'all' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Reset All
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
interface DatabaseStats {
  posts_count: number
  comments_count: number
  projects_count: number
  processed_comments_count: number
  valid_projects_count: number
  projects_with_embeddings_count: number
  redis_keys_count: number
  redis_memory_used: string
  redis_connected: boolean
}

interface ServiceHealth {
  status: 'healthy' | 'unhealthy'
  url: string
  error?: string
  configured_model?: string
  available_models?: string[]
}

interface ServicesHealth {
  llm: ServiceHealth
  embedder: ServiceHealth
}

interface ResultMessage {
  success: boolean
  message: string
  details?: any
}

// Set page metadata
useHead({
  title: 'Admin - waywo',
  meta: [
    { name: 'description', content: 'Admin panel for database management.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const stats = ref<DatabaseStats | null>(null)
const servicesHealth = ref<ServicesHealth | null>(null)
const isLoadingStats = ref(false)
const isLoadingServices = ref(false)
const isResetting = ref<string | null>(null)
const isRebuilding = ref(false)
const lastResult = ref<ResultMessage | null>(null)

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

// Reset SQLite
async function resetSqlite() {
  if (!confirm('Are you sure you want to delete ALL data from SQLite?\n\nThis will delete all posts, comments, and projects!')) {
    return
  }

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
  if (!confirm('Are you sure you want to flush ALL Redis data?\n\nThis will delete all Celery task history!')) {
    return
  }

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

// Reset All
async function resetAll() {
  if (!confirm('ARE YOU ABSOLUTELY SURE?\n\nThis will delete ALL data from BOTH SQLite AND Redis!\n\nType "yes" in the next prompt to confirm.')) {
    return
  }

  const confirmation = prompt('Type "yes" to confirm deletion of ALL data:')
  if (confirmation !== 'yes') {
    lastResult.value = {
      success: false,
      message: 'Reset cancelled - confirmation not provided'
    }
    return
  }

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
})
</script>
