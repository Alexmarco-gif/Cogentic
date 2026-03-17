'use client'

import { useState } from 'react'
import { SignalCard } from './SignalCard'
import { SignalCardSkeleton } from '@/components/ui'
import { cn } from '@/lib/utils'
import type { Signal } from '@/lib/hooks/useSignals'

type Filter = 'all' | 'critical' | 'saved'

interface SignalFeedProps {
  signals: Signal[]
  loading: boolean
  onCardClick: (signal: Signal) => void
  onSave: (id: string) => void
  onDismiss: (id: string) => void
}

export function SignalFeed({ signals, loading, onCardClick, onSave, onDismiss }: SignalFeedProps) {
  const [filter, setFilter] = useState<Filter>('all')

  const visibleSignals = signals.filter(s => {
    if (filter === 'critical') return s.severity === 'critical'
    if (filter === 'saved') return s.isSaved
    return true
  })

  return (
    <div className="flex-1 min-w-0">
      {/* ── Toolbar ────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-1 bg-muted rounded-lg p-0.5">
          {(['all', 'critical', 'saved'] as Filter[]).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                'px-3 py-1.5 rounded-md text-[12px] font-medium capitalize transition-colors',
                filter === f
                  ? 'bg-surface shadow-sm text-heading'
                  : 'text-subtle hover:text-body',
              )}
            >
              {f === 'critical' ? '🔴 Critical' : f === 'saved' ? '🔖 Saved' : 'All signals'}
            </button>
          ))}
        </div>

        <span className="text-xs text-subtle">
          {loading ? '…' : `${visibleSignals.length} signal${visibleSignals.length !== 1 ? 's' : ''}`}
        </span>
      </div>

      {/* ── Feed list ──────────────────────────────────── */}
      <div className="flex flex-col gap-2">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <SignalCardSkeleton key={i} />)
        ) : visibleSignals.length === 0 ? (
          <div className="py-16 text-center text-subtle text-sm">
            No signals in this view.
          </div>
        ) : (
          visibleSignals.map(signal => (
            <SignalCard
              key={signal.id}
              signal={signal}
              onClick={() => onCardClick(signal)}
              onSave={() => onSave(signal.id)}
              onDismiss={() => onDismiss(signal.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}
