<script setup lang="ts">
defineProps<{
  icon: string
  title: string
  description?: string
}>()
</script>

<template>
  <div class="mb-8">
    <div class="flex items-center gap-3 mb-2">
      <div class="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-primary/10 shrink-0">
        <Icon :name="icon" class="h-5 w-5 text-primary" />
      </div>
      <h1 class="text-3xl font-bold tracking-tight">{{ title }}</h1>
    </div>
    <p v-if="description" class="text-base text-muted-foreground ml-[52px]">
      {{ description }}
    </p>
    <div v-if="$slots.default" class="mt-3 ml-[52px]">
      <slot />
    </div>
  </div>
</template>
