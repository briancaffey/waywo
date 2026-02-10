<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-5xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:video" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Videos</h1>
        <p class="text-xl text-muted-foreground">
          Generated short-form videos from project submissions
        </p>
      </div>

      <!-- Stats Card -->
      <Card class="p-6 mb-8">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-sm text-muted-foreground">Total Videos</p>
            <p class="text-3xl font-bold">{{ total }}</p>
          </div>
          <Button variant="outline" @click="fetchVideos" :disabled="isLoading">
            <Icon
              :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
              :class="isLoading ? 'animate-spin' : ''"
              class="mr-2 h-4 w-4"
            />
            Refresh
          </Button>
        </div>
      </Card>

      <!-- Status Filter Tabs -->
      <div class="flex gap-2 mb-6 flex-wrap">
        <Button
          v-for="tab in statusTabs"
          :key="tab.value"
          :variant="statusFilter === tab.value ? 'default' : 'outline'"
          @click="setStatusFilter(tab.value)"
        >
          {{ tab.label }}
        </Button>
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
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card
            v-for="video in videos"
            :key="video.id"
            class="cursor-pointer hover:border-primary/50 transition-colors overflow-hidden"
            @click="viewVideo(video.id)"
          >
            <!-- Thumbnail -->
            <div class="aspect-video bg-muted flex items-center justify-center overflow-hidden">
              <img
                v-if="video.thumbnail_path"
                :src="`${config.public.apiBase}/media/${video.thumbnail_path}`"
                :alt="video.video_title || 'Video thumbnail'"
                class="w-full h-full object-cover"
                loading="lazy"
              />
              <Icon v-else name="lucide:film" class="h-12 w-12 text-muted-foreground/40" />
            </div>

            <!-- Card Content -->
            <div class="p-4">
              <div class="flex items-start justify-between gap-2 mb-2">
                <h3 class="font-semibold text-sm line-clamp-2">
                  {{ video.video_title || `Video #${video.id}` }}
                </h3>
                <button
                  @click.stop="toggleFavorite(video.id)"
                  :disabled="togglingFavoriteId === video.id"
                  class="hover:scale-110 transition-transform flex-shrink-0"
                >
                  <Icon
                    name="lucide:star"
                    :class="[
                      'h-4 w-4 transition-colors',
                      video.is_favorited ? 'text-yellow-500 fill-yellow-500' : 'text-muted-foreground hover:text-yellow-500',
                      togglingFavoriteId === video.id ? 'animate-pulse' : ''
                    ]"
                  />
                </button>
              </div>

              <div class="flex items-center gap-2 flex-wrap">
                <Badge :variant="statusVariant(video.status)" class="text-xs">
                  {{ video.status }}
                </Badge>
                <span class="text-xs text-muted-foreground flex items-center gap-1">
                  <Icon name="lucide:clock" class="h-3 w-3" />
                  {{ formatDuration(video.duration_seconds) }}
                </span>
                <span class="text-xs text-muted-foreground flex items-center gap-1">
                  <Icon name="lucide:eye" class="h-3 w-3" />
                  {{ video.view_count }}
                </span>
              </div>
            </div>
          </Card>
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

function viewVideo(videoId: number) {
  window.location.href = `/videos/${videoId}`
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
