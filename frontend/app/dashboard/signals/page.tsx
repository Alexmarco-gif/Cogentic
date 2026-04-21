'use client'

import { Suspense, useCallback, useEffect, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useSignals, type Signal, type SignalSeverity } from '@/lib/hooks/useSignals'
import { useSignalsTable } from '@/lib/hooks/useSignalsTable'
import { SignalsStatsBar } from '@/components/signals/SignalsStatsBar'
import { SignalsToolbar } from '@/components/signals/SignalsToolbar'
import { SignalsTable } from '@/components/signals/SignalsTable'
import { SignalDrawer } from '@/components/signals/SignalDrawer'

const FILTER_TO_SEVERITY: Record<string, SignalSeverity | 'All'> = {
  'critical-alerts': 'critical',
  risks: 'high',
  opportunities: 'medium',
}

const FILTER_TO_QUERY: Record<string, string> = {
  investigations: 'investigation',
}

function escapeCsvCell(value: string | number | boolean | null | undefined): string {
  const stringValue = value == null ? '' : String(value)
  return `"${stringValue.replace(/"/g, '""')}"`
}

function buildSignalsCsv(signals: Signal[]): string {
  const header = ['Entity', 'Domain', 'Severity', 'Confidence', 'Headline', 'Summary', 'Published At', 'Saved']
  const rows = signals.map((signal) => ([
    signal.entityName,
    signal.domain,
    signal.severity,
    signal.confidence,
    signal.headline,
    signal.summary,
    signal.publishedAt,
    signal.isSaved,
  ].map(escapeCsvCell).join(',')))

  return [header.map(escapeCsvCell).join(','), ...rows].join('\n')
}

function mergeSignalsQuery(
  searchParams: URLSearchParams,
  updates: Record<string, string | null | undefined>,
): string {
  const next = new URLSearchParams(searchParams.toString())

  Object.entries(updates).forEach(([key, value]) => {
    if (value) {
      next.set(key, value)
    } else {
      next.delete(key)
    }
  })

  return next.toString()
}

function PageHeader({ newSinceLoad }: { newSinceLoad: number }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div>
        <h1 className="font-display text-xl font-semibold text-heading">
          Intelligence Signals
        </h1>
        <p className="mt-0.5 text-sm text-subtle">
          Strategic intelligence across your monitored sectors
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

function LoadingState() {
  return (
    <div className="rounded-card border border-border bg-canvas p-6">
      <div className="animate-pulse space-y-3">
        <div className="h-4 w-40 rounded bg-muted" />
        <div className="h-16 rounded-xl bg-muted/70" />
        <div className="h-16 rounded-xl bg-muted/60" />
        <div className="h-16 rounded-xl bg-muted/50" />
      </div>
    </div>
  )
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-card border border-rose-200 bg-rose-50 px-4 py-4 text-sm text-rose-800">
      <p className="font-medium">Signals could not be loaded.</p>
      <p className="mt-1 text-rose-700">{message}</p>
      <button
        onClick={onRetry}
        className="mt-3 rounded-lg border border-rose-200 bg-white px-3 py-2 text-xs font-medium text-rose-800 transition-colors hover:bg-rose-100"
      >
        Retry
      </button>
    </div>
  )
}

