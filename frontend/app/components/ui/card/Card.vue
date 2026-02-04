<script setup lang="ts">
import type { HTMLAttributes } from "vue"
import { cn } from '~/lib/utils'
import { useAttrs } from 'vue'

defineOptions({
  inheritAttrs: false
})

const props = defineProps<{
  class?: HTMLAttributes["class"]
}>()

const attrs = useAttrs()
</script>

<template>
  <div
    data-slot="card"
    :class="
      cn(
        'bg-card text-card-foreground flex flex-col gap-6 rounded-xl border py-6 shadow-sm',
        props.class,
      )
    "
    v-bind="attrs"
  >
    <slot />
  </div>
</template>
