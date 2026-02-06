<template>
  <Card
    class="p-4 cursor-pointer hover:border-primary/50 transition-colors"
    @click="$emit('click')"
  >
    <div class="flex justify-between items-start mb-2">
      <div class="flex-1">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs font-mono text-muted-foreground w-6">#{{ rank }}</span>
          <h3 class="text-base font-semibold">{{ result.project.title }}</h3>
        </div>
        <p class="text-sm text-muted-foreground ml-6">{{ result.project.short_description }}</p>
      </div>
      <div class="flex gap-1">
        <Badge variant="outline" class="text-xs flex items-center gap-1">
          <Icon name="lucide:lightbulb" class="h-3 w-3" />
          {{ result.project.idea_score }}
        </Badge>
        <Badge variant="outline" class="text-xs flex items-center gap-1">
          <Icon name="lucide:settings" class="h-3 w-3" />
          {{ result.project.complexity_score }}
        </Badge>
      </div>
    </div>

    <div class="ml-6 flex flex-wrap gap-1 mb-2">
      <Badge
        v-for="tag in result.project.hashtags.slice(0, 4)"
        :key="tag"
        variant="secondary"
        class="text-xs"
      >
        #{{ tag }}
      </Badge>
      <Badge
        v-if="result.project.hashtags.length > 4"
        variant="secondary"
        class="text-xs"
      >
        +{{ result.project.hashtags.length - 4 }}
      </Badge>
    </div>

    <div class="ml-6 flex items-center gap-4 text-xs text-muted-foreground">
      <div class="flex items-center gap-1">
        <Icon name="lucide:target" class="h-3 w-3" />
        <span>Similarity: {{ (result.similarity * 100).toFixed(1) }}%</span>
      </div>
      <div v-if="showRerankScore && result.rerank_score !== undefined" class="flex items-center gap-1">
        <Icon name="lucide:sparkles" class="h-3 w-3 text-primary" />
        <span>Rerank: {{ result.rerank_score.toFixed(2) }}</span>
      </div>
    </div>
  </Card>
</template>

<script setup lang="ts">
interface WaywoProject {
  id: number
  source_comment_id: number
  is_valid_project: boolean
  invalid_reason: string | null
  title: string
  short_description: string
  description: string
  hashtags: string[]
  project_urls: string[]
  url_summaries: Record<string, string>
  idea_score: number
  complexity_score: number
  created_at: string
  processed_at: string
  workflow_logs: string[]
}

interface SearchResult {
  project: WaywoProject
  similarity: number
  rerank_score?: number
}

defineProps<{
  result: SearchResult
  rank: number
  showRerankScore: boolean
}>()

defineEmits<{
  click: []
}>()
</script>
