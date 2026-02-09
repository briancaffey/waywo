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
        <a href="/videos">
          <Button variant="outline" class="mt-6">
            <Icon name="lucide:arrow-left" class="mr-2 h-4 w-4" />
            Back to Videos
          </Button>
        </a>
      </div>

      <!-- Video Details -->
      <div v-else-if="video">
        <!-- Breadcrumb -->
        <a href="/videos" class="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8">
          <Icon name="lucide:arrow-left" class="h-4 w-4" />
          All Videos
        </a>

        <!-- Hero Header -->
        <div class="mb-10">
          <!-- Error Alert -->
          <Alert v-if="video.status === 'failed' && video.error_message" variant="destructive" class="mb-6">
            <Icon name="lucide:alert-circle" class="h-4 w-4" />
            <AlertTitle>Generation Failed</AlertTitle>
            <AlertDescription>{{ video.error_message }}</AlertDescription>
          </Alert>

          <!-- Title Row -->
          <div class="flex items-start gap-4 mb-3">
            <button
              @click="toggleFavorite"
              :disabled="isTogglingFavorite"
              class="mt-1 hover:scale-110 transition-transform flex-shrink-0"
              :title="video.is_favorited ? 'Remove favorite' : 'Add favorite'"
            >
              <Icon
                name="lucide:star"
                :class="[
                  'h-8 w-8 transition-colors',
                  video.is_favorited ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground/40 hover:text-yellow-500',
                  isTogglingFavorite ? 'animate-pulse' : ''
                ]"
              />
            </button>
            <div class="min-w-0">
              <div class="flex items-center gap-3 flex-wrap">
                <h1 class="text-5xl md:text-6xl font-bold tracking-tight">
                  {{ video.video_title || `Video #${video.id}` }}
                </h1>
                <Badge :variant="statusVariant(video.status)">
                  {{ video.status }}
                </Badge>
              </div>
              <!-- Project Link -->
              <a
                v-if="project"
                :href="`/projects/${project.id}`"
                class="inline-flex items-center gap-1.5 text-sm text-primary hover:underline mt-2"
              >
                <Icon name="lucide:folder" class="h-3.5 w-3.5" />
                {{ project.title }}
              </a>
            </div>
          </div>

          <!-- Metadata Cards -->
          <div class="grid grid-cols-3 gap-4 mt-8 mb-6">
            <div class="relative overflow-hidden rounded-xl border bg-gradient-to-br from-blue-500/5 to-indigo-500/10 dark:from-blue-500/10 dark:to-indigo-500/5 p-5">
              <div class="flex items-center gap-3">
                <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-blue-500/10 dark:bg-blue-500/20">
                  <Icon name="lucide:clock" class="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <div class="text-sm font-medium text-muted-foreground">Duration</div>
                  <div class="text-2xl font-bold tracking-tight">{{ formatDuration(video.duration_seconds) }}</div>
                </div>
              </div>
            </div>
            <div class="relative overflow-hidden rounded-xl border bg-gradient-to-br from-green-500/5 to-emerald-500/10 dark:from-green-500/10 dark:to-emerald-500/5 p-5">
              <div class="flex items-center gap-3">
                <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-green-500/10 dark:bg-green-500/20">
                  <Icon name="lucide:eye" class="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <div class="text-sm font-medium text-muted-foreground">Views</div>
                  <div class="text-2xl font-bold tracking-tight">{{ video.view_count }}</div>
                </div>
              </div>
            </div>
            <div class="relative overflow-hidden rounded-xl border bg-gradient-to-br from-purple-500/5 to-violet-500/10 dark:from-purple-500/10 dark:to-violet-500/5 p-5">
              <div class="flex items-center gap-3">
                <div class="flex h-11 w-11 items-center justify-center rounded-lg bg-purple-500/10 dark:bg-purple-500/20">
                  <Icon name="lucide:layers" class="h-5 w-5 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <div class="text-sm font-medium text-muted-foreground">Version</div>
                  <div class="text-2xl font-bold tracking-tight">v{{ video.version }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Video Player -->
          <div v-if="video.status === 'completed' && video.video_path" class="mb-6">
            <Card class="overflow-hidden">
              <div class="flex justify-center bg-black">
                <video
                  controls
                  preload="metadata"
                  class="max-h-[500px] w-auto"
                  :poster="video.thumbnail_path ? `${config.public.apiBase}/media/${video.thumbnail_path}` : undefined"
                >
                  <source :src="`${config.public.apiBase}/media/${video.video_path}`" type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
              </div>
            </Card>
          </div>

          <!-- Action Buttons -->
          <div class="flex items-center gap-2">
            <a
              v-if="video.status === 'completed' && video.video_path"
              :href="`${config.public.apiBase}/media/${video.video_path}`"
              target="_blank"
            >
              <Button variant="outline" size="sm">
                <Icon name="lucide:external-link" class="mr-2 h-3.5 w-3.5" />
                Open in New Tab
              </Button>
            </a>
            <Button
              variant="ghost"
              size="sm"
              @click="deleteVideo"
              :disabled="isDeleting"
              class="text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            >
              <Icon
                :name="isDeleting ? 'lucide:loader-2' : 'lucide:trash-2'"
                :class="['h-3.5 w-3.5 mr-1.5', isDeleting ? 'animate-spin' : '']"
              />
              {{ isDeleting ? 'Deleting...' : 'Delete' }}
            </Button>
          </div>
        </div>

        <!-- Content Sections -->
        <div class="space-y-6">

          <!-- Segments -->
          <section v-if="video.segments?.length">
            <div class="flex items-center gap-2.5 mb-3">
              <Icon name="lucide:layout-list" class="h-5 w-5 text-muted-foreground" />
              <h2 class="text-lg font-semibold">Segments</h2>
              <Badge variant="secondary">{{ video.segments.length }}</Badge>
            </div>

            <div class="space-y-4">
              <Card v-for="segment in video.segments" :key="segment.id" class="overflow-hidden">
                <!-- Segment Header -->
                <div class="flex items-center gap-2 px-5 py-3 border-b bg-muted/30">
                  <Badge variant="outline" class="text-xs">{{ segment.segment_type }}</Badge>
                  <span class="text-sm text-muted-foreground">#{{ segment.segment_index }}</span>
                  <Badge :variant="statusVariant(segment.status)" class="text-xs ml-auto">
                    {{ segment.status }}
                  </Badge>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-0 md:divide-x">
                  <!-- Image Preview -->
                  <div class="flex items-center justify-center bg-muted/20 p-4 min-h-[160px]">
                    <img
                      v-if="segment.image_path"
                      :src="`${config.public.apiBase}/media/${segment.image_path}`"
                      :alt="`Segment ${segment.segment_index} image`"
                      class="max-h-48 rounded-md object-contain"
                      loading="lazy"
                    />
                    <Icon v-else name="lucide:image" class="h-12 w-12 text-muted-foreground/30" />
                  </div>

                  <!-- Content -->
                  <div class="md:col-span-2 p-5 space-y-4">
                    <!-- Scene Description (read-only) -->
                    <div>
                      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Scene Description</label>
                      <p class="text-sm text-muted-foreground mt-1 leading-relaxed">{{ segment.scene_description }}</p>
                    </div>

                    <!-- Narration Text (editable) -->
                    <div>
                      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Narration Text</label>
                      <Textarea
                        v-model="segmentEdits[segment.id].narration_text"
                        class="mt-1 text-sm"
                        rows="3"
                      />
                      <div class="flex items-center gap-2 mt-2">
                        <Button
                          size="sm"
                          @click="saveNarration(segment.id)"
                          :disabled="!hasNarrationChanged(segment.id) || savingNarration === segment.id"
                        >
                          <Icon
                            :name="savingNarration === segment.id ? 'lucide:loader-2' : 'lucide:save'"
                            :class="['h-3 w-3 mr-1', savingNarration === segment.id ? 'animate-spin' : '']"
                          />
                          Save
                        </Button>
                        <span v-if="hasNarrationChanged(segment.id)" class="text-xs text-amber-600 dark:text-amber-400">
                          Unsaved changes
                        </span>
                      </div>
                    </div>

                    <!-- Image Prompt (editable) -->
                    <div>
                      <label class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Image Prompt</label>
                      <Textarea
                        v-model="segmentEdits[segment.id].image_prompt"
                        class="mt-1 text-sm"
                        rows="3"
                      />
                      <div class="flex items-center gap-2 mt-2">
                        <Button
                          size="sm"
                          @click="saveImagePrompt(segment.id)"
                          :disabled="!hasImagePromptChanged(segment.id) || savingImagePrompt === segment.id"
                        >
                          <Icon
                            :name="savingImagePrompt === segment.id ? 'lucide:loader-2' : 'lucide:save'"
                            :class="['h-3 w-3 mr-1', savingImagePrompt === segment.id ? 'animate-spin' : '']"
                          />
                          Save
                        </Button>
                        <span v-if="hasImagePromptChanged(segment.id)" class="text-xs text-amber-600 dark:text-amber-400">
                          Unsaved changes
                        </span>
                      </div>
                    </div>

                    <!-- Audio Info -->
                    <div v-if="segment.audio_duration_seconds" class="flex items-center gap-2 text-sm text-muted-foreground">
                      <Icon name="lucide:audio-lines" class="h-4 w-4" />
                      Audio: {{ formatDuration(segment.audio_duration_seconds) }}
                    </div>

                    <!-- Transcription Viewer -->
                    <div v-if="segment.transcription">
                      <Collapsible>
                        <CollapsibleTrigger class="flex items-center gap-2 group text-xs font-medium text-muted-foreground uppercase tracking-wider">
                          Transcription
                          <Icon name="lucide:chevron-down" class="h-3 w-3 transition-transform group-data-[state=open]:rotate-180" />
                        </CollapsibleTrigger>
                        <CollapsibleContent>
                          <div class="mt-2 p-3 bg-muted/50 rounded-lg">
                            <!-- Full text -->
                            <p v-if="segment.transcription.text" class="text-sm text-muted-foreground mb-3">
                              {{ segment.transcription.text }}
                            </p>
                            <!-- Word pills -->
                            <div v-if="segment.transcription.words" class="flex flex-wrap gap-1">
                              <TooltipProvider>
                                <Tooltip v-for="(word, wi) in segment.transcription.words" :key="wi">
                                  <TooltipTrigger as-child>
                                    <span class="inline-block px-1.5 py-0.5 text-xs rounded bg-background border cursor-default">
                                      {{ word.word }}
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p class="text-xs">{{ word.start?.toFixed(2) }}s - {{ word.end?.toFixed(2) }}s</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          </div>
                        </CollapsibleContent>
                      </Collapsible>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </section>

          <!-- Workflow Logs -->
          <section v-if="video.workflow_logs?.length">
            <Collapsible>
              <div class="flex items-center gap-2.5 mb-3">
                <Icon name="lucide:terminal" class="h-5 w-5 text-muted-foreground" />
                <CollapsibleTrigger class="flex items-center gap-2 group">
                  <h2 class="text-lg font-semibold">Workflow Logs</h2>
                  <Icon name="lucide:chevron-down" class="h-4 w-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
                </CollapsibleTrigger>
              </div>
              <CollapsibleContent>
                <Card class="p-5">
                  <div class="bg-muted/50 rounded-lg p-4 font-mono text-xs space-y-1 max-h-80 overflow-y-auto">
                    <div v-for="(log, index) in video.workflow_logs" :key="index" class="text-muted-foreground">
                      {{ log }}
                    </div>
                  </div>
                </Card>
              </CollapsibleContent>
            </Collapsible>
          </section>

        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WaywoVideo, WaywoVideoSegment, WaywoProject } from '~/types/models'

