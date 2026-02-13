<template>
  <div v-if="visibleSteps.length > 0" class="space-y-2 mb-3">
    <div
      v-for="(step, i) in visibleSteps"
      :key="i"
    >
      <!-- Tool Call -->
      <div
        v-if="step.type === 'tool_call'"
        class="flex items-center gap-2.5 rounded-xl border border-blue-200 bg-blue-50/60 px-3.5 py-2.5 dark:border-blue-500/20 dark:bg-blue-950/30"
      >
        <div class="flex h-6 w-6 items-center justify-center rounded-md bg-blue-100 dark:bg-blue-900/50">
          <Icon name="lucide:search" class="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        </div>
        <span class="text-sm text-blue-700 dark:text-blue-300">
          Searching for <span class="font-medium">"{{ formatInput(step) }}"</span>
        </span>
      </div>

      <!-- Tool Result -->
      <div
        v-if="step.type === 'tool_result'"
        class="flex items-center gap-2.5 rounded-xl border border-green-200 bg-green-50/60 px-3.5 py-2.5 dark:border-green-500/20 dark:bg-green-950/30"
      >
        <div class="flex h-6 w-6 items-center justify-center rounded-md bg-green-100 dark:bg-green-900/50">
          <Icon name="lucide:database" class="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
        </div>
        <span class="text-sm text-green-700 dark:text-green-300">
          Found {{ step.projects_found }} project{{ step.projects_found === 1 ? '' : 's' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AgentStep } from '~/types/models'

const props = defineProps<{
  steps: AgentStep[]
}>()

const visibleSteps = computed(() =>
  props.steps.filter((s) => s.type === 'tool_call' || s.type === 'tool_result')
)

function formatInput(step: AgentStep): string {
  const raw = step.input ?? ''
  // Try to extract query from JSON like {"query": "shipping freight", "top_k": 5}
  try {
    const parsed = JSON.parse(raw)
    if (parsed.query) return parsed.query
  } catch {
    // not JSON
  }
  return raw
}
</script>
