'use client'

import { memo } from 'react'
import {
  Search,
  LayoutGrid,
  List,
  Download,
  X,
  SlidersHorizontal,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { type SignalSeverity } from '@/lib/hooks/useSignals'
import { type ViewMode } from '@/lib/hooks/useSignalsTable'

// ── Domain options — now data-driven ──────────────────────────────────────────
// The domain filter options are passed in from the parent that holds signal data.
// Fallback: a minimal list that appears before data loads.

const DEFAULT_DOMAINS: string[] = ['All']
const DEFAULT_DOMAIN_LABELS: Record<string, string> = { All: 'All Domains' }

/** Build domain filter options from signal data */
export function buildDomainOptions(domains: string[]): { options: string[]; labels: Record<string, string> } {
  const unique = Array.from(new Set(domains)).sort()
  const options = ['All', ...unique]
  const labels: Record<string, string> = { All: 'All Domains' }
  unique.forEach(d => { labels[d] = d.length > 16 ? d.slice(0, 14) + '…' : d })
  return { options, labels }
}

const SEVERITIES: (SignalSeverity | 'All')[] = [
  'All',
  'critical',
  'high',
  'medium',
  'low',
]

const SEVERITY_LABELS: Record<string, string> = {
  All: 'All Severities',
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

// ── Local select primitive ────────────────────────────────────────────────────

interface FilterSelectProps<T extends string> {
  value: T
  options: T[]
  labels: Record<string, string>
  onChange: (v: T) => void
  className?: string
}

function FilterSelect<T extends string>({
  value,
  options,
  labels,
  onChange,
  className,
}: FilterSelectProps<T>) {
  const hasFilter = value !== 'All'
  return (
    <div className={cn('relative', className)}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className={cn(
          'h-9 w-full appearance-none rounded-lg border border-border bg-surface',
          'pl-3 pr-8 text-sm text-body outline-none',
          'transition-colors duration-150',
          'focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30',
          'cursor-pointer',
          hasFilter && 'border-indigo-500/40 text-indigo-400',
        )}
      >
        {options.map((opt) => (
          <option key={opt} value={opt} className="bg-[#0d0d11] text-body">
            {labels[opt] ?? opt}
          </option>
        ))}
      </select>
      {/* chevron */}
      <svg
        className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </div>
  )
}

// ── ViewMode Toggle ───────────────────────────────────────────────────────────

interface ViewToggleProps {
  mode: ViewMode
  onChange: (mode: ViewMode) => void
}

function ViewToggle({ mode, onChange }: ViewToggleProps) {
  return (
    <div className="flex h-9 items-center rounded-lg border border-border bg-surface p-0.5">
      {(
        [
          { id: 'table', icon: List },
          { id: 'grid', icon: LayoutGrid },
        ] as { id: ViewMode; icon: React.ElementType }[]
      ).map(({ id, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={cn(
            'flex h-full w-8 items-center justify-center rounded-md transition-colors duration-150',
            mode === id
              ? 'bg-indigo-500/15 text-indigo-400'
              : 'text-subtle hover:text-body',
          )}
          aria-label={id === 'table' ? 'Table view' : 'Grid view'}
        >
          <Icon className="h-3.5 w-3.5" strokeWidth={1.8} />
        </button>
      ))}
    </div>
  )
}

// ── Main Toolbar ─────────────────────────────────────────────────────────────

interface SignalsToolbarProps {
  searchQuery: string
  onSearchChange: (q: string) => void
  filterDomain: string
  onDomainChange: (d: string) => void
  filterSeverity: SignalSeverity | 'All'
  onSeverityChange: (s: SignalSeverity | 'All') => void
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  resultCount: number
  totalCount: number
  availableDomains?: string[]
  onExport?: () => void
  className?: string
}

export const SignalsToolbar = memo(function SignalsToolbar({
  searchQuery,
  onSearchChange,
  filterDomain,
  onDomainChange,
  filterSeverity,
  onSeverityChange,
  viewMode,
  onViewModeChange,
  resultCount,
  totalCount,
  availableDomains = [],
  onExport,
  className,
}: SignalsToolbarProps) {
  const { options: domainOptions, labels: domainLabels } = availableDomains.length > 0
    ? buildDomainOptions(availableDomains)
    : { options: DEFAULT_DOMAINS, labels: DEFAULT_DOMAIN_LABELS }

  const hasActiveFilters =
    searchQuery.length > 0 ||
    filterDomain !== 'All' ||
    filterSeverity !== 'All'

  function clearAll() {
    onSearchChange('')
    onDomainChange('All')
    onSeverityChange('All')
  }

  return (
    <div
      data-onboarding="signals-toolbar"
      className={cn('flex flex-col gap-3 sm:flex-row sm:items-center', className)}
    >
      {/* Left: search */}
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-subtle" />
        <input
          data-onboarding="signals-search"
          type="text"
          placeholder="Search signals, entities, keywords…"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className={cn(
            'h-9 w-full rounded-lg border border-border bg-surface',
            'pl-8.5 pr-4 text-sm text-body placeholder:text-subtle',
            'outline-none transition-colors duration-150',
            'focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/30',
          )}
          style={{ paddingLeft: '2.125rem' }}
        />
        {searchQuery && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-subtle hover:text-body"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Right: filters + controls */}
      <div className="flex items-center gap-2">
        {/* filter icon — cosmetic on mobile */}
        <SlidersHorizontal className="hidden h-3.5 w-3.5 shrink-0 text-subtle sm:block" />

        <FilterSelect
          value={filterDomain}
          options={domainOptions}
          labels={domainLabels}
          onChange={onDomainChange}
          className="w-36"
        />

        <FilterSelect
          value={filterSeverity}
          options={SEVERITIES}
          labels={SEVERITY_LABELS}
          onChange={onSeverityChange}
          className="w-36"
        />

        {hasActiveFilters && (
          <button
            onClick={clearAll}
            className="flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-xs text-subtle transition-colors hover:border-white/15 hover:text-body"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}

        <ViewToggle mode={viewMode} onChange={onViewModeChange} />

        <button
          onClick={onExport}
          className={cn(
            'flex h-9 items-center gap-1.5 rounded-lg border border-border px-3',
            'text-xs text-subtle transition-colors duration-150',
            'hover:border-white/15 hover:text-body disabled:cursor-not-allowed disabled:opacity-50',
          )}
          aria-label="Export signals"
          disabled={!onExport}
        >
          <Download className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Export</span>
        </button>
      </div>

      {/* Result count row — subtle, shown only when filtering */}
      {hasActiveFilters && (
        <div className="order-last flex w-full items-center gap-1 text-[11px] text-subtle sm:order-none sm:w-auto">
          <span>
            {resultCount} of {totalCount} signals
          </span>
        </div>
      )}
    </div>
  )
})
