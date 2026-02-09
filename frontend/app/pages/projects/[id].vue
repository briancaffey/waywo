<template>
  <div class="container mx-auto px-4 py-8 md:py-12">
    <div class="max-w-4xl mx-auto">
      <!-- Loading State -->
      <div v-if="isLoading" class="flex justify-center py-20">
        <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <!-- Error State -->
      <div v-else-if="fetchError" class="text-center py-20">
        <Icon name="lucide:alert-circle" class="h-12 w-12 text-destructive mx-auto mb-4" />
        <p class="text-destructive text-lg">{{ fetchError }}</p>
        <a href="/projects">
          <Button variant="outline" class="mt-6">
            <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
            Back to Projects
          </Button>
        </a>
      </div>

      <!-- Project Details -->
      <div v-else-if="project">
        <!-- Breadcrumb -->
        <a href="/projects" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8">
          <Icon name="lucide:arrow-left" class="h-4 w-4" />
          All Projects
        </a>

        <!-- Hero Header -->
        <div class="mb-10">
          <!-- Invalid Alert (top of header) -->
          <Alert v-if="!project.is_valid_project && project.invalid_reason" variant="destructive" class="mb-6">
            <Icon name="lucide:alert-circle" class="h-4 w-4" />
            <AlertTitle>Invalid Project</AlertTitle>
            <AlertDescription>{{ project.invalid_reason }}</AlertDescription>
          </Alert>

          <!-- Title Row -->
          <div class="flex items-start gap-4 mb-3">
            <button
              @click="toggleBookmark"
              :disabled="isTogglingBookmark"
              class="mt-1 hover:scale-110 transition-transform flex-shrink-0"
              :title="project.is_bookmarked ? 'Remove bookmark' : 'Add bookmark'"
            >
              <Icon
                name="lucide:star"
                :class="[
                  'h-8 w-8 transition-colors',
                  project.is_bookmarked ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground/40 hover:text-yellow-500',
                  isTogglingBookmark ? 'animate-pulse' : ''
                ]"
              />
            </button>
            <div class="min-w-0">
              <div class="flex items-center gap-3 flex-wrap">
                <h1 class="text-5xl md:text-6xl font-bold tracking-tight">{{ project.title }}</h1>
                <Badge v-if="!project.is_valid_project" variant="destructive" class="text-xs">
                  Invalid
                </Badge>
              </div>
              <p class="text-lg md:text-xl text-muted-foreground mt-2 leading-relaxed">{{ project.short_description }}</p>
              <a
                v-if="project.primary_url"
                :href="project.primary_url"
                target="_blank"
                class="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mt-2"
              >
                <Icon name="lucide:external-link" class="h-3.5 w-3.5" />
                {{ project.primary_url }}
              </a>
            </div>
          </div>

          <!-- Score Cards -->
          <div class="grid grid-cols-2 gap-4 mt-8 mb-6">
            <div class="relative overflow-hidden rounded-xl border bg-gradient-to-br from-amber-500/5 to-orange-500/10 dark:from-amber-500/10 dark:to-orange-500/5 p-5">
              <div class="flex items-center gap-3">
                <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-amber-500/10 dark:bg-amber-500/20">
                  <Icon name="lucide:lightbulb" class="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <div class="text-sm font-medium text-muted-foreground">Idea Score</div>
                  <div class="text-3xl font-bold tracking-tight">{{ project.idea_score }}<span class="text-base font-normal text-muted-foreground">/10</span></div>
                </div>
              </div>
            </div>
            <div class="relative overflow-hidden rounded-xl border bg-gradient-to-br from-blue-500/5 to-indigo-500/10 dark:from-blue-500/10 dark:to-indigo-500/5 p-5">
              <div class="flex items-center gap-3">
                <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-500/10 dark:bg-blue-500/20">
                  <Icon name="lucide:gauge" class="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <div class="text-sm font-medium text-muted-foreground">Complexity</div>
                  <div class="text-3xl font-bold tracking-tight">{{ project.complexity_score }}<span class="text-base font-normal text-muted-foreground">/10</span></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Tags -->
          <div v-if="project.hashtags?.length" class="flex flex-wrap gap-2 mb-6">
            <Badge
              v-for="tag in project.hashtags"
              :key="tag"
              variant="secondary"
              class="px-3 py-1"
            >
              #{{ tag }}
            </Badge>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center gap-1">
            <a
              :href="`https://news.ycombinator.com/item?id=${project.source_comment_id}`"
              target="_blank"
              class="inline-flex items-center justify-center h-8 px-3 rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors gap-1.5"
            >
              <span class="inline-flex items-center justify-center w-4 h-4 rounded-sm bg-orange-500 text-white text-[10px] font-bold leading-none">Y</span>
              HN
            </a>
            <Button
              variant="ghost"
              size="sm"
              @click="reprocessProject"
              :disabled="isReprocessing"
              :class="{
                'bg-amber-500/10 text-amber-600 hover:bg-amber-500/20': btnFeedback.getFeedback('reprocess') === 'confirming',
                'bg-green-500/10 text-green-600': btnFeedback.getFeedback('reprocess') === 'success',
                'bg-destructive/10 text-destructive': btnFeedback.getFeedback('reprocess') === 'error',
                'text-muted-foreground': !['confirming', 'success', 'error'].includes(btnFeedback.getFeedback('reprocess')),
              }"
            >
              <Icon
                :name="isReprocessing ? 'lucide:loader-2' : btnFeedback.getFeedback('reprocess') === 'confirming' ? 'lucide:alert-triangle' : btnFeedback.getFeedback('reprocess') === 'success' ? 'lucide:check' : btnFeedback.getFeedback('reprocess') === 'error' ? 'lucide:x' : 'lucide:rotate-cw'"
                :class="['h-3.5 w-3.5 mr-1.5', isReprocessing ? 'animate-spin' : '']"
              />
              {{ isReprocessing ? 'Queuing...' : btnFeedback.getFeedback('reprocess') === 'confirming' ? 'Sure?' : btnFeedback.getFeedback('reprocess') === 'success' ? 'Queued' : btnFeedback.getFeedback('reprocess') === 'error' ? 'Failed' : 'Reprocess' }}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              @click="generateVideo"
              :disabled="isGeneratingVideo"
              :class="{
                'bg-green-500/10 text-green-600': btnFeedback.getFeedback('genvideo') === 'success',
                'bg-destructive/10 text-destructive': btnFeedback.getFeedback('genvideo') === 'error',
                'text-muted-foreground': !['success', 'error'].includes(btnFeedback.getFeedback('genvideo')),
              }"
            >
              <Icon
                :name="isGeneratingVideo ? 'lucide:loader-2' : btnFeedback.getFeedback('genvideo') === 'success' ? 'lucide:check' : btnFeedback.getFeedback('genvideo') === 'error' ? 'lucide:x' : 'lucide:video'"
                :class="['h-3.5 w-3.5 mr-1.5', isGeneratingVideo ? 'animate-spin' : '']"
              />
              {{ isGeneratingVideo ? 'Starting...' : btnFeedback.getFeedback('genvideo') === 'success' ? 'Started' : btnFeedback.getFeedback('genvideo') === 'error' ? 'Failed' : 'Generate Video' }}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              @click="deleteProject"
              :disabled="isDeleting"
              :class="[
                btnFeedback.getFeedback('delete') === 'confirming'
                  ? 'bg-destructive text-destructive-foreground hover:bg-destructive/90'
                  : btnFeedback.getFeedback('delete') === 'error'
                    ? 'bg-destructive/10 text-destructive'
                    : 'text-muted-foreground hover:text-destructive hover:bg-destructive/10'
              ]"
            >
              <Icon
                :name="isDeleting ? 'lucide:loader-2' : btnFeedback.getFeedback('delete') === 'confirming' ? 'lucide:alert-triangle' : btnFeedback.getFeedback('delete') === 'error' ? 'lucide:x' : 'lucide:trash-2'"
                :class="['h-3.5 w-3.5 mr-1.5', isDeleting ? 'animate-spin' : '']"
              />
              {{ isDeleting ? 'Deleting...' : btnFeedback.getFeedback('delete') === 'confirming' ? 'Sure?' : btnFeedback.getFeedback('delete') === 'error' ? 'Failed' : 'Delete' }}
            </Button>
          </div>
        </div>

        <!-- Content Sections -->
        <div class="space-y-6">

          <!-- Description -->
          <section>
            <div class="flex items-center gap-2.5 mb-3">
              <Icon name="lucide:text" class="h-5 w-5 text-muted-foreground" />
              <h2 class="text-lg font-semibold">Description</h2>
            </div>
            <Card class="p-6">
              <p class="text-muted-foreground leading-relaxed">{{ project.description }}</p>
            </Card>
          </section>

          <!-- Screenshot -->
          <section v-if="project.screenshot_path">
            <div class="flex items-center gap-2.5 mb-3">
              <Icon name="lucide:image" class="h-5 w-5 text-muted-foreground" />
              <h2 class="text-lg font-semibold">Screenshot</h2>
            </div>
            <Card class="overflow-hidden">
              <div class="border-b">
                <img
                  :src="`${config.public.apiBase}/media/${project.screenshot_path}`"
                  :alt="`Screenshot of ${project.title}`"
                  class="w-full"
                  loading="lazy"
                />
              </div>
              <div v-if="project.project_urls?.length" class="px-5 py-3">
                <a
                  :href="project.project_urls[0]"
                  target="_blank"
                  class="text-sm text-muted-foreground hover:text-primary transition-colors flex items-center gap-1.5"
                >
                  <Icon name="lucide:external-link" class="h-3.5 w-3.5" />
                  {{ project.project_urls[0] }}
                </a>
              </div>
            </Card>
          </section>

          <!-- URLs & Scraped Content -->
          <section v-if="project.project_urls?.length">
            <Collapsible>
              <div class="flex items-center gap-2.5 mb-3">
                <Icon name="lucide:link" class="h-5 w-5 text-muted-foreground" />
                <CollapsibleTrigger class="flex items-center gap-2 group">
                  <h2 class="text-lg font-semibold">URLs & Scraped Content</h2>
                  <Icon name="lucide:chevron-down" class="h-4 w-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent>
                <Card class="divide-y">
                  <div v-for="url in project.project_urls" :key="url" class="p-5">
                    <a
                      :href="url"
                      target="_blank"
                      class="text-primary hover:underline flex items-center gap-2 mb-3 font-medium text-sm"
                    >
                      <Icon name="lucide:external-link" class="h-4 w-4 flex-shrink-0" />
                      <span class="truncate">{{ url }}</span>
                    </a>
                    <!-- Full scraped content (primary display) -->
                    <div v-if="project.url_contents?.[url]" class="space-y-3">
                      <div class="text-sm text-muted-foreground bg-muted/50 p-4 rounded-lg leading-relaxed max-h-96 overflow-y-auto whitespace-pre-wrap font-mono text-xs">{{ project.url_contents[url] }}</div>
                      <!-- Summary as secondary info -->
                      <div v-if="project.url_summaries?.[url]" class="text-sm text-muted-foreground italic border-l-2 border-muted pl-3">
                        <span class="font-medium not-italic text-xs uppercase tracking-wider text-muted-foreground/70">Summary:</span>
                        {{ project.url_summaries[url] }}
                      </div>
                    </div>
                    <!-- Fallback to summary only -->
                    <div v-else-if="project.url_summaries?.[url]" class="text-sm text-muted-foreground bg-muted/50 p-4 rounded-lg leading-relaxed">
                      {{ project.url_summaries[url] }}
                    </div>
                    <div v-else class="text-sm text-muted-foreground/60 italic">
                      No content available
                    </div>
                  </div>
                </Card>
              </CollapsibleContent>
            </Collapsible>
          </section>

          <!-- Original Comment (Collapsible) -->
          <section v-if="sourceComment">
            <Collapsible>
              <div class="flex items-center gap-2.5 mb-3">
                <Icon name="lucide:message-square" class="h-5 w-5 text-muted-foreground" />
                <CollapsibleTrigger class="flex items-center gap-2 group">
                  <h2 class="text-lg font-semibold">Original Comment</h2>
                  <Icon name="lucide:chevron-down" class="h-4 w-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent>
                <Card class="p-6">
                  <div class="flex items-center gap-3 mb-5">
                    <div class="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <span class="text-sm font-semibold text-primary">
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
                        {{ formatUnixTime(sourceComment.time) }}
                      </p>
                    </div>
                  </div>
                  <div
                    class="prose prose-sm max-w-none dark:prose-invert bg-muted/50 p-5 rounded-lg"
                    v-html="sourceComment.text || '<em>No content</em>'"
                  />
                  <div class="mt-5 flex gap-4">
                    <a
                      :href="`https://news.ycombinator.com/item?id=${sourceComment.id}`"
                      target="_blank"
                      class="text-sm text-primary hover:underline flex items-center gap-1.5"
                    >
                      <Icon name="lucide:external-link" class="h-3.5 w-3.5" />
                      View on HN
                    </a>
                    <a
                      v-if="parentPost"
                      :href="`/comments?post_id=${parentPost.id}`"
                      class="text-sm text-primary hover:underline flex items-center gap-1.5"
                    >
                      <Icon name="lucide:file-text" class="h-3.5 w-3.5" />
                      View Post Comments
                    </a>
                  </div>
                </Card>
              </CollapsibleContent>
            </Collapsible>
          </section>

          <!-- Workflow Logs (Collapsible) -->
          <section v-if="project.workflow_logs?.length">
            <Collapsible>
              <div class="flex items-center gap-2.5 mb-3">
                <Icon name="lucide:terminal" class="h-5 w-5 text-muted-foreground" />
                <CollapsibleTrigger class="flex items-center gap-2 group">
                  <h2 class="text-lg font-semibold">Processing Logs</h2>
                  <Icon name="lucide:chevron-down" class="h-4 w-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent>
                <Card class="p-5">
                  <div class="bg-muted/50 rounded-lg p-4 font-mono text-xs space-y-1 max-h-80 overflow-y-auto">
                    <div v-for="(log, index) in project.workflow_logs" :key="index" class="text-muted-foreground">
                      {{ log }}
                    </div>
                  </div>
                </Card>
              </CollapsibleContent>
            </Collapsible>
          </section>

          <!-- Metadata -->
          <section>
            <div class="flex items-center gap-2.5 mb-3">
              <Icon name="lucide:info" class="h-5 w-5 text-muted-foreground" />
              <h2 class="text-lg font-semibold">Metadata</h2>
            </div>
            <Card class="p-6">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div class="flex flex-col gap-1">
                  <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Project ID</span>
                  <span class="font-mono text-sm">{{ project.id }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Source Comment</span>
                  <span class="font-mono text-sm">{{ project.source_comment_id }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Comment Date</span>
                  <span class="text-sm">{{ project.comment_time ? formatUnixTime(project.comment_time) : 'Unknown' }}</span>
                </div>
                <div class="flex flex-col gap-1">
                  <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Processed</span>
                  <span class="text-sm">{{ formatISODate(project.processed_at, true) }}</span>
                </div>
              </div>
            </Card>
          </section>

          <!-- Similar Projects -->
          <section>
            <div class="flex items-center gap-2.5 mb-3">
              <Icon name="lucide:sparkles" class="h-5 w-5 text-muted-foreground" />
              <h2 class="text-lg font-semibold">Similar Projects</h2>
            </div>
            <Card>
              <div v-if="isLoadingSimilar" class="flex items-center gap-2.5 text-muted-foreground p-6">
                <Icon name="lucide:loader-2" class="h-4 w-4 animate-spin" />
                <span class="text-sm">Finding similar projects...</span>
              </div>
              <div v-else-if="similarProjects.length === 0" class="text-sm text-muted-foreground p-6">
                No similar projects found.
              </div>
              <div v-else class="divide-y">
                <a
                  v-for="item in similarProjects"
                  :key="item.project.id"
                  :href="`/projects/${item.project.id}`"
                  class="flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors first:rounded-t-xl last:rounded-b-xl"
                >
                  <div
                    v-if="item.project.screenshot_path"
                    class="w-16 h-10 rounded-md overflow-hidden flex-shrink-0 bg-muted border"
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
                    class="w-16 h-10 rounded-md flex-shrink-0 bg-muted border flex items-center justify-center"
                  >
                    <Icon name="lucide:image-off" class="h-4 w-4 text-muted-foreground/40" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-medium text-sm truncate">{{ item.project.title }}</div>
                    <div class="text-xs text-muted-foreground truncate mt-0.5">{{ item.project.short_description }}</div>
                  </div>
                  <Badge variant="outline" class="flex-shrink-0 tabular-nums">
                    {{ Math.round(item.similarity * 100) }}%
                  </Badge>
                </a>
              </div>
            </Card>
          </section>

          <!-- Videos -->
          <section>
            <div class="flex items-center gap-2.5 mb-3">
              <Icon name="lucide:video" class="h-5 w-5 text-muted-foreground" />
              <h2 class="text-lg font-semibold">Videos</h2>
              <Badge v-if="projectVideos.length > 0" variant="secondary">{{ projectVideos.length }}</Badge>
            </div>
            <Card>
              <div v-if="isLoadingVideos" class="flex items-center gap-2.5 text-muted-foreground p-6">
                <Icon name="lucide:loader-2" class="h-4 w-4 animate-spin" />
                <span class="text-sm">Loading videos...</span>
              </div>
              <div v-else-if="projectVideos.length === 0" class="text-sm text-muted-foreground p-6">
                No videos generated yet.
              </div>
              <div v-else class="divide-y">
                <a
                  v-for="vid in projectVideos"
                  :key="vid.id"
                  :href="`/videos/${vid.id}`"
                  class="flex items-center gap-4 p-4 hover:bg-muted/50 transition-colors first:rounded-t-xl last:rounded-b-xl"
                >
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-sm truncate">
                        {{ vid.video_title || `Video #${vid.id}` }}
                      </span>
                      <Badge variant="outline" class="text-xs flex-shrink-0">v{{ vid.version }}</Badge>
                    </div>
                    <div class="text-xs text-muted-foreground mt-0.5">
                      {{ formatISODate(vid.created_at) }}
                    </div>
                  </div>
                  <div class="flex items-center gap-2 flex-shrink-0">
                    <Icon
                      name="lucide:star"
                      :class="[
                        'h-4 w-4',
                        vid.is_favorited ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground/30'
                      ]"
                    />
                    <Badge
                      :variant="vid.status === 'completed' ? 'default' : vid.status === 'failed' ? 'destructive' : 'secondary'"
                      class="text-xs"
                    >
                      {{ vid.status }}
                    </Badge>
                  </div>
                </a>
              </div>
            </Card>
          </section>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WaywoProject, WaywoComment, WaywoPost, WaywoVideo } from '~/types/models'

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