function SignalsInner() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const filterParam = searchParams.get('filter') ?? ''
  const openParam = searchParams.get('open') ?? ''

  const initialFilterSeverity = FILTER_TO_SEVERITY[filterParam]
  const initialSearchQuery = FILTER_TO_QUERY[filterParam] ?? ''

  const {
    signals,
    loading,
    error,
    activeDrawerSignal,
    openDrawer,
    openDrawerById,
    closeDrawer,
    toggleSave,
    dismiss,
    hasMore,
    isLoadingMore,
    loadMore,
    refresh,
  } = useSignals()

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

  const availableDomains = useMemo(
    () => Array.from(new Set(signals.map((signal) => signal.domain))).sort(),
    [signals],
  )

  const replaceQuery = useCallback((updates: Record<string, string | null | undefined>) => {
    const nextQuery = mergeSignalsQuery(new URLSearchParams(searchParams.toString()), updates)
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname, { scroll: false })
  }, [pathname, router, searchParams])

  useEffect(() => {
    if (!openParam || activeDrawerSignal?.id === openParam) return
    setSelectedRowId(openParam)
    void openDrawerById(openParam)
  }, [activeDrawerSignal?.id, openDrawerById, openParam, setSelectedRowId])

  const handleRowClick = useCallback((signal: Signal) => {
    if (selectedRowId === signal.id) {
      setSelectedRowId(null)
      closeDrawer()
      replaceQuery({ open: null })
      return
    }

    setSelectedRowId(signal.id)
    openDrawer(signal)
    replaceQuery({ open: signal.id })
  }, [closeDrawer, openDrawer, replaceQuery, selectedRowId, setSelectedRowId])

  const handleDrawerClose = useCallback(() => {
    setSelectedRowId(null)
    closeDrawer()
    replaceQuery({ open: null })
  }, [closeDrawer, replaceQuery, setSelectedRowId])

  const handleSave = useCallback((signal: Signal) => {
    toggleSave(signal.id)
  }, [toggleSave])

  const handleDismiss = useCallback((signal: Signal) => {
    dismiss(signal.id)
    if (selectedRowId === signal.id) {
      setSelectedRowId(null)
      closeDrawer()
      replaceQuery({ open: null })
    }
  }, [closeDrawer, dismiss, replaceQuery, selectedRowId, setSelectedRowId])

  const handleExport = useCallback(() => {
    const csv = buildSignalsCsv(rows)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `signals-${new Date().toISOString().slice(0, 10)}.csv`
    anchor.click()
    URL.revokeObjectURL(url)
  }, [rows])

  return (
    <>
      <div
        data-onboarding="signals-page"
        className={cn(
          'flex min-h-full flex-col gap-5 px-6 py-6 transition-all duration-300',
          activeDrawerSignal ? 'xl:mr-[440px]' : '',
        )}
      >
        <div data-onboarding="signals-header">
          <PageHeader newSinceLoad={newSinceLoad} />
        </div>

        <div data-onboarding="signals-stats">
          <SignalsStatsBar
            total={totalCount}
            critical={criticalCount}
            unread={unreadCount}
            saved={savedCount}
          />
        </div>

        <div data-onboarding="signals-toolbar">
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
            availableDomains={availableDomains}
            onExport={handleExport}
          />
        </div>

        {error && !loading && signals.length === 0 ? (
          <ErrorState message={error} onRetry={refresh} />
        ) : loading && signals.length === 0 ? (
          <LoadingState />
        ) : (
          <>
            {error && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
                {error}
              </div>
            )}

            {!error && !loading && signals.length === 0 && (
              <div className="rounded-card border border-border bg-surface px-5 py-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-heading">Your signals workspace is ready for live intelligence.</p>
                    <p className="mt-1 text-xs text-subtle">
                      No signals have landed yet. Define what you want monitored in Studio or activate a managed source in Marketplace, then come back here to review the first cards and dossiers.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => router.push('/dashboard/studio')}
                      className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
                    >
                      Create contract
                    </button>
                    <button
                      onClick={() => router.push('/dashboard/marketplace')}
                      className="rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold text-heading transition-colors hover:bg-muted"
                    >
                      Browse sources
                    </button>
                  </div>
                </div>
              </div>
            )}

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

            {hasMore && (
              <div className="flex justify-center">
                <button
                  onClick={() => void loadMore()}
                  disabled={isLoadingMore}
                  className="rounded-lg border border-border bg-surface px-4 py-2 text-sm text-body transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isLoadingMore ? 'Loading more...' : 'Load more signals'}
                </button>
              </div>
            )}
          </>
        )}
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
