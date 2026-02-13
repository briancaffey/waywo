<template>
  <div>
    <div v-if="isLoading" class="h-[500px] flex items-center justify-center">
      <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="error" class="h-[500px] flex items-center justify-center">
      <div class="text-center">
        <Icon name="lucide:alert-circle" class="h-8 w-8 text-destructive mx-auto mb-2" />
        <p class="text-sm text-muted-foreground">{{ error }}</p>
      </div>
    </div>

    <div v-else-if="projects.length === 0" class="h-[500px] flex items-center justify-center">
      <div class="text-center max-w-sm">
        <Icon name="lucide:scatter-chart" class="h-12 w-12 text-muted-foreground mx-auto mb-3" />
        <h3 class="text-lg font-medium mb-2">No cluster data yet</h3>
        <p class="text-sm text-muted-foreground">
          Run "Compute Clusters" from the
          <a href="/admin" class="text-primary hover:underline">admin page</a>
          to generate the UMAP visualization.
        </p>
      </div>
    </div>

    <div v-else class="relative">
      <div
        ref="chartContainer"
        class="h-[600px] w-full"
        @wheel.prevent="onWheel"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
        :style="{ cursor: isPanning ? 'grabbing' : 'grab' }"
      >
        <VisXYContainer
          :data="projects"
          :margin="{ top: 20, right: 20, bottom: 20, left: 20 }"
          :xDomain="currentXDomain"
          :yDomain="currentYDomain"
          :height="containerHeight"
        >
          <VisScatter
            :x="(d: NormalizedProject) => d.nx"
            :y="(d: NormalizedProject) => d.ny"
            :color="(d: NormalizedProject) => clusterColor(d.cluster_label)"
            :size="6"
            :cursor="'pointer'"
            :events="{
              [VisScatterSelectors.point]: {
                click: onPointClick,
                mouseover: onPointMouseOver,
                mouseout: onPointMouseOut,
              }
            }"
          />
          <VisTooltip :triggers="{ [VisScatterSelectors.point]: tooltipContent }" />
        </VisXYContainer>
      </div>

      <!-- Zoom controls -->
      <div class="absolute top-2 left-2 flex flex-col gap-1">
        <Button variant="outline" size="icon" class="h-8 w-8" @click="zoomIn" title="Zoom in">
          <Icon name="lucide:plus" class="h-4 w-4" />
        </Button>
        <Button variant="outline" size="icon" class="h-8 w-8" @click="zoomOut" title="Zoom out">
          <Icon name="lucide:minus" class="h-4 w-4" />
        </Button>
        <Button
          v-if="isZoomed"
          variant="outline"
          size="icon"
          class="h-8 w-8"
          @click="resetZoom"
          title="Reset zoom"
        >
          <Icon name="lucide:maximize-2" class="h-4 w-4" />
        </Button>
      </div>

      <!-- Legend -->
      <div class="mt-4 flex flex-wrap gap-2">
        <div
          v-for="cluster in clusterLegend"
          :key="cluster.label"
          class="flex items-center gap-1.5 text-xs text-muted-foreground"
        >
          <span
            class="inline-block w-3 h-3 rounded-full"
            :style="{ backgroundColor: cluster.color }"
          />
          <span>{{ cluster.name }} ({{ cluster.count }})</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { VisXYContainer, VisScatter, VisScatterSelectors, VisTooltip } from '@unovis/vue'
import type { ClusterMapProject } from '~/types/models'

const config = useRuntimeConfig()
const router = useRouter()

const rawProjects = ref<ClusterMapProject[]>([])
const clusterNames = ref<Record<string, string>>({})
const isLoading = ref(false)
const error = ref<string | null>(null)
const chartContainer = ref<HTMLElement | null>(null)
const containerHeight = ref(600)

// Normalize x/y independently to [0, 100] so data fills the chart regardless of container shape
interface NormalizedProject extends ClusterMapProject {
  nx: number
  ny: number
}

