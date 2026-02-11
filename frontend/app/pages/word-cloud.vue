<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-6xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-8">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:cloud" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Word Cloud</h1>
        <p class="text-xl text-muted-foreground">
          Visualize project hashtags — bigger means more popular
        </p>
      </div>

      <!-- Stats -->
      <div v-if="tagData" class="grid grid-cols-3 gap-4 max-w-md mx-auto mb-8">
        <div class="p-4 bg-muted rounded-lg text-center">
          <p class="text-2xl font-bold">{{ tagData.total_unique }}</p>
          <p class="text-sm text-muted-foreground">Unique Tags</p>
        </div>
        <div class="p-4 bg-muted rounded-lg text-center">
          <p class="text-2xl font-bold">{{ tagData.total_usage }}</p>
          <p class="text-sm text-muted-foreground">Total Usages</p>
        </div>
        <div class="p-4 bg-muted rounded-lg text-center">
          <p class="text-2xl font-bold">{{ words.length }}</p>
          <p class="text-sm text-muted-foreground">Shown</p>
        </div>
      </div>

      <!-- Word Cloud -->
      <Card class="p-6">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-lg font-semibold">Project Tag Cloud</h2>
            <p class="text-sm text-muted-foreground">
              Tags from {{ tagData?.total_unique ?? '...' }} unique hashtags across all projects
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" @click="fetchTags">
              <Icon name="lucide:refresh-cw" class="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Button variant="outline" size="sm" @click="settingsOpen = true">
              <Icon name="lucide:settings" class="h-4 w-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="flex items-center justify-center h-[500px]">
          <div class="text-center">
            <Icon name="lucide:loader-2" class="h-8 w-8 text-muted-foreground animate-spin mx-auto mb-2" />
            <p class="text-muted-foreground">Loading tags...</p>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else-if="words.length === 0" class="flex items-center justify-center h-[500px]">
          <div class="text-center">
            <Icon name="lucide:cloud-off" class="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p class="text-muted-foreground">No tags found</p>
          </div>
        </div>

        <!-- Cloud -->
        <ClientOnly v-else>
          <div class="word-cloud-container">
            <VueWordCloud
              style="width: 100%; height: 500px;"
              :words="words"
              :color="colorFn"
              :font-family="settings.fontFamily"
              :font-weight="settings.fontWeight"
              :spacing="settings.spacing"
              :font-size-ratio="settings.fontSizeRatio"
              :rotation="rotationFn"
              rotation-unit="deg"
              :animation-duration="800"
              animation-easing="ease-out"
              :animation-overlap="0.5"
            >
              <template #default="{ text, weight }">
                <a
                  :href="`/projects?tags=${encodeURIComponent(text)}`"
                  :title="`#${text} — ${weight} projects`"
                  class="word-cloud-tag"
                >
                  {{ text }}
                </a>
              </template>
            </VueWordCloud>
          </div>
        </ClientOnly>
      </Card>
    </div>
  </div>

  <!-- Settings Sheet -->
  <Sheet v-model:open="settingsOpen">
    <SheetContent side="right" class="w-[340px] sm:max-w-[340px] overflow-y-auto">
      <SheetHeader>
        <SheetTitle>Word Cloud Settings</SheetTitle>
        <SheetDescription>Customize the appearance of the word cloud.</SheetDescription>
      </SheetHeader>

      <div class="space-y-6 px-4 py-4">
        <!-- Color Palette -->
        <div class="space-y-2">
          <Label>Color Palette</Label>
          <Select v-model="settings.colorPalette">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="Choose palette" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="vibrant">Vibrant</SelectItem>
              <SelectItem value="cool">Cool</SelectItem>
              <SelectItem value="warm">Warm</SelectItem>
              <SelectItem value="monochrome">Monochrome</SelectItem>
              <SelectItem value="theme">Theme</SelectItem>
            </SelectContent>
          </Select>
          <!-- Palette preview swatches -->
          <div class="flex gap-1 mt-1">
            <div
              v-for="(color, i) in activePalette"
              :key="i"
              class="h-4 flex-1 rounded-sm first:rounded-l-md last:rounded-r-md"
              :style="{ backgroundColor: color }"
            />
          </div>
        </div>

        <!-- Monochrome Base Hue (only visible when monochrome is selected) -->
        <div v-if="settings.colorPalette === 'monochrome'" class="space-y-2">
          <Label>Base Hue: {{ monochromeHueLabel }}</Label>
          <Slider
            v-model="monochromeHueArr"
            :min="0"
            :max="360"
            :step="5"
          />
        </div>

        <!-- Font Family -->
        <div class="space-y-2">
          <Label>Font Family</Label>
          <Select v-model="settings.fontFamily">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="Choose font" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Inter, system-ui, sans-serif">Inter</SelectItem>
              <SelectItem value="Georgia, serif">Georgia</SelectItem>
              <SelectItem value="Menlo, monospace">Menlo (Mono)</SelectItem>
              <SelectItem value="system-ui, sans-serif">System Default</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Font Weight -->
        <div class="space-y-2">
          <Label>Font Weight</Label>
          <Select v-model="settings.fontWeight">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="Choose weight" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="normal">Normal</SelectItem>
              <SelectItem value="bold">Bold</SelectItem>
              <SelectItem value="900">Black</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Spacing -->
        <div class="space-y-2">
          <Label>Spacing: {{ Math.round(settings.spacing * 100) }}%</Label>
          <Slider
            v-model="spacingArr"
            :min="0"
            :max="1"
            :step="0.05"
          />
        </div>

        <!-- Rotation -->
        <div class="space-y-2">
          <Label>Rotation</Label>
          <Select v-model="settings.rotationPreset">
            <SelectTrigger class="w-full">
              <SelectValue placeholder="Choose rotation" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">None (all horizontal)</SelectItem>
              <SelectItem value="mixed">Mixed (slight tilt)</SelectItem>
              <SelectItem value="right-angles">Right Angles (0 / 90)</SelectItem>
              <SelectItem value="random">Full Random</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Font Size Ratio -->
        <div class="space-y-2">
          <Label>Font Size Ratio: {{ settings.fontSizeRatio.toFixed(1) }}</Label>
          <Slider
            v-model="fontSizeRatioArr"
            :min="0"
            :max="10"
            :step="0.5"
          />
          <p class="text-xs text-muted-foreground">
            Controls the size difference between the largest and smallest words.
          </p>
        </div>

        <!-- Max Words -->
        <div class="space-y-2">
          <Label>Max Words: {{ settings.maxWords }}</Label>
          <Slider
            v-model="maxWordsArr"
            :min="25"
            :max="500"
            :step="25"
          />
        </div>
      </div>

      <SheetFooter>
        <Button variant="outline" class="w-full" @click="resetSettings">
          <Icon name="lucide:rotate-ccw" class="h-4 w-4 mr-2" />
          Reset to Defaults
        </Button>
      </SheetFooter>
    </SheetContent>
  </Sheet>
