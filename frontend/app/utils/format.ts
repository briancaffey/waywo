/**
 * Format a Unix timestamp (seconds) to a readable date string.
 */
export function formatUnixTime(timestamp: number | null, includeTime = true): string {
  if (!timestamp) return 'Unknown date'
  const date = new Date(timestamp * 1000)
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }
  if (includeTime) {
    options.hour = '2-digit'
    options.minute = '2-digit'
  }
  return date.toLocaleDateString('en-US', options)
}

/**
 * Format a year/month pair to a readable date string (e.g. "Mar 2024").
 */
export function formatYearMonth(year: number | null, month: number | null): string {
  if (!year || !month) return 'Unknown'
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${monthNames[month - 1]} ${year}`
}

/**
 * Format an ISO date string to a readable date.
 */
export function formatISODate(dateStr: string, includeTime = false): string {
  const date = new Date(dateStr)
  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }
  if (includeTime) {
    options.hour = '2-digit'
    options.minute = '2-digit'
  }
  return date.toLocaleDateString('en-US', options)
}