const route = useRoute()
const videoId = computed(() => Number(route.params.id))

useHead({
  title: computed(() => video.value ? `${video.value.video_title || 'Video'} - waywo` : 'Video - waywo'),
  meta: [
    { name: 'description', content: 'View and edit video details.' }
  ]
})

const config = useRuntimeConfig()

const video = ref<WaywoVideo | null>(null)
const project = ref<WaywoProject | null>(null)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)
const isDeleting = ref(false)
const isTogglingFavorite = ref(false)
const savingNarration = ref<number | null>(null)
const savingImagePrompt = ref<number | null>(null)

// Track edits per segment: keyed by segment ID
const segmentEdits = reactive<Record<number, { narration_text: string; image_prompt: string }>>({})
// Store originals for change detection
const segmentOriginals = reactive<Record<number, { narration_text: string; image_prompt: string }>>({})

function initSegmentEdits(segments: WaywoVideoSegment[]) {
  for (const seg of segments) {
    segmentEdits[seg.id] = {
      narration_text: seg.narration_text,
      image_prompt: seg.image_prompt,
    }
    segmentOriginals[seg.id] = {
      narration_text: seg.narration_text,
      image_prompt: seg.image_prompt,
    }
  }
}

function hasNarrationChanged(segmentId: number): boolean {
  return segmentEdits[segmentId]?.narration_text !== segmentOriginals[segmentId]?.narration_text
}

