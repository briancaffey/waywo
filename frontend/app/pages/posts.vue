<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:file-text" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Waywo Posts</h1>
        <p class="text-xl text-muted-foreground">
          Monthly "What are you working on?" posts from Hacker News
        </p>
      </div>

      <!-- Controls -->
      <Card class="p-6 mb-8">
        <div class="flex flex-col sm:flex-row gap-4 items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold">Process Posts</h2>
            <p class="text-sm text-muted-foreground">
              Fetch and store posts from Hacker News API
            </p>
          </div>
          <div class="flex gap-4 items-center">
            <div class="flex gap-2 items-center">
              <label class="text-sm font-medium">Limit Posts:</label>
              <Input
                v-model="limitPosts"
                type="number"
                class="w-20"
                min="1"
                placeholder="All"
              />
            </div>
            <div class="flex gap-2 items-center">
              <label class="text-sm font-medium">Limit Comments:</label>
              <Input
                v-model="limitComments"
                type="number"
                class="w-20"
                min="1"
                placeholder="All"
              />
            </div>
            <Button
              @click="triggerProcessPosts"
              :disabled="isProcessing"
            >
              <Icon
                :name="isProcessing ? 'lucide:loader-2' : 'lucide:download'"
                :class="isProcessing ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              {{ isProcessing ? 'Processing...' : 'Process Posts' }}
            </Button>
          </div>
        </div>

        <!-- Status Messages -->
        <Alert v-if="processSuccess" class="mt-4 border-green-200 bg-green-50">
          <Icon name="lucide:check-circle" class="h-4 w-4 text-green-600" />
          <AlertTitle class="text-green-800">Task Queued</AlertTitle>
          <AlertDescription class="text-green-700">
            Processing task has been queued. Task ID: {{ taskId }}
          </AlertDescription>
        </Alert>

        <Alert v-if="processError" variant="destructive" class="mt-4">
          <Icon name="lucide:alert-circle" class="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{{ processError }}</AlertDescription>
        </Alert>
      </Card>

      <!-- Chart -->
      <PostsChart ref="postsChartRef" class="mb-8" />

      <!-- Posts Table -->
      <Card class="p-6">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-xl font-semibold">Stored Posts</h2>
          <Button variant="outline" @click="fetchPosts" :disabled="isLoading">
            <Icon
              :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoading ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>

        <div v-if="isLoading" class="flex justify-center py-12">
          <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
        </div>

        <div v-else-if="fetchError" class="text-center py-12">
          <Icon name="lucide:alert-circle" class="h-12 w-12 text-destructive mx-auto mb-4" />
          <p class="text-destructive">{{ fetchError }}</p>
          <Button variant="outline" @click="fetchPosts" class="mt-4">
            Try Again
          </Button>
        </div>

        <div v-else-if="posts.length === 0" class="text-center py-12">
          <Icon name="lucide:inbox" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <p class="text-muted-foreground">No posts stored yet</p>
          <p class="text-sm text-muted-foreground mt-2">
            Click "Process Posts" to fetch posts from Hacker News
          </p>
        </div>

        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Title</TableHead>
              <TableHead class="text-right">Score</TableHead>
              <TableHead class="text-right">Comments Stored</TableHead>
              <TableHead class="text-right">Total Comments</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="post in posts" :key="post.id">
              <TableCell class="font-medium">
                {{ formatDate(post.year, post.month) }}
              </TableCell>
              <TableCell>
                <a
                  :href="`https://news.ycombinator.com/item?id=${post.id}`"
                  target="_blank"
                  class="hover:underline text-primary"
                >
                  {{ post.title || `Post ${post.id}` }}
                </a>
              </TableCell>
              <TableCell class="text-right">
                {{ post.score ?? '-' }}
              </TableCell>
              <TableCell class="text-right">
                <Badge variant="secondary">
                  {{ post.comment_count }}
                </Badge>
              </TableCell>
              <TableCell class="text-right text-muted-foreground">
                {{ post.descendants ?? '-' }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <div v-if="posts.length > 0" class="mt-4 text-sm text-muted-foreground text-right">
          {{ posts.length }} posts stored
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import PostsChart from '~/components/waywo/PostsChart.vue'

interface WaywoPostSummary {
  id: number
  title: string | null
  year: number | null
  month: number | null
  score: number | null
  comment_count: number
  descendants: number | null
}

// Set page metadata
useHead({
  title: 'Posts - waywo',
  meta: [
    { name: 'description', content: 'View and manage Waywo posts from Hacker News.' }
  ]
})

// Get runtime config for API base URL
const config = useRuntimeConfig()

// Reactive state
const posts = ref<WaywoPostSummary[]>([])
const isLoading = ref(false)
const fetchError = ref<string | null>(null)

const isProcessing = ref(false)
const processError = ref<string | null>(null)
const processSuccess = ref(false)
const taskId = ref<string | null>(null)

const limitPosts = ref<number | undefined>(undefined)
const limitComments = ref<number | undefined>(undefined)

// Chart ref
const postsChartRef = ref<{ refresh: () => void } | null>(null)

// Format date from year/month
function formatDate(year: number | null, month: number | null): string {
  if (!year || !month) return 'Unknown'
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${monthNames[month - 1]} ${year}`
}

// Fetch posts from API
async function fetchPosts() {
  isLoading.value = true
  fetchError.value = null

  try {
    const response = await $fetch<WaywoPostSummary[]>(`${config.public.apiBase}/api/waywo-posts`)
    posts.value = response
  } catch (err) {
    console.error('Failed to fetch posts:', err)
    fetchError.value = 'Failed to fetch posts. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
}

// Trigger processing of posts
async function triggerProcessPosts() {
  if (isProcessing.value) return

  isProcessing.value = true
  processError.value = null
  processSuccess.value = false
  taskId.value = null

  try {
    const body: Record<string, number | undefined> = {}
    if (limitPosts.value) body.limit_posts = limitPosts.value
    if (limitComments.value) body.limit_comments = limitComments.value

    const response = await $fetch<{ task_id: string; status: string }>(
      `${config.public.apiBase}/api/process-waywo-posts`,
      {
        method: 'POST',
        body
      }
    )

    taskId.value = response.task_id
    processSuccess.value = true

    // Refresh posts and chart after a short delay
    setTimeout(() => {
      fetchPosts()
      postsChartRef.value?.refresh()
    }, 2000)
  } catch (err) {
    console.error('Failed to trigger processing:', err)
    processError.value = 'Failed to trigger processing. Make sure the backend is running.'
  } finally {
    isProcessing.value = false
  }
}

// Fetch posts on mount
onMounted(() => {
  fetchPosts()
})
</script>
