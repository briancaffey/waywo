import type { ChatThread } from '~/types/chat'

export function useChatThreads() {
  const config = useRuntimeConfig()
  const base = `${config.public.apiBase}/api/chat`

  const threads = ref<ChatThread[]>([])
  const loading = ref(false)
  const activeThreadId = ref<string | null>(null)

  async function fetchThreads() {
    loading.value = true
    try {
      const data = await $fetch<{ threads: ChatThread[]; total: number }>(
        `${base}/threads`
      )
      threads.value = data.threads
    } catch (err) {
      console.error('Failed to fetch chat threads:', err)
    } finally {
      loading.value = false
    }
  }

  async function createThread(title?: string): Promise<ChatThread | null> {
    try {
      const thread = await $fetch<ChatThread>(`${base}/threads`, {
        method: 'POST',
        body: title ? { title } : {},
      })
      threads.value.unshift(thread)
      activeThreadId.value = thread.id
      return thread
    } catch (err) {
      console.error('Failed to create chat thread:', err)
      return null
    }
  }

  async function renameThread(threadId: string, title: string) {
    try {
      const updated = await $fetch<ChatThread>(
        `${base}/threads/${threadId}`,
        { method: 'PUT', body: { title } }
      )
      const idx = threads.value.findIndex((t) => t.id === threadId)
      if (idx !== -1) {
        threads.value[idx] = { ...threads.value[idx], title: updated.title, updated_at: updated.updated_at }
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

  async function refreshThread(threadId: string) {
    try {
      const data = await $fetch<ChatThread>(
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
