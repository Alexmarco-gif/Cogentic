import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Merges Tailwind classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format relative time (e.g. "2h ago") */
export function timeAgo(date: Date | string): string {
  const now = new Date()
  const past = new Date(date)
  const diffMs = now.getTime() - past.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}

/** Returns confidence color class */
export function confidenceClass(score: number): string {
  if (score >= 75) return 'confidence-high'
  if (score >= 50) return 'confidence-medium'
  return 'confidence-low'
}

/** Returns confidence color for charts */
export function confidenceColor(score: number): string {
  if (score >= 75) return '#059669'
  if (score >= 50) return '#D97706'
  return '#E11D48'
}

/** Truncates text to n characters with ellipsis */
export function truncate(text: string, n: number): string {
  return text.length > n ? text.slice(0, n) + '…' : text
}
