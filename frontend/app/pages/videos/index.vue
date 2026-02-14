<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-6xl mx-auto">
      <WaywoPageHeader
        icon="lucide:video"
        title="Videos"
        description="Generated short-form videos from project submissions"
      />

      <!-- Toolbar -->
      <div class="flex items-center gap-3 flex-wrap mb-6">
        <!-- Video count -->
        <div class="inline-flex items-center gap-1.5 rounded-lg border bg-muted/50 px-3 py-1.5 text-sm font-medium tabular-nums">
          <span class="text-foreground font-semibold">{{ total }}</span>
          <span class="text-muted-foreground">videos</span>
        </div>

        <!-- Status filter tabs -->
        <div class="flex items-center gap-1.5 flex-1 min-w-0">
          <Button
            v-for="tab in statusTabs"
            :key="tab.value"
            size="sm"
            :variant="statusFilter === tab.value ? 'default' : 'outline'"
            @click="setStatusFilter(tab.value)"
          >
            {{ tab.label }}
          </Button>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1.5">
          <Button variant="outline" size="sm" @click="fetchVideos" :disabled="isLoading">
            <Icon
              :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoading ? 'animate-spin' : ''"
              class="mr-1.5 h-3.5 w-3.5"
            />
            Refresh
          </Button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex justify-center py-12">
        <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <!-- Error State -->
      <div v-else-if="fetchError" class="text-center py-12">
        <Icon name="lucide:alert-circle" class="h-12 w-12 text-destructive mx-auto mb-4" />
        <p class="text-destructive">{{ fetchError }}</p>
        <Button variant="outline" @click="fetchVideos" class="mt-4">
          Try Again
        </Button>
      </div>

      <!-- Empty State -->
      <div v-else-if="videos.length === 0" class="text-center py-12">
        <Icon name="lucide:inbox" class="h-12 w-12 text-muted-foreground mx-auto mb-4" />
        <p class="text-muted-foreground">No videos found</p>
        <p class="text-sm text-muted-foreground mt-2">
          {{ statusFilter ? 'Try a different status filter' : 'Generate a video from a project page' }}
        </p>
      </div>

      <!-- Video Grid -->
      <div v-else>
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          <div
            v-for="video in videos"
            :key="video.id"
            class="group"
          >
            <!-- Thumbnail / Video -->
            <div
              class="relative aspect-[9/16] rounded-lg bg-muted overflow-hidden mb-2 cursor-pointer"
              @click="togglePlay(video.id)"
            >
              <!-- Video element (hidden until playing) -->
              <video
                v-if="video.video_path"
                :ref="(el) => { if (el) videoRefs[video.id] = el as HTMLVideoElement }"
                :src="`${config.public.apiBase}/media/${video.video_path}`"
                :poster="video.thumbnail_path ? `${config.public.apiBase}/media/${video.thumbnail_path}` : undefined"
                class="w-full h-full object-cover"
                playsinline
                loop
                preload="none"
                @ended="playingVideoId = null"
              />
              <!-- Fallback thumbnail for videos without a file -->
              <template v-else>
                <img
                  v-if="video.thumbnail_path"
                  :src="`${config.public.apiBase}/media/${video.thumbnail_path}`"
                  :alt="video.video_title || 'Video thumbnail'"
                  class="w-full h-full object-cover"
                  loading="lazy"
                />
                <Icon v-else name="lucide:film" class="absolute inset-0 m-auto h-10 w-10 text-muted-foreground/40" />
              </template>

              <!-- Play/Pause button -->
              <div
                :class="[
                  'absolute inset-0 flex items-center justify-center transition-opacity',
                  playingVideoId === video.id ? 'opacity-0 hover:opacity-100' : 'opacity-100'
                ]"
              >
                <div class="flex items-center justify-center w-12 h-12 rounded-full bg-black/50 backdrop-blur-sm">
                  <Icon
                    :name="playingVideoId === video.id ? 'lucide:pause' : 'lucide:play'"
                    class="h-5 w-5 text-white"
                  />
                </div>
              </div>


              <!-- Status badge -->
              <Badge
                v-if="video.status !== 'completed'"
                :variant="statusVariant(video.status)"
                class="absolute top-2 left-2 text-[10px] z-10"
              >
                {{ video.status }}
              </Badge>

              <!-- Duration & favorite -->
              <div
                :class="[
                  'absolute bottom-2 left-2 right-2 flex items-center justify-between z-10 transition-opacity',
                  playingVideoId === video.id ? 'opacity-0' : 'opacity-100'
                ]"
              >
                <span class="text-[10px] text-white/90 bg-black/50 rounded px-1.5 py-0.5">
                  {{ formatDuration(video.duration_seconds) }}
                </span>
                <button
                  @click.stop="toggleFavorite(video.id)"
                  :disabled="togglingFavoriteId === video.id"
                  class="flex items-center justify-center w-7 h-7 rounded-full bg-black/40 hover:bg-black/60 transition-colors"
                >
                  <Icon
                    name="lucide:star"
                    :class="[
                      'h-3.5 w-3.5 transition-colors',
                      video.is_favorited ? 'text-yellow-500 fill-yellow-500' : 'text-white/80 hover:text-yellow-500',
                      togglingFavoriteId === video.id ? 'animate-pulse' : ''
                    ]"
                  />
                </button>
              </div>
            </div>

            <!-- Title (links to detail page) -->
            <NuxtLink :to="`/videos/${video.id}`" class="block" @click.stop>
              <h3 class="font-medium text-sm line-clamp-2 hover:text-primary transition-colors">
                {{ video.video_title || `Video #${video.id}` }}
              </h3>
            </NuxtLink>
          </div>
        </div>

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
import type { WaywoVideo } from '~/types/models'

