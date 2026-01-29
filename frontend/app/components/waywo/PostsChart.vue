<template>
  <Card class="p-6">
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-lg font-semibold">Comments per Post</h3>
        <p class="text-sm text-muted-foreground">
          Stored comments from each monthly post
        </p>
      </div>
      <Button variant="outline" size="sm" @click="fetchChartData" :disabled="isLoading">
        <Icon
          :name="isLoading ? 'lucide:loader-2' : 'lucide:refresh-cw'"
          :class="isLoading ? 'animate-spin' : ''"
          class="h-4 w-4"
        />
      </Button>
    </div>

    <div v-if="isLoading" class="h-[300px] flex items-center justify-center">
      <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="error" class="h-[300px] flex items-center justify-center">
      <div class="text-center">
        <Icon name="lucide:alert-circle" class="h-8 w-8 text-destructive mx-auto mb-2" />
        <p class="text-sm text-muted-foreground">{{ error }}</p>
      </div>
    </div>

    <div v-else-if="chartData.length === 0" class="h-[300px] flex items-center justify-center">
      <div class="text-center">
        <Icon name="lucide:bar-chart-2" class="h-8 w-8 text-muted-foreground mx-auto mb-2" />
        <p class="text-sm text-muted-foreground">No data available</p>
      </div>
    </div>

    <div v-else class="h-[300px]">
      <BarChart
        :data="chartData"
        index="tooltip_title"
        :categories="['comment_count']"
        :colors="['hsl(var(--primary))']"
        :x-formatter="(_v: number, i: number) => chartData[i]?.label ?? ''"
        :y-formatter="(value: number) => value.toLocaleString()"
        :show-legend="false"
        :rounded-corners="4"
        :margin="{ top: 10, right: 10, bottom: 50, left: 40 }"
        :custom-tooltip="PostsChartTooltip"
      />
    </div>

    <div v-if="chartData.length > 0" class="mt-4 pt-4 border-t">
      <div class="flex justify-between text-sm text-muted-foreground">
        <span>{{ chartData.length }} posts</span>
        <span>{{ totalComments }} comments stored</span>
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
import PostsChartTooltip from '~/components/waywo/PostsChartTooltip.vue'

interface ApiPostChartItem {
  id: number
  year: number | null
  month: number | null
  title: string | null
  comment_count: number
  total_comments: number
  label: string
  tooltip_title: string
}

interface ChartDataItem {
  label: string
  tooltip_title: string
  comment_count: number
  total_comments: number
}

const config = useRuntimeConfig()

const rawData = ref<ApiPostChartItem[]>([])
const isLoading = ref(false)
const error = ref<string | null>(null)

// Transform data to only include chart-relevant fields
const chartData = computed<ChartDataItem[]>(() => {
  return rawData.value.map(item => ({
    label: item.label,
    tooltip_title: item.tooltip_title,
    comment_count: item.comment_count,
    total_comments: item.total_comments,
  }))
})

const totalComments = computed(() => {
  return rawData.value.reduce((sum, item) => sum + item.comment_count, 0)
})

async function fetchChartData() {
  isLoading.value = true
  error.value = null

  try {
    const response = await $fetch<{ posts: ApiPostChartItem[]; total_posts: number }>(
      `${config.public.apiBase}/api/waywo-posts/chart-data`
    )
    rawData.value = response.posts
  } catch (err) {
    console.error('Failed to fetch chart data:', err)
    error.value = 'Failed to load chart data'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchChartData()
})

// Expose refresh function for parent components
defineExpose({
  refresh: fetchChartData
})
</script>
