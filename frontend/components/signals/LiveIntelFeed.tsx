'use client'

import { useState, useMemo } from 'react'
import { cn } from '@/lib/utils'
import {
  ArrowRight,
  ShieldAlert,
  Lightbulb,
  AlertTriangle,
  Search,
  FileText,
} from 'lucide-react'
import { LiveIndicator } from '@/components/ui'
import type { FeedEvent, FeedCategory, Signal } from '@/lib/hooks/useSignals'

// ── Category config ──────────────────────────────────────────────────────────
const CATEGORY_CONFIG: Record<FeedCategory, {
  icon: React.ReactNode
  label: string
  pillBg: string
  pillText: string
}> = {
  risk: {
    icon: <ShieldAlert size={12} />,
    label: 'Risk',
    pillBg: 'bg-red-50',
    pillText: 'text-red-700',
  },
  opportunity: {
    icon: <Lightbulb size={12} />,
    label: 'Opportunity',
    pillBg: 'bg-emerald-50',
    pillText: 'text-emerald-700',
  },
  alert: {
    icon: <AlertTriangle size={12} />,
    label: 'Alert',
    pillBg: 'bg-amber-50',
    pillText: 'text-amber-700',
  },
  investigation: {
    icon: <Search size={12} />,
    label: 'Investigation',
    pillBg: 'bg-blue-50',
    pillText: 'text-blue-700',
  },
  brief: {
    icon: <FileText size={12} />,
    label: 'Brief',
    pillBg: 'bg-violet-50',
    pillText: 'text-violet-700',
  },
}

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-red-500',
  high:     'bg-orange-400',
  medium:   'bg-amber-400',
  low:      'bg-slate-300',
}

import { getDomainPillLight } from '@/lib/domain-colors'

type FeedFilter = 'all' | 'critical' | 'opportunities' | 'risks'

interface LiveIntelFeedProps {
  events: FeedEvent[]
  signals?: Signal[]
  loading?: boolean
  onEventClick?: (signal: Signal) => void
  onOpenSignal?: (signalId: string) => void
  lastUpdated?: Date
  liveConnected?: boolean
  onViewTimeline?: () => void
}

function timeAgo(date: Date): string {
  const secs = Math.floor((Date.now() - date.getTime()) / 1000)
  if (secs < 10) return 'just now'
  if (secs < 60) return `${secs}s ago`
  const mins = Math.floor(secs / 60)
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
}

