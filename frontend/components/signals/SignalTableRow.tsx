'use client'

import { memo } from 'react'
import { Bookmark, Eye, X, ChevronRight } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TrendLine } from '@/components/ui/TrendLine'
import { type Signal, type SignalSeverity } from '@/lib/hooks/useSignals'
import { getDomainPill, getDomainAvatar, getDomainTrend } from '@/lib/domain-colors'

const SEVERITY_BAR: Record<SignalSeverity, string> = {
  critical: 'bg-red-500',
  high: 'bg-orange-400',
  medium: 'bg-amber-400',
  low: 'bg-slate-500',
}

const SEVERITY_LABEL: Record<SignalSeverity, string> = {
  critical: 'Critical',
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

const SEVERITY_TEXT: Record<SignalSeverity, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-amber-400',
  low: 'text-slate-400',
}

const CONFIDENCE_COLOR = (c: number) =>
  c >= 90 ? 'text-emerald-400' : c >= 75 ? 'text-amber-400' : 'text-slate-400'

// ── Types ─────────────────────────────────────────────────────────────────────

interface SignalTableRowProps {
  signal: Signal
  isSelected: boolean
  onClick: () => void
  onSave?: () => void
  onDismiss?: () => void
}

// ── Component ─────────────────────────────────────────────────────────────────

export const SignalTableRow = memo(function SignalTableRow({
  signal,
  isSelected,
  onClick,
  onSave,
  onDismiss,
}: SignalTableRowProps) {
  const {
    entityName,
    entityInitial,
    domain,
    severity,
    confidence,
    headline,
    summary,
    sparklineData,
    relativeTime,
    isUnread,
    isSaved,
  } = signal

  const avatarColors = getDomainAvatar(domain)
  const domainBadge = getDomainPill(domain)
  const sparkColor = getDomainTrend(domain)

  return (
    <div
      role="row"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      className={cn(
        'group relative flex cursor-pointer items-stretch gap-0',
        'border-b border-border transition-colors duration-150',
        'outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-indigo-500/50',
        isSelected
          ? 'bg-indigo-500/6'
          : 'hover:bg-white/[0.025]',
        isUnread && !isSelected && 'bg-amber-500/[0.025]',
      )}
    >
      {/* Severity bar */}
      <div
        className={cn(
          'w-1 shrink-0 rounded-l-sm transition-all duration-200',
          SEVERITY_BAR[severity],
          isSelected ? 'opacity-100' : 'opacity-60 group-hover:opacity-100',
        )}
        aria-hidden="true"
      />

      {/* Content */}
      <div className="flex min-w-0 flex-1 items-center gap-4 px-4 py-3.5">

        {/* Unread dot */}
        <div className="flex w-2 shrink-0 items-center justify-center">
          {isUnread && (
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          )}
        </div>

        {/* Entity avatar */}
        <div
          className={cn(
            'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
            'text-sm font-semibold ring-1',
            avatarColors,
          )}
          aria-hidden="true"
        >
          {entityInitial}
        </div>

        {/* Entity + domain */}
        <div className="w-44 shrink-0">
          <div className="truncate text-sm font-medium text-heading">
            {entityName}
          </div>
          <span
            className={cn(
              'mt-0.5 inline-block max-w-full truncate rounded px-1.5 py-0.5 text-[10px] font-medium',
              domainBadge,
            )}
          >
            {domain}
          </span>
        </div>

        {/* Headline + summary */}
        <div className="min-w-0 flex-1">
          <p className="line-clamp-1 text-sm font-medium text-heading">
            {headline}
          </p>
          <p className="line-clamp-1 mt-0.5 text-xs text-subtle">
            {summary}
          </p>
        </div>

        {/* Sparkline */}
        <div className="hidden shrink-0 sm:block">
          <TrendLine
            data={sparklineData}
            color={sparkColor}
            width={72}
            height={28}
          />
        </div>

        {/* Confidence */}
        <div className="hidden w-14 shrink-0 text-right lg:block">
          <span
            className={cn(
              'font-display text-sm font-bold tabular-nums',
              CONFIDENCE_COLOR(confidence),
            )}
          >
            {confidence}%
          </span>
          <div className="text-[10px] text-subtle">confidence</div>
        </div>

        {/* Severity badge */}
        <div className="hidden w-16 shrink-0 text-center md:block">
          <span
            className={cn(
              'text-xs font-semibold uppercase tracking-wide',
              SEVERITY_TEXT[severity],
            )}
          >
            {SEVERITY_LABEL[severity]}
          </span>
        </div>

        {/* Time */}
        <div className="hidden w-16 shrink-0 text-right text-[11px] text-subtle lg:block">
          {relativeTime}
        </div>

        {/* Actions — hover only */}
        <div
          className={cn(
            'flex shrink-0 items-center gap-1 opacity-100 transition-opacity duration-150 md:opacity-0 md:group-hover:opacity-100',
            isSelected && 'opacity-100',
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Save */}
          <button
            onClick={onSave}
            className={cn(
              'flex h-7 w-7 items-center justify-center rounded-md transition-colors',
              isSaved
                ? 'text-amber-400 hover:bg-amber-500/15'
                : 'text-subtle hover:bg-white/8 hover:text-body',
            )}
            aria-label={isSaved ? 'Unsave signal' : 'Save signal'}
          >
            <Bookmark
              className="h-3.5 w-3.5"
              fill={isSaved ? 'currentColor' : 'none'}
            />
          </button>

          {/* Dismiss */}
          <button
            onClick={onDismiss}
            className="flex h-7 w-7 items-center justify-center rounded-md text-subtle transition-colors hover:bg-white/8 hover:text-body"
            aria-label="Dismiss signal"
          >
            <X className="h-3.5 w-3.5" />
          </button>

          {/* View brief */}
          <button
            onClick={onClick}
            className="flex h-7 w-7 items-center justify-center rounded-md text-subtle transition-colors hover:bg-indigo-500/15 hover:text-indigo-400"
            aria-label="View intelligence brief"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
})
