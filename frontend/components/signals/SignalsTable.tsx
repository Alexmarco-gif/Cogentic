'use client'

import { memo } from 'react'
import { ArrowUp, ArrowDown, ArrowUpDown, Inbox } from 'lucide-react'
import { cn } from '@/lib/utils'
import { type Signal } from '@/lib/hooks/useSignals'
import { type SortField, type SortDirection, type ViewMode } from '@/lib/hooks/useSignalsTable'
import { SignalTableRow } from './SignalTableRow'
import { SignalCard } from './SignalCard'

// ── Table header column definitions ──────────────────────────────────────────

interface Column {
  key: SortField | '_entity' | '_headline' | '_actions'
  label: string
  sortField?: SortField
  className?: string
}

const COLUMNS: Column[] = [
  { key: '_entity', label: 'Entity & Domain', className: 'w-44 shrink-0' },
  { key: '_headline', label: 'Signal', className: 'flex-1' },
  { key: 'confidence', label: 'Conf.', sortField: 'confidence', className: 'hidden w-14 shrink-0 text-right lg:block' },
  { key: 'severity', label: 'Severity', sortField: 'severity', className: 'hidden w-16 shrink-0 text-center md:block' },
  { key: 'publishedAt', label: 'Time', sortField: 'publishedAt', className: 'hidden w-16 shrink-0 text-right lg:block' },
  { key: '_actions', label: '', className: 'w-24 shrink-0' },
]

// ── Sort icon ─────────────────────────────────────────────────────────────────

function SortIcon({
  field,
  active,
  direction,
}: {
  field: SortField
  active: boolean
  direction: SortDirection
}) {
  if (!active) {
    return <ArrowUpDown className="ml-1 h-3 w-3 text-subtle/50" />
  }
  return direction === 'asc' ? (
    <ArrowUp className="ml-1 h-3 w-3 text-indigo-400" />
  ) : (
    <ArrowDown className="ml-1 h-3 w-3 text-indigo-400" />
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-24">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface border border-border">
        <Inbox className="h-5 w-5 text-subtle" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-heading">No signals match your filters</p>
        <p className="mt-1 text-xs text-subtle">Try adjusting your search or filters</p>
      </div>
    </div>
  )
}

// ── Confidence histogram ──────────────────────────────────────────────────────

function ConfidenceHistogram({ signals }: { signals: Signal[] }) {
  if (!signals.length) return null

  // bucket into 5 ranges: <60, 60-70, 70-80, 80-90, 90+
  const buckets = [
    { label: '<60', min: 0, max: 59 },
    { label: '60–70', min: 60, max: 69 },
    { label: '70–80', min: 70, max: 79 },
    { label: '80–90', min: 80, max: 89 },
    { label: '90+', min: 90, max: 100 },
  ]

  const counts = buckets.map((b) =>
    signals.filter((s) => s.confidence >= b.min && s.confidence <= b.max).length,
  )
  const maxCount = Math.max(...counts, 1)

  return (
    <div className="flex items-end gap-1.5 px-4 py-2 border-b border-border bg-canvas/60">
      <span className="mr-1 text-[10px] text-subtle font-medium">Confidence distribution</span>
      {buckets.map((b, i) => {
        const height = Math.round((counts[i] / maxCount) * 24)
        return (
          <div key={b.label} className="flex flex-col items-center gap-0.5" title={`${b.label}%: ${counts[i]} signals`}>
            <div
              className={cn(
                'w-7 rounded-sm transition-all duration-300',
                counts[i] === 0 ? 'bg-white/5' : 'bg-indigo-500/30',
              )}
              style={{ height: Math.max(height, 3) }}
            />
            <span className="text-[9px] text-subtle/60">{b.label}</span>
          </div>
        )
      })}
    </div>
  )
}

// ── Main SignalsTable ─────────────────────────────────────────────────────────

interface SignalsTableProps {
  rows: Signal[]
  allSignals: Signal[]
  viewMode: ViewMode
  sortField: SortField
  sortDirection: SortDirection
  selectedRowId: string | null
  onRowClick: (signal: Signal) => void
  onSave: (signal: Signal) => void
  onDismiss: (signal: Signal) => void
  onSort: (field: SortField) => void
  className?: string
}

export const SignalsTable = memo(function SignalsTable({
  rows,
  allSignals,
  viewMode,
  sortField,
  sortDirection,
  selectedRowId,
  onRowClick,
  onSave,
  onDismiss,
  onSort,
  className,
}: SignalsTableProps) {
  // ── Grid mode ───────────────────────────────────────────────────────────────
  if (viewMode === 'grid') {
    return (
      <div className={cn('rounded-card border border-border bg-canvas overflow-hidden', className)}>
        <ConfidenceHistogram signals={allSignals} />
        {rows.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2 xl:grid-cols-3">
            {rows.map((signal) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                onClick={() => onRowClick(signal)}
                onSave={() => onSave(signal)}
                onDismiss={() => onDismiss(signal)}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Table mode ──────────────────────────────────────────────────────────────
  return (
    <div
      className={cn(
        'overflow-hidden rounded-card border border-border bg-canvas',
        className,
      )}
      role="table"
      aria-label="Signals table"
    >
      {/* Confidence histogram strip */}
      <ConfidenceHistogram signals={allSignals} />

      {/* Header */}
      <div
        role="rowgroup"
        className="border-b border-border bg-surface/50"
      >
        <div
          role="row"
          className="flex items-center gap-4 px-4 py-2.5"
        >
          {/* unread spacer */}
          <div className="w-1 shrink-0" aria-hidden="true" />
          <div className="w-2 shrink-0" aria-hidden="true" />
          {/* avatar spacer */}
          <div className="w-8 shrink-0" aria-hidden="true" />

          {COLUMNS.map((col) => {
            const isSortable = !!col.sortField
            const isActive = col.sortField === sortField
            return (
              <div
                key={col.key}
                role="columnheader"
                className={cn(
                  'text-[11px] font-medium text-subtle',
                  col.className,
                  isSortable &&
                    'flex cursor-pointer select-none items-center hover:text-body',
                  isActive && 'text-indigo-400',
                )}
                onClick={isSortable ? () => onSort(col.sortField!) : undefined}
              >
                {col.label}
                {isSortable && col.sortField && (
                  <SortIcon
                    field={col.sortField}
                    active={isActive}
                    direction={sortDirection}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Rows */}
      <div role="rowgroup">
        {rows.length === 0 ? (
          <EmptyState />
        ) : (
          rows.map((signal) => (
            <SignalTableRow
              key={signal.id}
              signal={signal}
              isSelected={selectedRowId === signal.id}
              onClick={() => onRowClick(signal)}
              onSave={() => onSave(signal)}
              onDismiss={() => onDismiss(signal)}
            />
          ))
        )}
      </div>

      {/* Footer */}
      {rows.length > 0 && (
        <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
          <span className="text-[11px] text-subtle">
            {rows.length} signal{rows.length !== 1 ? 's' : ''}
          </span>
          <span className="text-[11px] text-subtle">
            Sorted by{' '}
            <span className="font-medium text-body">
              {sortField === 'publishedAt'
                ? 'time'
                : sortField === 'confidence'
                  ? 'confidence'
                  : sortField}
            </span>{' '}
            ({sortDirection === 'desc' ? 'newest first' : 'oldest first'})
          </span>
        </div>
      )}
    </div>
  )
})
