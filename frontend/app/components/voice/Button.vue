<template>
  <div class="flex flex-col items-center">
    <!-- Main button with animated rings -->
    <div class="relative flex items-center justify-center">
      <!-- Pulsing rings for listening state -->
      <div
        v-if="state === 'listening'"
        class="absolute inset-0 flex items-center justify-center"
      >
        <div class="absolute w-32 h-32 rounded-full bg-blue-500/20 animate-ping" />
        <div
          class="absolute w-40 h-40 rounded-full bg-blue-500/10 animate-ping"
          style="animation-delay: 0.3s"
        />
      </div>

      <!-- Processing spinner ring -->
      <div
        v-if="state === 'processing'"
        class="absolute w-32 h-32 rounded-full border-4 border-transparent border-t-purple-500 animate-spin"
      />

      <!-- Speaking wave ring -->
      <div
        v-if="state === 'speaking'"
        class="absolute w-32 h-32 rounded-full border-4 border-green-500/50 animate-pulse"
      />

      <!-- The button itself -->
      <button
        class="relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-offset-2 focus:ring-offset-background"
        :class="buttonClasses"
        :disabled="disabled"
        @mousedown="onPress"
        @mouseup="onRelease"
        @mouseleave="onRelease"
        @touchstart.prevent="onPress"
        @touchend.prevent="onRelease"
      >
        <!-- Mic icon (idle) -->
        <Icon
          v-if="state === 'idle'"
          name="lucide:mic"
          class="h-10 w-10"
        />
        <!-- Mic active icon (listening) -->
        <Icon
          v-if="state === 'listening'"
          name="lucide:mic"
          class="h-10 w-10"
        />
        <!-- Thinking icon (processing) -->
        <Icon
          v-if="state === 'processing'"
          name="lucide:brain"
          class="h-10 w-10 animate-pulse"
        />
        <!-- Speaker icon (speaking) -->
        <Icon
          v-if="state === 'speaking'"
          name="lucide:volume-2"
          class="h-10 w-10"
        />
      </button>
    </div>

    <!-- State label (only show active states) -->
    <p v-if="state !== 'idle'" class="text-sm font-medium mt-3" :class="labelClasses">
      {{ stateLabel }}
    </p>
  </div>
</template>

<script setup lang="ts">
import type { VoiceState } from '~/types/voice'

const props = defineProps<{
  state: VoiceState
  disabled?: boolean
}>()

const emit = defineEmits<{
  press: []
  release: []
}>()

const buttonClasses = computed(() => {
  switch (props.state) {
    case 'idle':
      return 'bg-primary text-primary-foreground hover:bg-primary/90 focus:ring-primary/50 cursor-pointer'
    case 'listening':
      return 'bg-blue-500 text-white scale-110 focus:ring-blue-500/50'
    case 'processing':
      return 'bg-purple-500/80 text-white cursor-wait focus:ring-purple-500/50'
    case 'speaking':
      return 'bg-green-500/80 text-white cursor-default focus:ring-green-500/50'
    default:
      return ''
  }
})

const labelClasses = computed(() => {
  switch (props.state) {
    case 'idle':
      return 'text-muted-foreground'
    case 'listening':
      return 'text-blue-500'
    case 'processing':
      return 'text-purple-500'
    case 'speaking':
      return 'text-green-500'
    default:
      return 'text-muted-foreground'
  }
})

const stateLabel = computed(() => {
  switch (props.state) {
    case 'idle':
      return 'Hold to talk'
    case 'listening':
      return 'Listening...'
    case 'processing':
      return 'Thinking...'
    case 'speaking':
      return 'Speaking...'
    default:
      return ''
  }
})

let isPressed = false

function onPress() {
  if (props.disabled || props.state !== 'idle') return
  isPressed = true
  emit('press')
}

function onRelease() {
  if (!isPressed) return
  isPressed = false
  emit('release')
}
</script>
