<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-destructive/10 mb-6">
          <Icon name="lucide:shield-alert" class="h-8 w-8 text-destructive" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Admin Panel</h1>
        <p class="text-xl text-muted-foreground">
          Database management and development tools
        </p>
      </div>

      <!-- Warning Banner -->
      <Alert variant="destructive" class="mb-8">
        <Icon name="lucide:alert-triangle" class="h-4 w-4" />
        <AlertTitle>Danger Zone</AlertTitle>
        <AlertDescription>
          Actions on this page will permanently delete data. Use with caution!
        </AlertDescription>
      </Alert>

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

      <!-- Reset Actions -->
      <Card class="p-6">
        <h2 class="text-xl font-semibold mb-4">Reset Actions</h2>

        <div class="space-y-4">
          <!-- Reset SQLite -->
          <div class="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <h3 class="font-medium flex items-center gap-2">
                <Icon name="lucide:database" class="h-5 w-5" />
                Reset SQLite Database
              </h3>
              <p class="text-sm text-muted-foreground mt-1">
                Delete all posts, comments, and projects from SQLite
              </p>
            </div>
            <Button
              variant="destructive"
              @click="resetSqlite"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'sqlite' ? 'lucide:loader-2' : 'lucide:trash-2'"
                :class="isResetting === 'sqlite' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Reset SQLite
            </Button>
          </div>

          <!-- Reset Redis -->
          <div class="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <h3 class="font-medium flex items-center gap-2">
                <Icon name="lucide:server" class="h-5 w-5" />
                Reset Redis
              </h3>
              <p class="text-sm text-muted-foreground mt-1">
                Flush all Redis keys including Celery task data
              </p>
            </div>
            <Button
              variant="destructive"
              @click="resetRedis"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'redis' ? 'lucide:loader-2' : 'lucide:trash-2'"
                :class="isResetting === 'redis' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Reset Redis
            </Button>
          </div>

          <!-- Reset All -->
          <div class="flex items-center justify-between p-4 border-2 border-destructive rounded-lg bg-destructive/5">
            <div>
              <h3 class="font-medium flex items-center gap-2 text-destructive">
                <Icon name="lucide:alert-octagon" class="h-5 w-5" />
                Reset Everything
              </h3>
              <p class="text-sm text-muted-foreground mt-1">
                Delete ALL data from both SQLite and Redis
              </p>
            </div>
            <Button
              variant="destructive"
              @click="resetAll"
              :disabled="isResetting"
            >
              <Icon
                :name="isResetting === 'all' ? 'lucide:loader-2' : 'lucide:bomb'"
                :class="isResetting === 'all' ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Reset All
            </Button>
          </div>
        </div>
      </Card>

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
const isLoadingStats = ref(false)
const isResetting = ref<string | null>(null)
const lastResult = ref<ResultMessage | null>(null)

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

// Fetch stats on mount
onMounted(() => {
  fetchStats()
})
</script>
