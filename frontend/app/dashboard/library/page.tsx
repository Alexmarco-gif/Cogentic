'use client'

import { useCallback, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Search,
  SlidersHorizontal,
  BookOpen,
  Bookmark,
  Radio,
  ChevronDown,
  X,
  AlertTriangle,
  Loader2,
  RefreshCw,
  ArrowRight,
} from 'lucide-react'
import { useLibrary } from '@/lib/hooks/useLibrary'
import type { LibraryBrief, LibraryFilterDomain, LibraryFilterType, LibrarySortKey } from '@/lib/hooks/useLibrary'
import { BriefGrid } from '@/components/library/BriefGrid'
import { ReaderModal } from '@/components/library/ReaderModal'
import { WeeklyReport } from '@/components/library/WeeklyReport'

// ── Type label map for filter UI ──────────────────────────────────────────────

const TYPE_LABELS: Record<string, string> = {
  All:            'All types',
  'ai-brief':      'AI Briefs',
  'weekly-report': 'Weekly Reports',
  'deep-analysis': 'Deep Analysis',
  'sector-review': 'Sector Reviews',
}

const SORT_LABELS: Record<LibrarySortKey, string> = {
  date:       'Most recent',
  confidence: 'Confidence',
  readTime:   'Read time',
  title:      'Title A–Z',
}

// ── Filter pill ───────────────────────────────────────────────────────────────