</template>

<script setup lang="ts">
useHead({
  title: 'Word Cloud - waywo',
  meta: [
    { name: 'description', content: 'Visualize project hashtags as an interactive word cloud.' }
  ]
})

const config = useRuntimeConfig()

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TagCount {
  tag: string
  count: number
}

interface TagData {
  tags: TagCount[]
  total_unique: number
  total_usage: number
}

type ColorPalette = 'vibrant' | 'cool' | 'warm' | 'monochrome' | 'theme'
type RotationPreset = 'none' | 'mixed' | 'right-angles' | 'random'

interface Settings {
  colorPalette: ColorPalette
  monochromeHue: number
  fontFamily: string
  fontWeight: string
  spacing: number
  rotationPreset: RotationPreset
  fontSizeRatio: number
  maxWords: number
}

// ---------------------------------------------------------------------------
// Defaults & Settings
// ---------------------------------------------------------------------------

const DEFAULTS: Settings = {
  colorPalette: 'vibrant',
  monochromeHue: 262,
  fontFamily: 'Inter, system-ui, sans-serif',
  fontWeight: 'bold',
  spacing: 0.25,
  rotationPreset: 'mixed',
  fontSizeRatio: 3,
  maxWords: 200,
}

const STORAGE_KEY = 'waywo-word-cloud-settings'

function loadSettings(): Settings {
  if (import.meta.server) return { ...DEFAULTS }
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return { ...DEFAULTS }
}

function saveSettings(s: Settings) {
  if (import.meta.server) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
  } catch { /* ignore */ }
}

const settings = reactive<Settings>(loadSettings())
const settingsOpen = ref(false)

// Persist on any change
watch(() => ({ ...settings }), (val) => saveSettings(val), { deep: true })

function resetSettings() {
  Object.assign(settings, { ...DEFAULTS })
}

// ---------------------------------------------------------------------------
// Slider array wrappers (Slider v-model expects number[])
// ---------------------------------------------------------------------------

const spacingArr = computed({
  get: () => [settings.spacing],
  set: (v: number[]) => { settings.spacing = v[0] },
})

const fontSizeRatioArr = computed({
  get: () => [settings.fontSizeRatio],
  set: (v: number[]) => { settings.fontSizeRatio = v[0] },
})

const maxWordsArr = computed({
  get: () => [settings.maxWords],
  set: (v: number[]) => { settings.maxWords = v[0] },
})

const monochromeHueArr = computed({
  get: () => [settings.monochromeHue],
  set: (v: number[]) => { settings.monochromeHue = v[0] },
})

const monochromeHueLabel = computed(() => {
  const h = settings.monochromeHue
  if (h < 15) return `${h} (Red)`
  if (h < 45) return `${h} (Orange)`
  if (h < 70) return `${h} (Yellow)`
  if (h < 160) return `${h} (Green)`
  if (h < 200) return `${h} (Cyan)`
  if (h < 260) return `${h} (Blue)`
  if (h < 300) return `${h} (Purple)`
  if (h < 340) return `${h} (Pink)`
  return `${h} (Red)`
})

// ---------------------------------------------------------------------------
// Tag Data
// ---------------------------------------------------------------------------