useHead({
  title: 'Videos - waywo',
  meta: [
    { name: 'description', content: 'Browse generated short-form videos.' }
  ]
})

const config = useRuntimeConfig()

const videos = ref<WaywoVideo[]>([])
const total = ref(0)
const isLoading = ref(false)
const fetchError = ref<string | null>(null)
const statusFilter = ref<string | null>(null)
const togglingFavoriteId = ref<number | null>(null)
const playingVideoId = ref<number | null>(null)
const videoRefs: Record<number, HTMLVideoElement> = {}

const limit = ref(12)
const offset = ref(0)

const statusTabs = [
  { label: 'All', value: null },
  { label: 'Completed', value: 'completed' },
  { label: 'Generating', value: 'generating' },
  { label: 'Pending', value: 'pending' },
  { label: 'Failed', value: 'failed' },
]

function statusVariant(status: string) {
  switch (status) {
    case 'completed': return 'default' as const
    case 'failed': return 'destructive' as const
    default: return 'secondary' as const
  }
}

function setStatusFilter(value: string | null) {
  statusFilter.value = value
  offset.value = 0
  fetchVideos()
}

async function fetchVideos() {
  isLoading.value = true
  fetchError.value = null

  try {
    const params: Record<string, string | number> = {
      limit: limit.value,
      offset: offset.value,
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }

    const response = await $fetch<{
      videos: WaywoVideo[]
      total: number
      limit: number
      offset: number
    }>(`${config.public.apiBase}/api/waywo-videos`, { params })

    videos.value = response.videos
    total.value = response.total
  } catch (err) {
    console.error('Failed to fetch videos:', err)
    fetchError.value = 'Failed to fetch videos. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
}

async function toggleFavorite(videoId: number) {
  if (togglingFavoriteId.value === videoId) return

  togglingFavoriteId.value = videoId

  try {
    const response = await $fetch<{ is_favorited: boolean; video_id: number }>(
      `${config.public.apiBase}/api/waywo-videos/${videoId}/favorite`,
      { method: 'POST' }
    )
    const video = videos.value.find(v => v.id === videoId)
    if (video) {
      video.is_favorited = response.is_favorited
    }
  } catch (err) {
    console.error('Failed to toggle favorite:', err)
  } finally {
    togglingFavoriteId.value = null
  }
}

function togglePlay(videoId: number) {
  const el = videoRefs[videoId]
  if (!el) return

  if (playingVideoId.value === videoId) {
    el.pause()
    playingVideoId.value = null
  } else {
    // Pause any currently playing video
    if (playingVideoId.value !== null && videoRefs[playingVideoId.value]) {
      videoRefs[playingVideoId.value].pause()
    }
    el.play()
    playingVideoId.value = videoId
  }
}

function nextPage() {
  if (offset.value + limit.value < total.value) {
    offset.value += limit.value
    fetchVideos()
  }
}

function prevPage() {
  if (offset.value > 0) {
    offset.value = Math.max(0, offset.value - limit.value)
    fetchVideos()
  }
}

onMounted(() => {
  fetchVideos()
})
</script>