const projects = computed<NormalizedProject[]>(() => {
  const raw = rawProjects.value
  if (raw.length === 0) return []

  const xs = raw.map(p => p.umap_x)
  const ys = raw.map(p => p.umap_y)
  const xMin = Math.min(...xs)
  const xMax = Math.max(...xs)
  const yMin = Math.min(...ys)
  const yMax = Math.max(...ys)
  const xRange = xMax - xMin || 1
  const yRange = yMax - yMin || 1

  return raw.map(p => ({
    ...p,
    nx: ((p.umap_x - xMin) / xRange) * 100,
    ny: ((p.umap_y - yMin) / yRange) * 100,
  }))
})

// --- Zoom & pan state ---
const DEFAULT_DOMAIN: [number, number] = [-5, 105]
const xDomain = ref<[number, number]>([...DEFAULT_DOMAIN])
const yDomain = ref<[number, number]>([...DEFAULT_DOMAIN])
const isPanning = ref(false)
const panStart = ref<{ x: number; y: number; xd: [number, number]; yd: [number, number] } | null>(null)

const currentXDomain = computed<[number, number]>(() => xDomain.value)
const currentYDomain = computed<[number, number]>(() => yDomain.value)

const isZoomed = computed(() => {
  return xDomain.value[0] !== DEFAULT_DOMAIN[0] ||
    xDomain.value[1] !== DEFAULT_DOMAIN[1] ||
    yDomain.value[0] !== DEFAULT_DOMAIN[0] ||
    yDomain.value[1] !== DEFAULT_DOMAIN[1]
})

function zoomAt(factor: number, centerX: number, centerY: number) {
  const [x0, x1] = xDomain.value
  const [y0, y1] = yDomain.value
  const xSpan = x1 - x0
  const ySpan = y1 - y0

  const newXSpan = xSpan * factor
  const newYSpan = ySpan * factor

  // Clamp so we don't zoom out past the default
  if (newXSpan > DEFAULT_DOMAIN[1] - DEFAULT_DOMAIN[0]) {
    resetZoom()
    return
  }
  // Don't zoom in too far
  if (newXSpan < 5) return

  xDomain.value = [
    centerX - newXSpan * ((centerX - x0) / xSpan),
    centerX + newXSpan * ((x1 - centerX) / xSpan),
  ]
  yDomain.value = [
    centerY - newYSpan * ((centerY - y0) / ySpan),
    centerY + newYSpan * ((y1 - centerY) / ySpan),
  ]
}

function onWheel(e: WheelEvent) {
  const rect = chartContainer.value?.getBoundingClientRect()
  if (!rect) return

  // Convert mouse position to domain coordinates
  const margin = 20
  const plotWidth = rect.width - margin * 2
  const plotHeight = rect.height - margin * 2
  const relX = (e.clientX - rect.left - margin) / plotWidth
  const relY = 1 - (e.clientY - rect.top - margin) / plotHeight // Y is flipped

  const [x0, x1] = xDomain.value
  const [y0, y1] = yDomain.value
  const centerX = x0 + relX * (x1 - x0)
  const centerY = y0 + relY * (y1 - y0)

  const factor = e.deltaY > 0 ? 1.15 : 0.85
  zoomAt(factor, centerX, centerY)
}

function zoomIn() {
  const [x0, x1] = xDomain.value
  const [y0, y1] = yDomain.value
  zoomAt(0.7, (x0 + x1) / 2, (y0 + y1) / 2)
}

function zoomOut() {
  const [x0, x1] = xDomain.value
  const [y0, y1] = yDomain.value
  zoomAt(1.4, (x0 + x1) / 2, (y0 + y1) / 2)
}

function resetZoom() {
  xDomain.value = [...DEFAULT_DOMAIN]
  yDomain.value = [...DEFAULT_DOMAIN]
}

function onMouseDown(e: MouseEvent) {
  // Don't start pan if clicking on a point (let click handler work)
  if ((e.target as HTMLElement)?.closest('circle')) return
  isPanning.value = true
  panStart.value = {
    x: e.clientX,
    y: e.clientY,
    xd: [...xDomain.value],
    yd: [...yDomain.value],
  }
}