function hasImagePromptChanged(segmentId: number): boolean {
  return segmentEdits[segmentId]?.image_prompt !== segmentOriginals[segmentId]?.image_prompt
}

function statusVariant(status: string) {
  switch (status) {
    case 'completed':
    case 'complete': return 'default' as const
    case 'failed': return 'destructive' as const
    default: return 'secondary' as const
  }
}

async function fetchVideo() {
  isLoading.value = true
  fetchError.value = null

  try {
    const response = await $fetch<{
      video: WaywoVideo
      project: WaywoProject | null
    }>(`${config.public.apiBase}/api/waywo-videos/${videoId.value}`)

    video.value = response.video
    project.value = response.project

    if (response.video.segments) {
      initSegmentEdits(response.video.segments)
    }
  } catch (err) {
    console.error('Failed to fetch video:', err)
    fetchError.value = 'Failed to fetch video. It may not exist.'
  } finally {
    isLoading.value = false
  }
}

async function toggleFavorite() {
  if (isTogglingFavorite.value || !video.value) return

  isTogglingFavorite.value = true

  try {
    const response = await $fetch<{ is_favorited: boolean; video_id: number }>(
      `${config.public.apiBase}/api/waywo-videos/${videoId.value}/favorite`,
      { method: 'POST' }
    )
    video.value.is_favorited = response.is_favorited
  } catch (err) {
    console.error('Failed to toggle favorite:', err)
  } finally {
    isTogglingFavorite.value = false
  }
}

