<template>
  <div v-if="visibleSteps.length > 0" class="space-y-2 mb-3">
    <div
      v-for="(step, i) in visibleSteps"
      :key="i"
    >
      <!-- Tool Call: Analytics Query -->
      <div
        v-if="step.type === 'tool_call' && isAnalytics(step)"
        class="rounded-xl border border-blue-200 bg-blue-50/60 px-3.5 py-2.5 dark:border-blue-500/20 dark:bg-blue-950/30"
      >
        <div class="flex items-center gap-2.5">
          <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-blue-100 dark:bg-blue-900/50">
            <Icon name="lucide:bar-chart-3" class="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          </div>
          <button
            class="flex items-center gap-1.5 text-sm text-blue-700 dark:text-blue-300 hover:underline cursor-pointer"
            @click="toggleSql(i)"
          >
            Running analytics query
            <Icon
              :name="expandedSql.has(i) ? 'lucide:chevron-up' : 'lucide:chevron-down'"
              class="h-3.5 w-3.5"
            />
          </button>
        </div>
        <div v-if="expandedSql.has(i)" class="mt-2 ml-8.5">
          <pre class="overflow-x-auto rounded-lg bg-blue-100/80 px-3 py-2 text-xs text-blue-800 dark:bg-blue-900/40 dark:text-blue-200"><code>{{ extractSql(step) }}</code></pre>
        </div>
      </div>

      <!-- Tool Call: Search / Project Lookup -->
      <div
        v-else-if="step.type === 'tool_call'"
        class="flex items-center gap-2.5 rounded-xl border border-blue-200 bg-blue-50/60 px-3.5 py-2.5 dark:border-blue-500/20 dark:bg-blue-950/30"
      >
        <div class="flex h-6 w-6 items-center justify-center rounded-md bg-blue-100 dark:bg-blue-900/50">
          <Icon name="lucide:search" class="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        </div>
        <span class="text-sm text-blue-700 dark:text-blue-300">
          Searching for <span class="font-medium">"{{ formatInput(step) }}"</span>
        </span>
      </div>

      <!-- Tool Result: Analytics -->
      <div
        v-if="step.type === 'tool_result' && isAnalytics(step)"
        class="flex items-center gap-2.5 rounded-xl border border-green-200 bg-green-50/60 px-3.5 py-2.5 dark:border-green-500/20 dark:bg-green-950/30"
      >
        <div class="flex h-6 w-6 items-center justify-center rounded-md bg-green-100 dark:bg-green-900/50">
          <Icon name="lucide:check" class="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
        </div>
        <span class="text-sm text-green-700 dark:text-green-300">
          Query executed
        </span>
      </div>

      <!-- Tool Result: Search / Project Lookup -->
      <div
        v-else-if="step.type === 'tool_result'"
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

const expandedSql = ref<Set<number>>(new Set())

function toggleSql(index: number) {
  const next = new Set(expandedSql.value)
  if (next.has(index)) {
    next.delete(index)
  } else {
    next.add(index)
  }
  expandedSql.value = next
}

function isAnalytics(step: AgentStep): boolean {
  return step.tool === 'run_analytics_query'
}

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

function extractSql(step: AgentStep): string {
  const raw = step.input ?? ''
  try {
    const parsed = JSON.parse(raw)
    if (parsed.sql) return parsed.sql
  } catch {
    // input may be truncated JSON — extract sql value with regex
    const match = raw.match(/"sql":\s*"((?:[^"\\]|\\.)*)"?/)
    if (match) return match[1].replace(/\\n/g, '\n').replace(/\\"/g, '"')
  }
  return raw
}
</script>