function onMouseMove(e: MouseEvent) {
  if (!isPanning.value || !panStart.value || !chartContainer.value) return

  const rect = chartContainer.value.getBoundingClientRect()
  const margin = 20
  const plotWidth = rect.width - margin * 2
  const plotHeight = rect.height - margin * 2

  const dx = e.clientX - panStart.value.x
  const dy = e.clientY - panStart.value.y

  const xSpan = panStart.value.xd[1] - panStart.value.xd[0]
  const ySpan = panStart.value.yd[1] - panStart.value.yd[0]

  const domainDx = -(dx / plotWidth) * xSpan
  const domainDy = (dy / plotHeight) * ySpan // Y is flipped

  xDomain.value = [panStart.value.xd[0] + domainDx, panStart.value.xd[1] + domainDx]
  yDomain.value = [panStart.value.yd[0] + domainDy, panStart.value.yd[1] + domainDy]
}

function onMouseUp() {
  isPanning.value = false
  panStart.value = null
}

// Color palette for clusters (tab20-like)
const CLUSTER_COLORS = [
  '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
  '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
  '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5',
]
const NOISE_COLOR = '#d1d5db' // gray-300

function clusterColor(label: number | null): string {
  if (label === null || label === -1) return NOISE_COLOR
  return CLUSTER_COLORS[label % CLUSTER_COLORS.length]
}

const clusterLegend = computed(() => {
  const counts = new Map<number, number>()
  for (const p of projects.value) {
    const label = p.cluster_label ?? -1
    counts.set(label, (counts.get(label) || 0) + 1)
  }

  const names = clusterNames.value
  const entries: { label: number; name: string; color: string; count: number }[] = []
  for (const [label, count] of Array.from(counts.entries()).sort((a, b) => a[0] - b[0])) {
    entries.push({
      label,
      name: label === -1 ? 'Noise' : (names[String(label)] || `Cluster ${label}`),
      color: clusterColor(label),
      count,
    })
  }
  return entries
})

function tooltipContent(d: NormalizedProject): string {
  const tags = d.hashtags.slice(0, 4).map(t => `#${t}`).join(' ')
  const names = clusterNames.value
  const clusterName = d.cluster_label != null && d.cluster_label !== -1
    ? names[String(d.cluster_label)] || `Cluster ${d.cluster_label}`
    : 'Noise'
  return `
    <div style="max-width: 280px; padding: 4px 0;">
      <div style="font-weight: 600; margin-bottom: 4px;">${escapeHtml(d.title)}</div>
      <div style="font-size: 12px; color: #888; margin-bottom: 4px;">${escapeHtml(d.short_description)}</div>
      <div style="font-size: 11px; color: #aaa; margin-bottom: 2px;">${escapeHtml(tags)}</div>
      <div style="font-size: 11px; color: #666;">${escapeHtml(clusterName)}</div>
    </div>
  `
}

function escapeHtml(str: string): string {
  const el = document.createElement('span')
  el.textContent = str
  return el.innerHTML
}

function onPointClick(d: NormalizedProject) {
  router.push(`/projects/${d.id}`)
}

function onPointMouseOver() {
  document.body.style.cursor = 'pointer'
}

function onPointMouseOut() {
  document.body.style.cursor = isPanning.value ? 'grabbing' : 'grab'
}

async function fetchClusterData() {
  isLoading.value = true
  error.value = null

  try {
    const response = await $fetch<{
      projects: ClusterMapProject[]
      total: number
      cluster_names: Record<string, string>
    }>(
      `${config.public.apiBase}/api/waywo-projects/cluster-map`
    )
    rawProjects.value = response.projects
    clusterNames.value = response.cluster_names || {}
  } catch (err) {
    console.error('Failed to fetch cluster map data:', err)
    error.value = 'Failed to load cluster map data'
  } finally {
    isLoading.value = false
  }
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  fetchClusterData()

  if (chartContainer.value) {
    containerHeight.value = chartContainer.value.clientHeight
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        containerHeight.value = entry.contentRect.height
      }
    })
    resizeObserver.observe(chartContainer.value)
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})

defineExpose({
  refresh: fetchClusterData,
  total: computed(() => projects.value.length),
  clusterCount: computed(() => {
    const labels = new Set(projects.value.map(p => p.cluster_label).filter(l => l !== null && l !== -1))
    return labels.size
  }),
})
</script>
