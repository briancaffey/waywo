<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-3xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:sparkles" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Designer</h1>
        <p class="text-xl text-muted-foreground">
          Generate AI-powered project ideas from existing trends
        </p>
      </div>

      <!-- Configuration Card -->
      <Card class="p-6 mb-6">
        <div class="space-y-6">
          <!-- Seed Tags -->
          <div class="space-y-2">
            <Label>Seed Tags</Label>
            <p class="text-sm text-muted-foreground">Optionally select tags to guide idea generation</p>
            <Combobox v-model="selectedTags" multiple>
              <ComboboxAnchor class="w-full">
                <div class="relative">
                  <div class="flex flex-wrap gap-1 min-h-[38px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                    <Badge
                      v-for="tag in selectedTags"
                      :key="tag"
                      variant="secondary"
                      class="text-xs"
                    >
                      #{{ tag }}
                      <button
                        @click.stop="removeTag(tag)"
                        class="ml-1 hover:text-destructive"
                      >
                        <Icon name="lucide:x" class="h-3 w-3" />
                      </button>
                    </Badge>
                    <ComboboxInput
                      v-model="tagSearchQuery"
                      placeholder="Search tags..."
                      class="flex-1 min-w-[100px] bg-transparent outline-none placeholder:text-muted-foreground"
                      @keydown.enter.prevent
                    />
                  </div>
                </div>
              </ComboboxAnchor>
              <ComboboxList class="w-[var(--reka-combobox-trigger-width)] max-h-[200px] overflow-y-auto rounded-md border bg-popover p-1 shadow-md">
                <ComboboxEmpty class="py-6 text-center text-sm text-muted-foreground">
                  No tags found
                </ComboboxEmpty>
                <ComboboxItem
                  v-for="tag in filteredTags"
                  :key="tag"
                  :value="tag"
                  class="cursor-pointer"
                >
                  <ComboboxItemIndicator class="mr-2">
                    <Icon name="lucide:check" class="h-4 w-4" />
                  </ComboboxItemIndicator>
                  #{{ tag }}
                </ComboboxItem>
              </ComboboxList>
            </Combobox>
          </div>

          <!-- Number of Ideas -->
          <div class="space-y-2">
            <Label>Number of Ideas</Label>
            <Input
              v-model.number="numIdeas"
              type="number"
              :min="1"
              :max="50"
              class="w-32"
            />
          </div>

          <!-- Creativity Slider -->
          <div class="space-y-2">
            <Label>Creativity: {{ creativity }}</Label>
            <Slider
              v-model="creativityArr"
              :min="0.1"
              :max="1.5"
              :step="0.1"
              class="w-full"
            />
            <div class="flex justify-between text-xs text-muted-foreground">
              <span>Conservative</span>
              <span>Balanced</span>
              <span>Wild</span>
            </div>
          </div>

          <!-- Generate Button -->
          <Button
            @click="generate"
            :disabled="isRunning"
            class="w-full"
          >
            <Icon
              :name="isRunning ? 'lucide:loader-2' : 'lucide:sparkles'"
              :class="['mr-2 h-4 w-4', isRunning ? 'animate-spin' : '']"
            />
            {{ isRunning ? 'Generating...' : 'Generate Ideas' }}
          </Button>
        </div>
      </Card>

      <!-- Progress Section -->
      <Card v-if="taskId" class="p-6 mb-6">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Icon
                v-if="taskState === 'SUCCESS'"
                name="lucide:check-circle"
                class="h-5 w-5 text-green-500"
              />
              <Icon
                v-else-if="taskState === 'FAILURE'"
                name="lucide:x-circle"
                class="h-5 w-5 text-destructive"
              />
              <Icon
                v-else
                name="lucide:loader-2"
                class="h-5 w-5 animate-spin text-primary"
              />
              <span class="font-medium">
                {{ stageLabel }}
              </span>
            </div>
            <Badge
              :variant="taskState === 'SUCCESS' ? 'default' : taskState === 'FAILURE' ? 'destructive' : 'secondary'"
            >
              {{ taskState }}
            </Badge>
          </div>

          <div v-if="taskState === 'STARTED' || taskState === 'PENDING'">
            <Progress :model-value="progressPercent" class="mb-2" />
            <p class="text-sm text-muted-foreground text-right">
              {{ taskProgress }} / {{ taskTotal }}
            </p>
          </div>

          <p v-if="taskState === 'FAILURE' && taskError" class="text-sm text-destructive">
            {{ taskError }}
          </p>
        </div>
      </Card>

      <!-- Results Section -->
      <Card v-if="taskResult" class="p-6">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">Results</h2>
            <a href="/projects?source=nemo_data_designer">
              <Button variant="outline" size="sm">
                View All AI Projects
                <Icon name="lucide:arrow-right" class="ml-2 h-4 w-4" />
              </Button>
            </a>
          </div>

          <p class="text-sm text-muted-foreground">
            Generated {{ taskResult.num_saved }} projects
            <span v-if="taskResult.errors.length > 0">
              ({{ taskResult.errors.length }} error{{ taskResult.errors.length > 1 ? 's' : '' }})
            </span>
          </p>

          <!-- Generated Projects List -->
          <div v-if="generatedProjects.length > 0" class="divide-y rounded-md border">
            <a
              v-for="project in generatedProjects"
              :key="project.id"
              :href="`/projects/${project.id}`"
              class="flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors first:rounded-t-md last:rounded-b-md"
            >
              <div class="flex-1 min-w-0">
                <div class="font-medium text-sm truncate">{{ project.title }}</div>
                <div class="text-xs text-muted-foreground truncate mt-0.5">{{ project.short_description }}</div>
                <div class="flex flex-wrap gap-1 mt-1">
                  <Badge
                    v-for="tag in project.hashtags?.slice(0, 3)"
                    :key="tag"
                    variant="secondary"
                    class="text-[10px] px-1.5 py-0"
                  >
                    #{{ tag }}
                  </Badge>
                </div>
              </div>
              <div class="flex gap-2 flex-shrink-0">
                <Badge variant="outline" class="text-xs">
                  <Icon name="lucide:lightbulb" class="mr-1 h-3 w-3" />
                  {{ project.idea_score }}
                </Badge>
                <Badge variant="outline" class="text-xs">
                  <Icon name="lucide:settings" class="mr-1 h-3 w-3" />
                  {{ project.complexity_score }}
                </Badge>
              </div>
            </a>
          </div>

          <!-- Errors -->
          <div v-if="taskResult.errors.length > 0" class="space-y-2">
            <p class="text-sm font-medium text-destructive">Errors:</p>
            <div v-for="err in taskResult.errors" :key="err.row" class="text-xs text-muted-foreground">
              Row {{ err.row }}: {{ err.error }}
            </div>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WaywoProject, GenerateIdeasStatus } from '~/types/models'