const config = useRuntimeConfig()

// Reactive state
const project = ref<WaywoProject | null>(null)
const sourceComment = ref<WaywoComment | null>(null)
const parentPost = ref<WaywoPost | null>(null)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)
const isDeleting = ref(false)
const isReprocessing = ref(false)
const isTogglingBookmark = ref(false)
const similarProjects = ref<{ project: WaywoProject; similarity: number }[]>([])
const isLoadingSimilar = ref(false)
const projectVideos = ref<WaywoVideo[]>([])
const isLoadingVideos = ref(false)
const isGeneratingVideo = ref(false)
const btnFeedback = useButtonFeedback()

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

    // Fetch similar projects and videos in parallel (non-blocking)
    fetchSimilarProjects()
    fetchProjectVideos()
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
  if (!btnFeedback.confirmOrProceed('delete')) return

  isDeleting.value = true

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-projects/${projectId.value}`, {
      method: 'DELETE'
    })
    window.location.href = '/projects'
  } catch (err) {
    console.error('Failed to delete project:', err)
    btnFeedback.showError('delete')
    isDeleting.value = false
  }
}

// Reprocess project (reprocess the source comment)
async function reprocessProject() {
  if (isReprocessing.value || !project.value) return
  if (!btnFeedback.confirmOrProceed('reprocess')) return

  isReprocessing.value = true

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-comments/${project.value.source_comment_id}/process`, {
      method: 'POST'
    })
    btnFeedback.showSuccess('reprocess')
  } catch (err) {
    console.error('Failed to reprocess project:', err)
    btnFeedback.showError('reprocess')
  } finally {
    isReprocessing.value = false
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

// Fetch videos for this project
async function fetchProjectVideos() {
  isLoadingVideos.value = true
  try {
    const response = await $fetch<{
      videos: WaywoVideo[]
      total: number
      project_id: number
    }>(`${config.public.apiBase}/api/waywo-projects/${projectId.value}/videos`)
    projectVideos.value = response.videos
  } catch (err) {
    console.error('Failed to fetch project videos:', err)
  } finally {
    isLoadingVideos.value = false
  }
}

// Generate video for this project
async function generateVideo() {
  if (isGeneratingVideo.value) return

  isGeneratingVideo.value = true

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-projects/${projectId.value}/generate-video`, {
      method: 'POST'
    })
    btnFeedback.showSuccess('genvideo')
    fetchProjectVideos()
  } catch (err) {
    console.error('Failed to generate video:', err)
    btnFeedback.showError('genvideo')
  } finally {
    isGeneratingVideo.value = false
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
