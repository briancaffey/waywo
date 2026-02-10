import type { VoiceThread } from '~/types/voice'

/**
 * Composable for managing voice chat threads via REST API.
 *
 * Handles listing, creating, renaming, and deleting threads.
 */
export function useVoiceThreads() {
  const config = useRuntimeConfig()
  const base = `${config.public.apiBase}/api/voice`

  const threads = ref<VoiceThread[]>([])
  const loading = ref(false)
  const activeThreadId = ref<string | null>(null)

  async function fetchThreads() {
    loading.value = true
    try {
      const data = await $fetch<{ threads: VoiceThread[]; total: number }>(
        `${base}/threads`
      )
      threads.value = data.threads
    } catch (err) {
      console.error('Failed to fetch threads:', err)
    } finally {
      loading.value = false
    }
  }

  async function createThread(title?: string): Promise<VoiceThread | null> {
    try {
      const thread = await $fetch<VoiceThread>(`${base}/threads`, {
        method: 'POST',
        body: title ? { title } : {},
      })
      // Prepend to list (newest first)
      threads.value.unshift(thread)
      return thread
    } catch (err) {
      console.error('Failed to create thread:', err)
      return null
    }
  }

  async function renameThread(threadId: string, title: string) {
    try {
      const updated = await $fetch<VoiceThread>(
        `${base}/threads/${threadId}`,
        {
          method: 'PUT',
          body: { title },
        }
      )
      // Update in local list
      const idx = threads.value.findIndex((t) => t.id === threadId)
      if (idx !== -1) {
        threads.value[idx] = { ...threads.value[idx], ...updated }
      }
      return updated
    } catch (err) {
      console.error('Failed to rename thread:', err)
      return null
    }
  }

  async function deleteThread(threadId: string) {
    try {
      await $fetch(`${base}/threads/${threadId}`, {
        method: 'DELETE',
      })
      threads.value = threads.value.filter((t) => t.id !== threadId)
      if (activeThreadId.value === threadId) {
        activeThreadId.value = null
      }
      return true
    } catch (err) {
      console.error('Failed to delete thread:', err)
      return false
    }
  }

  function setActive(threadId: string | null) {
    activeThreadId.value = threadId
  }

  /** Refresh a single thread's title (e.g., after auto-title). */
  async function refreshThread(threadId: string) {
    try {
      const data = await $fetch<VoiceThread>(
        `${base}/threads/${threadId}`
      )
      const idx = threads.value.findIndex((t) => t.id === threadId)
      if (idx !== -1) {
        threads.value[idx] = {
          ...threads.value[idx],
          title: data.title,
          updated_at: data.updated_at,
        }
      }
    } catch {
      // ignore
    }
  }

  return {
    threads: readonly(threads),
    loading: readonly(loading),
    activeThreadId: readonly(activeThreadId),
    fetchThreads,
    createThread,
    renameThread,
    deleteThread,
    setActive,
    refreshThread,
  }
}