import { toast } from 'vue-sonner'

useHead({
  title: 'Designer - waywo',
  meta: [
    { name: 'description', content: 'Generate AI-powered project ideas.' }
  ]
})

const config = useRuntimeConfig()

// Form state
const selectedTags = ref<string[]>([])
const tagSearchQuery = ref('')
const availableTags = ref<string[]>([])
const numIdeas = ref(5)
const creativityArr = ref([0.85])
const creativity = computed(() => Math.round(creativityArr.value[0] * 10) / 10)

// Filtered tags for autocomplete
const filteredTags = computed(() => {
  const query = tagSearchQuery.value.toLowerCase()
  return availableTags.value
    .filter(tag => !selectedTags.value.includes(tag))
    .filter(tag => tag.toLowerCase().includes(query))
    .slice(0, 20)
})

function removeTag(tag: string) {
  selectedTags.value = selectedTags.value.filter(t => t !== tag)
}

// Task state
const taskId = ref<string | null>(null)
const taskState = ref<string>('PENDING')
const taskStage = ref<string>('')
const taskProgress = ref(0)
const taskTotal = ref(0)
const taskError = ref<string | null>(null)
const taskResult = ref<GenerateIdeasStatus['result'] | null>(null)
const generatedProjects = ref<WaywoProject[]>([])

