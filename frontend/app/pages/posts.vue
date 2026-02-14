<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <WaywoPageHeader
        icon="lucide:file-text"
        title="Waywo Posts"
        description='Monthly "What are you working on?" posts from Hacker News'
      />

      <!-- Chart -->
      <PostsChart ref="postsChartRef" class="mb-8" />

      <!-- Posts Table -->
      <Card class="p-6 mb-8">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-xl font-semibold">Stored Posts</h2>
          <div class="flex gap-2">
            <Dialog v-model:open="addDialogOpen">
              <DialogTrigger as-child>
                <Button>
                  <Icon name="lucide:plus" class="mr-2 h-4 w-4" />
                  Add Post
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add HN Post</DialogTitle>
                  <DialogDescription>
                    Paste a Hacker News "What are you working on?" post link. The year and month will be detected automatically, and all comments will be fetched.
                  </DialogDescription>
                </DialogHeader>
                <form @submit.prevent="submitAddPost" class="space-y-4">
                  <div class="space-y-2">
                    <label for="hn-url" class="text-sm font-medium">HN Post URL</label>
                    <Input
                      id="hn-url"
                      v-model="addPostUrl"
                      placeholder="https://news.ycombinator.com/item?id=..."
                      :disabled="isAdding"
                    />
                  </div>

                  <Alert v-if="addSuccess" class="border-green-200 bg-green-50">
                    <Icon name="lucide:check-circle" class="h-4 w-4 text-green-600" />
                    <AlertTitle class="text-green-800">Post Queued</AlertTitle>
                    <AlertDescription class="text-green-700">
                      {{ addSuccessMessage }}
                    </AlertDescription>
                  </Alert>

                  <Alert v-if="addError" variant="destructive">
                    <Icon name="lucide:alert-circle" class="h-4 w-4" />
                    <AlertTitle>Error</AlertTitle>
                    <AlertDescription>{{ addError }}</AlertDescription>
                  </Alert>

                  <DialogFooter>
                    <DialogClose as-child>
                      <Button type="button" variant="outline" :disabled="isAdding">Cancel</Button>
                    </DialogClose>
                    <Button type="submit" :disabled="isAdding || !addPostUrl.trim()">
                      <Icon
                        :name="isAdding ? 'lucide:loader-2' : 'lucide:download'"
                        :class="isAdding ? 'animate-spin' : ''"
                        class="mr-2 h-4 w-4"
                      />
                      {{ isAdding ? 'Adding...' : 'Add & Fetch Comments' }}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            <Button variant="outline" @click="fetchPosts" :disabled="isLoading">
              <Icon
                :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
                :class="isLoading ? 'animate-spin' : ''"
                class="mr-2 h-4 w-4"
              />
              Refresh
            </Button>
          </div>
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
            <TableRow
              v-for="post in posts"
              :key="post.id"
              class="cursor-pointer hover:bg-muted/50"
              @click="viewComments(post.id)"
            >
              <TableCell class="font-medium">
                {{ formatYearMonth(post.year, post.month) }}
              </TableCell>
              <TableCell>
                <a
                  :href="`https://news.ycombinator.com/item?id=${post.id}`"
                  target="_blank"
                  class="hover:underline text-primary"
                  @click.stop
                >
                  {{ post.title || `Post ${post.id}` }}
                </a>
              </TableCell>
              <TableCell class="text-right">
                {{ post.score ?? '-' }}
              </TableCell>
              <TableCell class="text-right">
                <a
                  :href="`/comments?post_id=${post.id}`"
                  @click.stop
                >
                  <Badge variant="secondary" class="hover:bg-primary hover:text-primary-foreground transition-colors">
                    {{ post.comment_count }}
                  </Badge>
                </a>
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

      <!-- Process Posts -->
      <Card class="p-6">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import PostsChart from '~/components/waywo/PostsChart.vue'
import type { WaywoPostSummary } from '~/types/models'

// Set page metadata
useHead({
  title: 'Posts - waywo',
  meta: [
    { name: 'description', content: 'View and manage Waywo posts from Hacker News.' }
  ]
})

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

// Add post dialog state
const addDialogOpen = ref(false)
const addPostUrl = ref('')
const isAdding = ref(false)
const addError = ref<string | null>(null)
const addSuccess = ref(false)
const addSuccessMessage = ref('')

watch(addDialogOpen, (open) => {
  if (!open) {
    addPostUrl.value = ''
    addError.value = null
    addSuccess.value = false
    addSuccessMessage.value = ''
  }
})

async function submitAddPost() {
  if (isAdding.value || !addPostUrl.value.trim()) return

  isAdding.value = true
  addError.value = null
  addSuccess.value = false

  try {
    const response = await $fetch<{ task_id: string; post_id: number; title: string; year: number; month: number; descendants: number }>(
      `${config.public.apiBase}/api/waywo-posts/add`,
      {
        method: 'POST',
        body: { url: addPostUrl.value.trim() },
      }
    )

    addSuccess.value = true
    addSuccessMessage.value = `"${response.title}" (${formatYearMonth(response.year, response.month)}) — fetching ${response.descendants ?? '?'} comments...`

    // Refresh posts list and chart after a delay
    setTimeout(() => {
      fetchPosts()
      postsChartRef.value?.refresh()
      addDialogOpen.value = false
    }, 2500)
  } catch (err: any) {
    const detail = err?.data?.detail || err?.message || 'Failed to add post'
    addError.value = detail
  } finally {
    isAdding.value = false
  }
}

// Navigate to comments page filtered by post
function viewComments(postId: number) {
  window.location.href = `/comments?post_id=${postId}`
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
