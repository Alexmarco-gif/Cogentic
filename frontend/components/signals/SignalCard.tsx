'use client'

import { Bookmark, Share2, X, Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TrendLine } from '@/components/ui'
import type { Signal } from '@/lib/hooks/useSignals'
import { getDomainPillLight, getDomainTrend } from '@/lib/domain-colors'

interface SignalCardProps {
  signal: Signal
  onClick: () => void
  onSave: () => void
  onDismiss: () => void
}

const SEVERITY_BAR: Record<string, string> = {
  critical: 'bg-red-500',
  high:     'bg-orange-400',
  medium:   'bg-amber-400',
  low:      'bg-slate-300',
}

function confidenceColor(score: number) {
  if (score >= 90) return 'text-emerald-600'
  if (score >= 75) return 'text-amber-600'
  return 'text-red-500'
}

export function SignalCard({ signal, onClick, onSave, onDismiss }: SignalCardProps) {
  const domainClass = getDomainPillLight(signal.domain)
  const severityBar = SEVERITY_BAR[signal.severity]
  const sparkColor = getDomainTrend(signal.domain)

  return (
    <article
      className={cn(
        'relative group bg-surface border border-border rounded-card shadow-card',
        'flex gap-0 overflow-hidden cursor-pointer',
        'transition-all duration-150 hover:shadow-md hover:border-border/80',
        signal.isUnread && 'border-l-[3px] border-l-primary',
      )}
      onClick={onClick}
    >
      {/* Severity bar — narrow left strip */}
      <div className={cn('w-1 shrink-0 rounded-l-card', severityBar, signal.isUnread ? 'opacity-0' : '')} />

      <div className="flex-1 px-4 py-3.5">
        {/* ── Top row ────────────────────────────────────── */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 min-w-0">
            {/* Entity avatar */}
            <div
              className="shrink-0 w-7 h-7 rounded-full bg-muted border border-border
                         flex items-center justify-center text-[10px] font-medium text-subtle"
            >
              {signal.entityInitial}
            </div>

            {/* Entity + domain */}
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[13px] font-medium text-heading truncate max-w-[160px]">
                  {signal.entityName}
                </span>
                <span
                  className={cn(
                    'shrink-0 text-[10px] font-medium px-1.5 py-0.5 rounded-pill border',
                    domainClass,
                  )}
                >
                  {signal.domain}
                </span>
              </div>
            </div>
          </div>

          {/* Time + confidence */}
          <div className="shrink-0 flex items-center gap-2 mt-0.5">
            <span className="text-[11px] text-subtle">{signal.relativeTime}</span>
            <span className={cn('text-[11px] font-medium tabular-nums', confidenceColor(signal.confidence))}>
              {signal.confidence}%
            </span>
            {/* Save button — always visible if saved, otherwise on hover */}
            <button
              onClick={e => { e.stopPropagation(); onSave() }}
              className={cn(
                'p-0.5 rounded transition-colors',
                signal.isSaved
                  ? 'text-primary'
                  : 'text-muted-foreground opacity-0 group-hover:opacity-100',
              )}
              title={signal.isSaved ? 'Saved' : 'Save'}
            >
              <Bookmark size={13} fill={signal.isSaved ? 'currentColor' : 'none'} />
            </button>
          </div>
        </div>

        {/* ── Headline ───────────────────────────────────── */}
        <h2 className="text-[14px] font-medium text-heading leading-snug mb-1.5">
          {signal.headline}
        </h2>

        {/* ── Summary ────────────────────────────────────── */}
        <p className="text-[13px] text-body leading-relaxed line-clamp-2 mb-3">
          {signal.summary}
        </p>

        {/* ── Sparkline + actions row ────────────────────── */}
        <div className="flex items-end justify-between">
          {/* Sparkline */}
          <TrendLine
            data={signal.sparklineData}
            color={sparkColor}
            width={80}
            height={28}
          />

          {/* Hover actions */}
          <div
            className={cn(
              'flex items-center gap-1 opacity-100 translate-y-0 transition-all duration-150',
              'sm:pointer-events-none sm:opacity-0 sm:translate-y-1 sm:group-hover:pointer-events-auto sm:group-hover:opacity-100 sm:group-hover:translate-y-0',
            )}
          >
            <button
              onClick={e => { e.stopPropagation(); onClick() }}
              className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium
                         bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
            >
              <Sparkles size={10} />
              Open Brief
            </button>
            <button
              onClick={e => {
                e.stopPropagation()
                const text = `${signal.headline} — ${signal.entityName}`
                const url  = `${window.location.origin}/dashboard/signals?open=${signal.id}`
                if (navigator.share) {
                  navigator.share({ title: text, url }).catch(() => {})
                } else {
                  navigator.clipboard.writeText(`${text}\n${url}`).catch(() => {})
                }
              }}
              className="p-1.5 rounded-md text-subtle hover:text-body hover:bg-muted transition-colors"
              title="Share"
            >
              <Share2 size={12} />
            </button>
            <button
              onClick={e => { e.stopPropagation(); onDismiss() }}
              className="p-1.5 rounded-md text-subtle hover:text-body hover:bg-muted transition-colors"
              title="Dismiss"
            >
              <X size={12} />
            </button>
          </div>
        </div>

        {/* Unread dot */}
        {signal.isUnread && (
          <span className="absolute top-3.5 right-3 w-1.5 h-1.5 rounded-full bg-primary" />
        )}
      </div>
    </article>
  )
}