const tagData = ref<TagData | null>(null)
const isLoading = ref(true)

const words = computed(() => {
  if (!tagData.value) return []
  return tagData.value.tags
    .slice(0, settings.maxWords)
    .map(t => [t.tag, t.count] as [string, number])
})

async function fetchTags() {
  isLoading.value = true
  try {
    tagData.value = await $fetch<TagData>(
      `${config.public.apiBase}/api/waywo-projects/hashtag-counts`,
      { params: { limit: 500, min_count: 1 } }
    )
  } catch (err) {
    console.error('Failed to fetch hashtag counts:', err)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchTags()
})

// ---------------------------------------------------------------------------
// Color Palettes
// ---------------------------------------------------------------------------

const palettes: Record<ColorPalette, string[]> = {
  vibrant: [
    'hsl(262, 83%, 58%)', // purple
    'hsl(221, 83%, 53%)', // blue
    'hsl(199, 89%, 48%)', // sky
    'hsl(172, 66%, 50%)', // teal
    'hsl(142, 71%, 45%)', // green
    'hsl(47, 96%, 53%)',  // yellow
    'hsl(24, 95%, 53%)',  // orange
    'hsl(346, 77%, 50%)', // rose
    'hsl(280, 65%, 60%)', // violet
    'hsl(199, 95%, 74%)', // light blue
  ],
  cool: [
    'hsl(221, 83%, 53%)', // blue
    'hsl(199, 89%, 48%)', // sky
    'hsl(172, 66%, 50%)', // teal
    'hsl(262, 83%, 58%)', // purple
    'hsl(142, 71%, 45%)', // green
    'hsl(199, 95%, 74%)', // light blue
    'hsl(280, 65%, 60%)', // violet
    'hsl(190, 80%, 42%)', // dark cyan
    'hsl(230, 70%, 65%)', // periwinkle
    'hsl(160, 60%, 55%)', // mint
  ],
  warm: [
    'hsl(346, 77%, 50%)', // rose
    'hsl(24, 95%, 53%)',  // orange
    'hsl(47, 96%, 53%)',  // yellow
    'hsl(0, 72%, 51%)',   // red
    'hsl(15, 80%, 60%)',  // salmon
    'hsl(40, 90%, 50%)',  // amber
    'hsl(340, 65%, 47%)', // crimson
    'hsl(30, 100%, 45%)', // burnt orange
    'hsl(55, 85%, 50%)',  // gold
    'hsl(10, 85%, 55%)',  // tomato
  ],
  monochrome: [], // generated dynamically
  theme: [
    'hsl(var(--primary))',
    'hsl(var(--secondary))',
    'hsl(var(--accent))',
    'hsl(var(--muted))',
    'hsl(var(--destructive))',
  ],
}

function generateMonochromePalette(hue: number): string[] {
  return [
    `hsl(${hue}, 85%, 40%)`,
    `hsl(${hue}, 75%, 45%)`,
    `hsl(${hue}, 70%, 50%)`,
    `hsl(${hue}, 65%, 55%)`,
    `hsl(${hue}, 60%, 60%)`,
    `hsl(${hue}, 55%, 65%)`,
    `hsl(${hue}, 50%, 70%)`,
    `hsl(${hue}, 45%, 75%)`,
    `hsl(${hue}, 40%, 80%)`,
    `hsl(${hue}, 35%, 85%)`,
  ]
}

const activePalette = computed(() => {
  if (settings.colorPalette === 'monochrome') {
    return generateMonochromePalette(settings.monochromeHue)
  }
  return palettes[settings.colorPalette]
})

const colorFn = (word: [string, number]) => {
  const pal = activePalette.value
  if (!pal.length) return 'currentColor'

  const weight = word[1]
  if (!tagData.value || tagData.value.tags.length === 0) return pal[0]

  const visibleTags = tagData.value.tags.slice(0, settings.maxWords)
  const maxCount = visibleTags[0].count
  const minCount = visibleTags[visibleTags.length - 1].count
  const range = maxCount - minCount || 1
  const normalized = (weight - minCount) / range

  // Higher weight = earlier in palette (bolder/darker colors)
  const index = Math.floor((1 - normalized) * (pal.length - 1))
  return pal[Math.min(index, pal.length - 1)]
}

// ---------------------------------------------------------------------------
// Rotation
// ---------------------------------------------------------------------------

const rotationFn = () => {
  switch (settings.rotationPreset) {
    case 'none':
      return 0
    case 'mixed': {
      const angles = [0, 0, 0, -15, 15]
      return angles[Math.floor(Math.random() * angles.length)]
    }
    case 'right-angles': {
      return Math.random() < 0.5 ? 0 : 90
    }
    case 'random':
      return Math.floor(Math.random() * 181) - 90
    default:
      return 0
  }
}
</script>

<style scoped>
.word-cloud-container {
  min-height: 500px;
  border-radius: 0.5rem;
}

.word-cloud-tag {
  cursor: pointer;
  text-decoration: none;
  color: inherit;
  transition: opacity 0.15s ease;
}

.word-cloud-tag:hover {
  opacity: 0.7;
}
</style>
