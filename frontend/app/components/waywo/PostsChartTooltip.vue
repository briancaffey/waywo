<script setup lang="ts">
const props = defineProps<{
  title?: string
  data: {
    name: string
    color: string
    value: any
  }[]
}>()

// Find specific values from data array
function findValue(name: string): any {
  return props.data.find(d => d.name === name)?.value
}
</script>

<template>
  <div class="bg-popover text-popover-foreground border rounded-lg shadow-lg p-3 text-sm">
    <div class="font-semibold mb-2">{{ title }}</div>
    <div class="flex flex-col gap-1 min-w-[120px]">
      <div class="flex justify-between items-center gap-4">
        <span class="text-muted-foreground">Stored</span>
        <span class="font-semibold">{{ findValue('comment_count')?.toLocaleString() ?? '-' }}</span>
      </div>
      <div class="flex justify-between items-center gap-4">
        <span class="text-muted-foreground">Total</span>
        <span class="text-muted-foreground">{{ findValue('total_comments')?.toLocaleString() ?? '-' }}</span>
      </div>
    </div>
  </div>
</template>
