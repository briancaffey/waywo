type FetchOptions = Parameters<typeof $fetch>[1]

/**
 * Composable providing a typed API client with automatic base URL,
 * loading state, and error handling.
 *
 * Usage:
 *   const { api, isLoading, error } = useApi()
 *   const data = await api<ResponseType>('/api/waywo-projects')
 */
export function useApi() {
  const config = useRuntimeConfig()
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function api<T>(path: string, options?: FetchOptions): Promise<T | null> {
    isLoading.value = true
    error.value = null
    try {
      const result = await $fetch<T>(`${config.public.apiBase}${path}`, options)
      return result
    } catch (err: any) {
      error.value = err.data?.detail || err.message || 'An unexpected error occurred'
      return null
    } finally {
      isLoading.value = false
    }
  }

  return { api, isLoading, error }
}
