'use client'

import { Suspense, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useSignals, type Signal, type SignalSeverity } from '@/lib/hooks/useSignals'
import { useSignalsTable } from '@/lib/hooks/useSignalsTable'
import { SignalsStatsBar } from '@/components/signals/SignalsStatsBar'
import { SignalsToolbar } from '@/components/signals/SignalsToolbar'
import { SignalsTable } from '@/components/signals/SignalsTable'
import { SignalDrawer } from '@/components/signals/SignalDrawer'
import { useDomains } from '@/lib/hooks/useDomains'

// ── Filter param → severity / search mapping ──────────────────────────────────
const FILTER_TO_SEVERITY: Record<string, SignalSeverity | 'All'> = {
  'critical-alerts': 'critical',
  'risks':           'high',
  'opportunities':   'medium',
}
const FILTER_TO_QUERY: Record<string, string> = {
  'investigations': 'investigation',
}

// ── Page header ───────────────────────────────────────────────────────────────

function PageHeader({ newSinceLoad }: { newSinceLoad: number }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="font-display text-xl font-semibold text-heading">
          Intelligence Signals
        </h1>
        <p className="mt-0.5 text-sm text-subtle">
          Real-time strategic intelligence across your monitored sectors
        </p>
      </div>

      {newSinceLoad > 0 && (
        <div
          className={cn(
            'flex items-center gap-2 rounded-full border border-amber-500/25',
            'bg-amber-500/8 px-3 py-1.5',
          )}
        >
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400" />
          </span>
          <span className="text-xs font-medium text-amber-300">
            {newSinceLoad} new signal{newSinceLoad !== 1 ? 's' : ''}
          </span>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

function SignalsInner() {
  const searchParams = useSearchParams()
  const filterParam  = searchParams.get('filter') ?? ''

  const initialFilterSeverity = FILTER_TO_SEVERITY[filterParam]
  const initialSearchQuery    = FILTER_TO_QUERY[filterParam] ?? ''

  const {
    signals,
    activeDrawerSignal,
    openDrawer,
    closeDrawer,
    toggleSave,
    dismiss,
  } = useSignals()

  const { names: domainNames } = useDomains()

  const {
    rows,
    totalCount,
    criticalCount,
    unreadCount,
    savedCount,
    viewMode,
    setViewMode,
    sortField,
    sortDirection,
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
  } = useSignalsTable({ signals, initialFilterSeverity, initialSearchQuery })

  const handleRowClick = useCallback(
    (signal: Signal) => {
      if (selectedRowId === signal.id) {
        setSelectedRowId(null)
        closeDrawer()
      } else {
        setSelectedRowId(signal.id)
        openDrawer(signal)
      }
    },
    [selectedRowId, setSelectedRowId, openDrawer, closeDrawer],
  )

  const handleDrawerClose = useCallback(() => {
    setSelectedRowId(null)
    closeDrawer()
  }, [setSelectedRowId, closeDrawer])

  const handleSave = useCallback(
    (signal: Signal) => toggleSave(signal.id),
    [toggleSave],
  )

  const handleDismiss = useCallback(
    (signal: Signal) => {
      dismiss(signal.id)
      if (selectedRowId === signal.id) {
        setSelectedRowId(null)
        closeDrawer()
      }
    },
    [dismiss, selectedRowId, setSelectedRowId, closeDrawer],
  )

  return (
    <>
      <div
        className={cn(
          'flex min-h-full flex-col gap-5 px-6 py-6 transition-all duration-300',
          activeDrawerSignal ? 'mr-[440px]' : '',
        )}
      >
        <PageHeader newSinceLoad={newSinceLoad} />

        <SignalsStatsBar
          total={totalCount}
          critical={criticalCount}
          unread={unreadCount}
          saved={savedCount}
        />

        <SignalsToolbar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          filterDomain={filterDomain}
          onDomainChange={setFilterDomain}
          filterSeverity={filterSeverity}
          onSeverityChange={setFilterSeverity}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          resultCount={rows.length}
          totalCount={totalCount}
          availableDomains={domainNames}
        />

        <SignalsTable
          rows={rows}
          allSignals={signals}
          viewMode={viewMode}
          sortField={sortField}
          sortDirection={sortDirection}
          selectedRowId={selectedRowId}
          onRowClick={handleRowClick}
          onSave={handleSave}
          onDismiss={handleDismiss}
          onSort={toggleSort}
          className="flex-1"
        />
      </div>

      <SignalDrawer
        signal={activeDrawerSignal}
        onClose={handleDrawerClose}
        onSave={(id) => toggleSave(id)}
      />
    </>
  )
}

export default function SignalsPage() {
  return (
    <Suspense fallback={null}>
      <SignalsInner />
    </Suspense>
  )
}