export function LiveIntelFeed({
  events,
  signals = [],
  loading,
  onEventClick,
  onOpenSignal,
  lastUpdated,
  liveConnected = false,
  onViewTimeline,
}: LiveIntelFeedProps) {
  const [filter, setFilter] = useState<FeedFilter>('all')

  const filteredEvents = useMemo(() => {
    switch (filter) {
      case 'critical':
        return events.filter(e => e.severity === 'critical' || e.severity === 'high')
      case 'opportunities':
        return events.filter(e => e.category === 'opportunity')
      case 'risks':
        return events.filter(e => e.category === 'risk' || e.category === 'alert')
      default:
        return events
    }
  }, [events, filter])

  const handleEventClick = (event: FeedEvent) => {
    if (event.signalId && onOpenSignal) {
      onOpenSignal(event.signalId)
      return
    }

    if (event.signalId && onEventClick) {
      const signal = signals.find(s => s.id === event.signalId)
      if (signal) onEventClick(signal)
    }
  }

  const filters: { key: FeedFilter; label: string; count?: number }[] = [
    { key: 'all', label: 'All', count: events.length },
    { key: 'critical', label: 'Critical', count: events.filter(e => e.severity === 'critical' || e.severity === 'high').length },
    { key: 'risks', label: 'Risks', count: events.filter(e => e.category === 'risk' || e.category === 'alert').length },
    { key: 'opportunities', label: 'Opportunities', count: events.filter(e => e.category === 'opportunity').length },
  ]

  if (loading) {
    return (
      <div className="bg-surface border border-border rounded-card shadow-card p-5">
        <div className="h-4 bg-muted rounded w-1/3 mb-4 animate-pulse" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-muted rounded mb-2 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="bg-surface border border-border rounded-card shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div>
              <h2 className="text-[14px] font-medium text-heading">Real-Time Intelligence Feed</h2>
              <p className="text-[11px] text-subtle mt-0.5">
                Live signals, risks, and opportunities as they are detected
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-[11px] text-subtle tabular-nums">
                Updated {timeAgo(lastUpdated)}
              </span>
            )}
            <LiveIndicator label={liveConnected ? 'Live' : 'Auto-refresh'} />
          </div>
        </div>
        {/* Filter tabs */}
        <div className="flex items-center gap-1">
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-colors',
                filter === f.key
                  ? 'bg-primary/10 text-primary'
                  : 'text-subtle hover:bg-muted hover:text-body',
              )}
            >
              {f.label}
              {f.count !== undefined && (
                <span className={cn(
                  'ml-1 tabular-nums',
                  filter === f.key ? 'text-primary/70' : 'text-subtle',
                )}>
                  {f.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Event list */}
      <div className="divide-y divide-border/50">
        {filteredEvents.length === 0 && (
          <div className="px-5 py-10 text-center">
            <p className="text-sm font-medium text-heading">No live events yet</p>
            <p className="mt-1 text-xs text-subtle">
              New signals for this industry will appear here as they are ingested.
            </p>
          </div>
        )}
        {filteredEvents.map((event, idx) => {
          const catConfig = CATEGORY_CONFIG[event.category]
          const isClickable = !!event.signalId

          return (
            <div
              key={event.id}
              onClick={() => handleEventClick(event)}
              className={cn(
                'group px-5 py-4 transition-all',
                isClickable && 'cursor-pointer hover:bg-muted/40',
                // Animate in effect — stagger by index
                'animate-in fade-in slide-in-from-bottom-1',
              )}
              style={{ animationDelay: `${idx * 50}ms`, animationFillMode: 'both' }}
            >
              <div className="flex items-start gap-3">
                {/* Timestamp column */}
                <div className="w-[52px] shrink-0 pt-0.5">
                  <p className="text-[11px] text-subtle tabular-nums">{event.relativeTime}</p>
                </div>

                {/* Severity dot */}
                <div className="pt-1.5 shrink-0">
                  <span className={cn(
                    'relative flex h-2 w-2',
                  )}>
                    {event.severity === 'critical' && (
                      <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', SEVERITY_DOT[event.severity])} />
                    )}
                    <span className={cn('relative inline-flex rounded-full h-2 w-2', SEVERITY_DOT[event.severity])} />
                  </span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    {/* Category pill */}
                    <span className={cn(
                      'inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full',
                      catConfig.pillBg, catConfig.pillText,
                    )}>
                      {catConfig.icon}
                      {catConfig.label}
                    </span>

                    {/* Domain pill */}
                    <span className={cn(
                      'text-[10px] font-medium px-2 py-0.5 rounded-full',
                      getDomainPillLight(event.domain),
                    )}>
                      {event.domain}
                    </span>
                  </div>

                  {/* Headline */}
                  <p className="text-[13px] font-medium text-heading leading-snug mb-1">
                    {event.headline}
                  </p>

                  {/* Explanation — intelligence, not just a headline */}
                  <p className="text-[12px] text-subtle leading-relaxed">
                    {event.explanation}
                  </p>
                </div>

                {/* Action arrow */}
                {isClickable && (
                  <div className="pt-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ArrowRight size={14} className="text-primary" />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-border bg-muted/20 flex items-center justify-between">
        <p className="text-[11px] text-subtle">
          Showing {filteredEvents.length} of {events.length} events
        </p>
        <button
          type="button"
          onClick={onViewTimeline}
          disabled={!onViewTimeline}
          className="text-[11px] font-medium text-primary flex items-center gap-1 hover:underline"
        >
          View full timeline
          <ArrowRight size={11} />
        </button>
      </div>
    </div>
  )
}
