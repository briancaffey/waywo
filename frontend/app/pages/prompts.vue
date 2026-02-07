<template>
  <div class="container mx-auto px-4 py-12">
    <div class="max-w-4xl mx-auto">
      <!-- Header -->
      <div class="text-center mb-12">
        <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-6">
          <Icon name="lucide:file-text" class="h-8 w-8 text-primary" />
        </div>
        <h1 class="text-4xl font-bold tracking-tight mb-4">Workflow Prompts</h1>
        <p class="text-xl text-muted-foreground">
          All prompt templates used in the processing pipeline
        </p>
        <a href="/admin" class="inline-flex items-center gap-1 mt-4 text-sm text-muted-foreground hover:text-primary transition-colors">
          <Icon name="lucide:arrow-left" class="h-4 w-4" />
          Back to Admin
        </a>
      </div>

      <!-- Loading -->
      <div v-if="isLoading" class="flex justify-center py-16">
        <Icon name="lucide:loader-2" class="h-8 w-8 animate-spin text-muted-foreground" />
      </div>

      <!-- Error -->
      <Alert v-else-if="error" variant="destructive" class="mb-8">
        <Icon name="lucide:alert-circle" class="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <!-- Steps -->
      <div v-else-if="steps" class="space-y-6">
        <Card v-for="step in steps" :key="step.step" class="overflow-hidden">
          <!-- Step header -->
          <div class="flex items-center gap-3 p-6 pb-4">
            <div class="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground font-bold text-sm shrink-0">
              {{ step.step }}
            </div>
            <div class="flex-1 min-w-0">
              <h2 class="text-lg font-semibold">{{ step.title }}</h2>
              <p class="text-sm text-muted-foreground">{{ step.description }}</p>
            </div>
            <Badge variant="outline" class="shrink-0">{{ step.workflow }}</Badge>
          </div>

          <!-- Event flow -->
          <div class="px-6 pb-3 flex items-center gap-2 text-xs text-muted-foreground">
            <code class="bg-muted px-1.5 py-0.5 rounded">{{ step.input_event }}</code>
            <Icon name="lucide:arrow-right" class="h-3 w-3" />
            <code class="bg-muted px-1.5 py-0.5 rounded">{{ step.output_event }}</code>
          </div>

          <!-- Template variables -->
          <div v-if="step.template_variables.length > 0" class="px-6 pb-3 flex items-center gap-2 flex-wrap">
            <span class="text-xs text-muted-foreground">Variables:</span>
            <Badge v-for="v in step.template_variables" :key="v" variant="secondary" class="text-xs">
              {{ '{' + v + '}' }}
            </Badge>
          </div>

          <!-- Prompt template -->
          <div v-if="step.prompt_template" class="px-6 pb-6">
            <div class="relative">
              <pre class="bg-muted rounded-lg p-4 text-sm overflow-x-auto whitespace-pre-wrap break-words font-mono leading-relaxed">{{ step.prompt_template }}</pre>
            </div>
          </div>

          <!-- No prompt -->
          <div v-else class="px-6 pb-6">
            <div class="bg-muted/50 rounded-lg p-4 text-sm text-muted-foreground italic">
              No LLM prompt — this step uses external services directly.
            </div>
          </div>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { WorkflowStep } from '~/types/models'

useHead({
  title: 'Workflow Prompts - waywo',
  meta: [
    { name: 'description', content: 'Inspect prompt templates used in the processing pipeline.' }
  ]
})

const config = useRuntimeConfig()

const steps = ref<WorkflowStep[] | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)

async function fetchPrompts() {
  isLoading.value = true
  error.value = null

  try {
    const response = await $fetch<{ steps: WorkflowStep[]; total: number }>(
      `${config.public.apiBase}/api/workflow-prompts`
    )
    steps.value = response.steps
  } catch (err) {
    console.error('Failed to fetch workflow prompts:', err)
    error.value = 'Failed to fetch workflow prompts. Make sure the backend is running.'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  fetchPrompts()
})
</script>