let pollInterval: ReturnType<typeof setInterval> | null = null

const isRunning = computed(() => {
  return taskId.value !== null && !['SUCCESS', 'FAILURE'].includes(taskState.value)
})

const progressPercent = computed(() => {
  if (taskTotal.value === 0) return 0
  return Math.round((taskProgress.value / taskTotal.value) * 100)
})

const stageLabel = computed(() => {
  if (taskState.value === 'PENDING') return 'Waiting to start...'
  if (taskState.value === 'SUCCESS') return 'Complete'
  if (taskState.value === 'FAILURE') return 'Failed'
  if (taskStage.value) {
    // Capitalize and make readable
    return taskStage.value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase())
  }
  return 'Processing...'
})

// Fetch tags on mount
async function fetchTags() {
  try {
    const response = await $fetch<{ hashtags: string[]; total: number }>(
      `${config.public.apiBase}/api/waywo-projects/hashtags`
    )
    availableTags.value = response.hashtags
  } catch (err) {
    console.error('Failed to fetch tags:', err)
  }
}

// Generate ideas
async function generate() {
  if (isRunning.value) return

  // Reset state
  taskResult.value = null
  generatedProjects.value = []
  taskError.value = null
  taskState.value = 'PENDING'
  taskProgress.value = 0
  taskTotal.value = 0
  taskStage.value = ''

  try {
    const response = await $fetch<{ task_id: string }>(`${config.public.apiBase}/api/generate-ideas`, {
      method: 'POST',
      body: {
        num_ideas: numIdeas.value,
        seed_tags: selectedTags.value.length > 0 ? selectedTags.value : undefined,
        creativity: creativity.value,
      },
    })

    taskId.value = response.task_id
    startPolling()
  } catch (err) {
    console.error('Failed to start generation:', err)
    toast.error('Failed to start idea generation')
  }
}

// Poll for task status
function startPolling() {
  stopPolling()
  pollInterval = setInterval(pollStatus, 3000)
  // Also poll immediately
  pollStatus()
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

async function pollStatus() {
  if (!taskId.value) return

  try {
    const status = await $fetch<GenerateIdeasStatus>(
      `${config.public.apiBase}/api/generate-ideas/${taskId.value}/status`
    )

    taskState.value = status.state

    if (status.state === 'STARTED') {
      taskStage.value = status.stage || ''
      taskProgress.value = status.progress || 0
      taskTotal.value = status.total || 0
    } else if (status.state === 'SUCCESS') {
      stopPolling()
      taskResult.value = status.result || null
      toast.success(`Generated ${status.result?.num_saved || 0} projects`)
      // Fetch the generated projects for display
      if (status.result?.project_ids?.length) {
        fetchGeneratedProjects(status.result.project_ids)
      }
    } else if (status.state === 'FAILURE') {
      stopPolling()
      taskError.value = status.error || 'Unknown error'
      toast.error('Idea generation failed')
    }
  } catch (err) {
    console.error('Failed to poll status:', err)
  }
}

// Fetch generated project details
async function fetchGeneratedProjects(projectIds: number[]) {
  try {
    const response = await $fetch<{
      projects: WaywoProject[]
      total: number
    }>(`${config.public.apiBase}/api/waywo-projects`, {
      params: { source: 'nemo_data_designer', limit: 50, sort: 'newest' },
    })
    // Filter to only the generated project IDs
    generatedProjects.value = response.projects.filter(p => projectIds.includes(p.id))
  } catch (err) {
    console.error('Failed to fetch generated projects:', err)
  }
}

onMounted(() => {
  fetchTags()
})

onUnmounted(() => {
  stopPolling()
})
</script>
