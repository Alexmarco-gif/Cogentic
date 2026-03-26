'use client'

import { useState, useMemo, useCallback } from 'react'
import { type Signal, type SignalDomain, type SignalSeverity } from './useSignals'

// ── Types ─────────────────────────────────────────────────────────────────────

export type SortField =
  | 'severity'
  | 'confidence'
  | 'entityName'
  | 'domain'
  | 'publishedAt'

export type SortDirection = 'asc' | 'desc'

export type ViewMode = 'table' | 'grid'

// Severity ordering for sort
const SEVERITY_ORDER: Record<SignalSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface UseSignalsTableOptions {
  signals: Signal[]
  initialViewMode?: ViewMode
  initialFilterSeverity?: SignalSeverity | 'All'
  initialSearchQuery?: string
}

export interface UseSignalsTableReturn {
  // displayed data
  rows: Signal[]
  totalCount: number
  criticalCount: number
  unreadCount: number
  savedCount: number

  // view state
  viewMode: ViewMode
  setViewMode: (mode: ViewMode) => void

  // sort state
  sortField: SortField
  sortDirection: SortDirection
  setSortField: (field: SortField) => void
  toggleSort: (field: SortField) => void

  // search / filter (mirrors useSignals but local so table can operate independently)
  searchQuery: string
  setSearchQuery: (q: string) => void
  filterDomain: SignalDomain | 'All'
  setFilterDomain: (d: SignalDomain | 'All') => void
  filterSeverity: SignalSeverity | 'All'
  setFilterSeverity: (s: SignalSeverity | 'All') => void

  // row selection
  selectedRowId: string | null
  setSelectedRowId: (id: string | null) => void

  // new-since-load counter
  newSinceLoad: number
}

export function useSignalsTable({
  signals,
  initialViewMode = 'table',
  initialFilterSeverity = 'All',
  initialSearchQuery = '',
}: UseSignalsTableOptions): UseSignalsTableReturn {
  const [viewMode, setViewMode] = useState<ViewMode>(initialViewMode)
  const [sortField, setSortField] = useState<SortField>('publishedAt')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [searchQuery, setSearchQuery] = useState(initialSearchQuery)
  const [filterDomain, setFilterDomain] = useState<SignalDomain | 'All'>('All')
  const [filterSeverity, setFilterSeverity] = useState<SignalSeverity | 'All'>(initialFilterSeverity)
  const [selectedRowId, setSelectedRowId] = useState<string | null>(null)

  // simulate "new since page load" — unread signals count as new
  const newSinceLoad = useMemo(
    () => signals.filter((s) => s.isUnread).length,
    [signals],
  )

  const toggleSort = useCallback(
    (field: SortField) => {
      if (field === sortField) {
        setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'))
      } else {
        setSortField(field)
        setSortDirection('desc')
      }
    },
    [sortField],
  )

  // ── Filtered + sorted rows ────────────────────────────────────────────────
  const rows = useMemo(() => {
    let result = [...signals]

    // search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(
        (s) =>
          s.headline.toLowerCase().includes(q) ||
          s.entityName.toLowerCase().includes(q) ||
          s.summary.toLowerCase().includes(q) ||
          s.domain.toLowerCase().includes(q),
      )
    }

    // domain filter
    if (filterDomain !== 'All') {
      result = result.filter((s) => s.domain === filterDomain)
    }

    // severity filter
    if (filterSeverity !== 'All') {
      result = result.filter((s) => s.severity === filterSeverity)
    }

    // sort
    result.sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'severity':
          cmp = SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
          break
        case 'confidence':
          cmp = a.confidence - b.confidence
          break
        case 'entityName':
          cmp = a.entityName.localeCompare(b.entityName)
          break
        case 'domain':
          cmp = a.domain.localeCompare(b.domain)
          break
        case 'publishedAt':
          cmp =
            new Date(a.publishedAt).getTime() -
            new Date(b.publishedAt).getTime()
          break
      }
      return sortDirection === 'asc' ? cmp : -cmp
    })

    return result
  }, [signals, searchQuery, filterDomain, filterSeverity, sortField, sortDirection])

  // ── Derived counts (from full unfiltered signals) ─────────────────────────
  const totalCount = signals.length
  const criticalCount = useMemo(
    () => signals.filter((s) => s.severity === 'critical').length,
    [signals],
  )
  const unreadCount = useMemo(
    () => signals.filter((s) => s.isUnread).length,
    [signals],
  )
  const savedCount = useMemo(
    () => signals.filter((s) => s.isSaved).length,
    [signals],
  )

  return {
    rows,
    totalCount,
    criticalCount,
    unreadCount,
    savedCount,
    viewMode,
    setViewMode,
    sortField,
    sortDirection,
    setSortField,
    toggleSort,
    searchQuery,
    setSearchQuery,
    filterDomain,
    setFilterDomain,
    filterSeverity,
    setFilterSeverity,
    selectedRowId,
    setSelectedRowId,
    newSinceLoad,
  }
}
