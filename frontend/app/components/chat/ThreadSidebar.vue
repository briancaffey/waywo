<template>
  <div
    class="fixed left-0 top-0 h-full z-40 transition-transform duration-300"
    :class="isOpen ? 'translate-x-0' : '-translate-x-full'"
  >
    <div class="w-72 h-full bg-background border-r flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b">
        <h3 class="font-semibold text-sm">Conversations</h3>
        <div class="flex items-center gap-1">
          <Button variant="ghost" size="icon" class="h-7 w-7" @click="$emit('new-thread')">
            <Icon name="lucide:plus" class="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" class="h-7 w-7" @click="$emit('close')">
            <Icon name="lucide:panel-left-close" class="h-4 w-4" />
          </Button>
        </div>
      </div>

      <!-- Thread list -->
      <ScrollArea class="flex-1">
        <div class="p-2 space-y-1">
          <div v-if="loading" class="text-center py-8 text-muted-foreground text-sm">
            Loading...
          </div>
          <div v-else-if="threads.length === 0" class="text-center py-8 text-muted-foreground text-sm">
            No conversations yet
          </div>
          <template v-else>
            <button
              v-for="thread in threads"
              :key="thread.id"
              class="w-full text-left px-3 py-2 rounded-md text-sm group hover:bg-accent transition-colors"
              :class="thread.id === activeThreadId ? 'bg-accent' : ''"
              @click="$emit('select-thread', thread.id)"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <p class="truncate font-medium text-xs">{{ thread.title }}</p>
                  <p class="text-[10px] text-muted-foreground mt-0.5">
                    {{ formatRelativeTime(thread.updated_at) }}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
                  @click.stop="$emit('delete-thread', thread.id)"
                >
                  <Icon name="lucide:trash-2" class="h-3 w-3 text-destructive" />
                </Button>
              </div>
            </button>
          </template>
        </div>
      </ScrollArea>
    </div>
  </div>

  <!-- Backdrop -->
  <div
    v-if="isOpen"
    class="fixed inset-0 z-30 bg-background/50 backdrop-blur-sm lg:hidden"
    @click="$emit('close')"
  />
</template>

<script setup lang="ts">
import type { ChatThread } from '~/types/chat'

defineProps<{
  isOpen: boolean
  threads: readonly ChatThread[]
  activeThreadId: string | null
  loading: boolean
}>()

defineEmits<{
  close: []
  'new-thread': []
  'select-thread': [threadId: string]
  'delete-thread': [threadId: string]
}>()

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}
</script>