function FilterPill({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-pill border px-3 py-1 text-xs font-medium transition-colors ${
        active
          ? 'border-primary/30 bg-primary/10 text-primary'
          : 'border-border bg-surface text-subtle hover:bg-muted hover:text-body'
      }`}
    >
      {label}
    </button>
  )
}

// ── Sort select ───────────────────────────────────────────────────────────────

function SortSelect({
  value,
  onChange,
}: {
  value: LibrarySortKey
  onChange: (v: LibrarySortKey) => void
}) {
  return (
    <div className="relative flex items-center">
      <select
        value={value}
        onChange={e => onChange(e.target.value as LibrarySortKey)}
        className="appearance-none rounded-lg border border-border bg-surface py-1.5 pl-3 pr-8 text-xs text-body focus:outline-none focus:ring-1 focus:ring-primary/40"
      >
        {(Object.keys(SORT_LABELS) as LibrarySortKey[]).map(k => (
          <option key={k} value={k}>{SORT_LABELS[k]}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-subtle" />
    </div>
  )
}

// ── Weekly report modal wrapper ───────────────────────────────────────────────

function WeeklyReportModal({
  brief,
  onClose,
}: {
  brief: LibraryBrief | null
  onClose: () => void
}) {
  if (!brief) return null
  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/25 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed inset-x-0 bottom-0 top-0 z-50 flex items-stretch justify-center overflow-hidden"
        role="dialog"
        aria-modal="true"
      >
        <div className="hidden flex-1 cursor-pointer lg:block" onClick={onClose} />
        <div className="flex w-full max-w-[820px] flex-col overflow-hidden bg-surface shadow-[0_0_80px_rgba(0,0,0,0.2)]">
          <div className="flex flex-shrink-0 items-center justify-between border-b border-border px-6 py-3">
            <span className="text-xs font-medium text-subtle">Weekly Intelligence Report</span>
            <button
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-subtle hover:bg-muted hover:text-heading"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <WeeklyReport brief={brief} />
          </div>
        </div>
        <div className="hidden flex-1 cursor-pointer lg:block" onClick={onClose} />
      </div>
    </>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LibraryPage() {
  const router = useRouter()
  const {
    briefs,
    weeklyReports,
    loading,
    error,
    refresh,
    searchQuery,
    setSearchQuery,
    filterDomain,
    setFilterDomain,
    filterType,
    setFilterType,
    sortKey,
    setSortKey,
    toggleSave,
    totalSaved,
    allDomains,
    allTypes,
    totalCount,
    hasMore,
    isLoadingMore,
    loadMore,
    loadBriefDetail,
  } = useLibrary()

  const [activeBrief, setActiveBrief]   = useState<LibraryBrief | null>(null)
  const [activeWeekly, setActiveWeekly] = useState<LibraryBrief | null>(null)
  const [showFilters, setShowFilters]   = useState(false)
  const [loadingBriefId, setLoadingBriefId] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)

  const handleOpen = useCallback(async (brief: LibraryBrief) => {
    setDetailError(null)
    if (brief.type === 'weekly-report') {
      setActiveWeekly(brief)
    } else {
      setActiveBrief(brief)
    }
    setLoadingBriefId(brief.id)

    try {
      const detailedBrief = await loadBriefDetail(brief.id)
      if (detailedBrief.type === 'weekly-report') {
        setActiveWeekly(detailedBrief)
      } else {
        setActiveBrief(detailedBrief)
      }
    } catch {
      setDetailError('The full brief could not be refreshed right now. Showing the latest loaded version instead.')
    } finally {
      setLoadingBriefId((current) => (current === brief.id ? null : current))
    }
  }, [loadBriefDetail])

  const latestWeekly = weeklyReports[0] ?? null

  return (
    <div
      data-onboarding="library-page"
      className="flex flex-col overflow-hidden"
      style={{ height: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* ── Page header ────────────────────────────────────────────────────── */}
      <div data-onboarding="library-header" className="flex-shrink-0 border-b border-border bg-surface/80 px-6 py-4 backdrop-blur-sm">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="font-display text-base font-semibold text-heading">Intelligence Library</h1>
            <p className="text-xs text-subtle">
              {totalCount} briefs · {weeklyReports.length} weekly reports
              {totalSaved > 0 && ` · ${totalSaved} saved`}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-3">
            <button
              onClick={() => {
                setDetailError(null)
                void refresh()
              }}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-2.5 text-xs font-semibold text-heading transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh library
            </button>

            {/* Latest weekly report CTA */}
            {latestWeekly && (
              <button
                onClick={() => { void handleOpen(latestWeekly) }}
                className="flex flex-shrink-0 items-center gap-2 rounded-xl border border-primary/20 bg-primary/5 px-4 py-2.5 text-left transition-colors hover:bg-primary/10"
              >
                <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Radio className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-primary">Latest Weekly Report</p>
                  <p className="text-[10px] text-subtle">{latestWeekly.relativeDate}</p>
                </div>
              </button>
            )}
          </div>
        </div>

        {/* ── Toolbar ─────────────────────────────────────────────────────── */}
        <div data-onboarding="library-toolbar" className="mt-4 flex flex-wrap items-center gap-3">

          {/* Search */}
          <div className="relative flex-1 min-w-[200px] max-w-[380px]">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
            <input
              data-onboarding="library-search"
              type="text"
              placeholder="Search briefs, tags, domains…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-border bg-muted py-1.5 pl-8 pr-3 text-xs text-body placeholder:text-subtle focus:border-primary/40 focus:outline-none focus:ring-1 focus:ring-primary/20"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-subtle hover:text-body"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {/* Filter toggle */}
          <button
            onClick={() => setShowFilters(v => !v)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
              showFilters || filterDomain !== 'All' || filterType !== 'All'
                ? 'border-primary/30 bg-primary/10 text-primary'
                : 'border-border bg-surface text-subtle hover:bg-muted'
            }`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filters
            {(filterDomain !== 'All' || filterType !== 'All') && (
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-white">
                {[filterDomain !== 'All', filterType !== 'All'].filter(Boolean).length}
              </span>
            )}
          </button>

          {/* Sort */}
          <SortSelect value={sortKey} onChange={setSortKey} />

          {/* Saved count */}
          {totalSaved > 0 && (
            <div className="flex items-center gap-1.5 rounded-pill border border-border bg-surface px-2.5 py-1 text-xs text-subtle">
              <Bookmark className="h-3 w-3" />
              {totalSaved} saved
            </div>
          )}

          <div className="ml-auto text-xs text-subtle">
            {briefs.length} result{briefs.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* ── Expandable filter row ────────────────────────────────────────── */}
        {showFilters && (
          <div className="mt-3 flex flex-wrap gap-4 border-t border-border pt-3">
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-subtle">Domain</p>
              <div className="flex flex-wrap gap-1.5">
                {allDomains.map(d => (
                  <FilterPill
                    key={d}
                    label={d}
                    active={filterDomain === d}
                    onClick={() => setFilterDomain(d as LibraryFilterDomain)}
                  />
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-subtle">Type</p>
              <div className="flex flex-wrap gap-1.5">
                {allTypes.map(t => (
                  <FilterPill
                    key={t}
                    label={TYPE_LABELS[t] ?? t}
                    active={filterType === t}
                    onClick={() => setFilterType(t as LibraryFilterType)}
                  />
                ))}
              </div>
            </div>
            {(filterDomain !== 'All' || filterType !== 'All') && (
              <button
                onClick={() => { setFilterDomain('All'); setFilterType('All') }}
                className="self-end text-[10px] font-medium text-rose-500 hover:underline"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Grid scroll body ────────────────────────────────────────────────── */}
      <div data-onboarding="library-results" className="flex-1 overflow-x-hidden overflow-y-auto bg-canvas px-6 py-6">
        {loading && totalCount === 0 && (
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-40 animate-pulse rounded-xl border border-border bg-surface" />
            ))}
          </div>
        )}

        {(error || detailError || loadingBriefId) && (
          <div className="mb-6 flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-2 text-sm text-body">
              <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${error ? 'text-rose-500' : 'text-amber-500'}`} />
              <span>
                {loadingBriefId
                  ? 'Opening the full brief…'
                  : error ?? detailError}
              </span>
            </div>
            {error && (
              <button
                onClick={() => {
                  setDetailError(null)
                  void refresh()
                }}
                className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-body hover:bg-muted"
              >
                Retry
              </button>
            )}
          </div>
        )}

        {!loading && !error && briefs.length === 0 && totalCount === 0 && (
          <div className="mb-6 rounded-xl border border-border bg-surface p-6 text-center">
            <h2 className="text-base font-semibold text-heading">No briefs yet</h2>
            <p className="mt-2 text-sm text-subtle">
              Published briefs appear here after Cogent turns live signals into intelligence. Start monitoring something first, then come back once your workspace has fresh signals to synthesize.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-3">
              <button
                onClick={() => router.push('/dashboard/studio')}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-xs font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
              >
                Create contract
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => router.push('/dashboard/marketplace')}
                className="rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold text-heading transition-colors hover:bg-muted"
              >
                Browse sources
              </button>
              <button
                onClick={() => router.push('/dashboard/signals')}
                className="rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold text-heading transition-colors hover:bg-muted"
              >
                Open signals workspace
              </button>
            </div>
          </div>
        )}

        {/* Weekly Reports horizontal strip */}
        {weeklyReports.length > 0 && filterType !== 'weekly-report' && (
          <div className="mb-8">
            <div className="mb-3 flex items-center gap-2">
              <BookOpen className="h-3.5 w-3.5 text-violet-500" />
              <h2 className="text-[11px] font-semibold uppercase tracking-widest text-subtle">
                Weekly Reports
              </h2>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {weeklyReports.map(wr => (
                <button
                  key={wr.id}
                  onClick={() => { void handleOpen(wr) }}
                  className="flex w-60 flex-shrink-0 items-center gap-3 rounded-xl border border-violet-100 bg-violet-50 px-4 py-3 text-left transition-colors hover:border-violet-200 hover:bg-violet-100"
                >
                  <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-violet-500/10">
                    <Radio className="h-4 w-4 text-violet-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[11px] font-medium text-violet-900 line-clamp-1">{wr.title}</p>
                    <p className="text-[10px] text-violet-500">{wr.relativeDate} · {wr.readTimeMinutes}m</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Main masonry grid */}
        <BriefGrid
          briefs={filterType === 'weekly-report'
            ? weeklyReports
            : briefs.filter(b => b.type !== 'weekly-report')}
          onOpen={(brief) => { void handleOpen(brief) }}
          onToggleSave={toggleSave}
        />

        {/* Load More */}
        {hasMore && (
          <div className="mt-8 flex justify-center">
            <button
              onClick={loadMore}
              disabled={isLoadingMore}
              className="flex items-center gap-2 rounded-xl border border-border bg-surface px-6 py-2.5 text-sm font-medium text-body transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoadingMore ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading…
                </>
              ) : (
                'Load more briefs'
              )}
            </button>
          </div>
        )}
      </div>

      {/* ── Modals ─────────────────────────────────────────────────────────── */}
      <ReaderModal brief={activeBrief} onClose={() => setActiveBrief(null)} />
      <WeeklyReportModal brief={activeWeekly} onClose={() => setActiveWeekly(null)} />
    </div>
  )
}
