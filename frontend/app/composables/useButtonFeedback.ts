/**
 * Composable for inline button feedback — replaces alert/confirm dialogs.
 *
 * Two patterns:
 *  1. confirmOrProceed(key) — first click shows "Sure?" state, second click proceeds.
 *     Auto-resets to idle after timeout if not confirmed.
 *  2. showSuccess(key) / showError(key) — briefly flashes the button green/red with
 *     a checkmark/X icon, then resets.
 */

export type ButtonFeedback = 'idle' | 'confirming' | 'success' | 'error'

export function useButtonFeedback() {
  const feedbacks = reactive<Record<string, ButtonFeedback>>({})
  const timers = new Map<string, ReturnType<typeof setTimeout>>()

  function getFeedback(key: string): ButtonFeedback {
    return feedbacks[key] || 'idle'
  }

  function _set(key: string, state: ButtonFeedback, autoResetMs: number) {
    const existing = timers.get(key)
    if (existing) clearTimeout(existing)

    feedbacks[key] = state

    if (state !== 'idle') {
      timers.set(key, setTimeout(() => {
        feedbacks[key] = 'idle'
        timers.delete(key)
      }, autoResetMs))
    }
  }

  /**
   * Two-click confirm pattern.
   * First call → enters 'confirming' state, returns false (don't act yet).
   * Second call while confirming → returns true (proceed with action).
   */
  function confirmOrProceed(key: string, timeoutMs: number = 3000): boolean {
    if (feedbacks[key] === 'confirming') {
      // Second click — proceed
      const existing = timers.get(key)
      if (existing) clearTimeout(existing)
      timers.delete(key)
      feedbacks[key] = 'idle'
      return true
    }
    // First click — enter confirming state
    _set(key, 'confirming', timeoutMs)
    return false
  }

  function showSuccess(key: string, durationMs: number = 1500) {
    _set(key, 'success', durationMs)
  }

  function showError(key: string, durationMs: number = 2000) {
    _set(key, 'error', durationMs)
  }

  onUnmounted(() => {
    for (const timer of timers.values()) {
      clearTimeout(timer)
    }
  })

  return { getFeedback, confirmOrProceed, showSuccess, showError }
}