async function deleteVideo() {
  if (isDeleting.value) return

  if (!confirm('Are you sure you want to delete this video?')) return

  isDeleting.value = true

  try {
    await $fetch(`${config.public.apiBase}/api/waywo-videos/${videoId.value}`, {
      method: 'DELETE'
    })
    window.location.href = '/videos'
  } catch (err) {
    console.error('Failed to delete video:', err)
    alert('Failed to delete video. Please try again.')
    isDeleting.value = false
  }
}

async function saveNarration(segmentId: number) {
  if (savingNarration.value === segmentId) return

  savingNarration.value = segmentId

  try {
    const response = await $fetch<{ segment: WaywoVideoSegment; message: string }>(
      `${config.public.apiBase}/api/waywo-videos/segments/${segmentId}/narration`,
      {
        method: 'PATCH',
        body: { narration_text: segmentEdits[segmentId].narration_text },
      }
    )

    // Update originals to reflect saved state
    segmentOriginals[segmentId].narration_text = response.segment.narration_text
    segmentEdits[segmentId].narration_text = response.segment.narration_text

    // Update segment in video data
    if (video.value?.segments) {
      const seg = video.value.segments.find(s => s.id === segmentId)
      if (seg) {
        Object.assign(seg, response.segment)
      }
    }
  } catch (err) {
    console.error('Failed to save narration:', err)
    alert('Failed to save narration. Please try again.')
  } finally {
    savingNarration.value = null
  }
}

async function saveImagePrompt(segmentId: number) {
  if (savingImagePrompt.value === segmentId) return

  savingImagePrompt.value = segmentId

  try {
    const response = await $fetch<{ segment: WaywoVideoSegment; message: string }>(
      `${config.public.apiBase}/api/waywo-videos/segments/${segmentId}/image-prompt`,
      {
        method: 'PATCH',
        body: { image_prompt: segmentEdits[segmentId].image_prompt },
      }
    )

    // Update originals to reflect saved state
    segmentOriginals[segmentId].image_prompt = response.segment.image_prompt
    segmentEdits[segmentId].image_prompt = response.segment.image_prompt

    // Update segment in video data
    if (video.value?.segments) {
      const seg = video.value.segments.find(s => s.id === segmentId)
      if (seg) {
        Object.assign(seg, response.segment)
      }
    }
  } catch (err) {
    console.error('Failed to save image prompt:', err)
    alert('Failed to save image prompt. Please try again.')
  } finally {
    savingImagePrompt.value = null
  }
}

async function recordView() {
  try {
    await $fetch(`${config.public.apiBase}/api/waywo-videos/${videoId.value}/view`, {
      method: 'POST'
    })
  } catch {
    // Fire-and-forget
  }
}

onMounted(() => {
  fetchVideo()
  recordView()
})
</script>
