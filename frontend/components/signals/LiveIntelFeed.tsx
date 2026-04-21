'use client'

import { useMemo, useState } from 'react'
import { cn } from '@/lib/utils'
import {
  AlertTriangle,
  ArrowRight,
  FileText,
  Lightbulb,
  Search,
  ShieldAlert,
} from 'lucide-react'
import { LiveIndicator } from '@/components/ui'
import type { FeedEvent, FeedCategory, Signal } from '@/lib/hooks/useSignals'
import { getDomainPillLight } from '@/lib/domain-colors'

const CATEGORY_CONFIG: Record<FeedCategory, {
  icon: React.ReactNode
  label: string
  pillBg: string
  pillText: string
}> = {
  risk: {
    icon: <ShieldAlert size={12} />,
    label: 'Risk',
    pillBg: 'bg-critical/10',
    pillText: 'text-critical',
  },
  opportunity: {
    icon: <Lightbulb size={12} />,
    label: 'Opportunity',
    pillBg: 'bg-success/10',
    pillText: 'text-success',
  },
  alert: {
    icon: <AlertTriangle size={12} />,
    label: 'Alert',
    pillBg: 'bg-warning/10',
    pillText: 'text-warning',
  },
  investigation: {
    icon: <Search size={12} />,
    label: 'Investigate',
    pillBg: 'bg-primary/10',
    pillText: 'text-primary',
  },
  brief: {
    icon: <FileText size={12} />,
    label: 'Brief',
    pillBg: 'bg-surface-2',
    pillText: 'text-heading',
  },
}

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-critical',
  high: 'bg-warning',
  medium: 'bg-primary',
  low: 'bg-neutral',
}

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
  emptyTitle?: string
  emptyDescription?: string
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
  emptyTitle = 'No live events yet',
  emptyDescription = 'New signals will appear here as soon as your selected industry or starter workspace receives fresh intelligence.',
}: LiveIntelFeedProps) {
  const [filter, setFilter] = useState<FeedFilter>('all')

  const filteredEvents = useMemo(() => {
    switch (filter) {
      case 'critical':
        return events.filter((event) => event.severity === 'critical' || event.severity === 'high')
      case 'opportunities':
        return events.filter((event) => event.category === 'opportunity')
      case 'risks':
        return events.filter((event) => event.category === 'risk' || event.category === 'alert')
      default:
        return events
    }
  }, [events, filter])

  const filters: { key: FeedFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: events.length },
    { key: 'critical', label: 'Critical', count: events.filter((event) => event.severity === 'critical' || event.severity === 'high').length },
    { key: 'risks', label: 'Risks', count: events.filter((event) => event.category === 'risk' || event.category === 'alert').length },
    { key: 'opportunities', label: 'Opportunities', count: events.filter((event) => event.category === 'opportunity').length },
  ]

  function handleEventClick(event: FeedEvent) {
    if (event.signalId && onOpenSignal) {
      onOpenSignal(event.signalId)
      return
    }

    if (event.signalId && onEventClick) {
      const signal = signals.find((item) => item.id === event.signalId)
      if (signal) onEventClick(signal)
    }
  }

  if (loading) {
    return (
      <div className="surface-panel p-5">
        <div className="skeleton mb-4 h-5 w-40" />
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="skeleton h-24 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="surface-panel overflow-hidden">
      <div className="border-b border-border px-5 py-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="eyebrow">Activity timeline</p>
            <h2 className="mt-2 text-title">What changed most recently</h2>
            <p className="mt-2 max-w-2xl text-[0.82rem] text-subtle">
              Instant feedback matters. This feed keeps the latest risks, opportunities, and briefs visible in one place.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {lastUpdated && (
              <span className="rounded-full border border-border bg-surface px-3 py-1.5 text-[0.74rem] font-semibold text-subtle">
                Updated {timeAgo(lastUpdated)}
              </span>
            )}
            <LiveIndicator label={liveConnected ? 'Live feed' : 'Auto refresh'} />
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {filters.map((item) => (
            <button
              key={item.key}
              onClick={() => setFilter(item.key)}
              className={cn(
                'button-press rounded-full px-3 py-1.5 text-[0.76rem] font-semibold transition-all duration-200',
                filter === item.key
                  ? 'bg-primary text-white shadow-glow'
                  : 'border border-border bg-surface text-body hover:bg-surface-2',
              )}
            >
              {item.label} <span className="opacity-75">{item.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="divide-y divide-border/80">
        {filteredEvents.length === 0 && (
          <div className="px-6 py-14 text-center">
            <p className="text-[0.92rem] font-semibold text-heading">{emptyTitle}</p>
            <p className="mx-auto mt-2 max-w-md text-[0.8rem] text-subtle">
              {emptyDescription}
            </p>
          </div>
        )}

        {filteredEvents.map((event, index) => {
          const category = CATEGORY_CONFIG[event.category]
          const clickable = Boolean(event.signalId)

          return (
            <div
              key={event.id}
              onClick={() => handleEventClick(event)}
              className={cn(
                'group px-5 py-4 transition-all duration-200',
                clickable && 'cursor-pointer hover:bg-surface-2/70',
                'animate-in fade-in slide-in-from-bottom-1',
              )}
              style={{ animationDelay: `${index * 50}ms`, animationFillMode: 'both' }}
            >
              <div className="flex items-start gap-4">
                <div className="w-16 shrink-0 pt-1 text-[0.74rem] font-semibold text-subtle">
                  {event.relativeTime}
                </div>

                <div className="pt-2">
                  <span className="relative flex h-2.5 w-2.5">
                    {event.severity === 'critical' && (
                      <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', SEVERITY_DOT[event.severity])} />
                    )}
                    <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', SEVERITY_DOT[event.severity])} />
                  </span>
                </div>

                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className={cn(
                      'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.14em]',
                      category.pillBg,
                      category.pillText,
                    )}>
                      {category.icon}
                      {category.label}
                    </span>

                    <span className={cn(
                      'rounded-full px-2.5 py-1 text-[0.68rem] font-semibold',
                      getDomainPillLight(event.domain),
                    )}>
                      {event.domain}
                    </span>
                  </div>

                  <p className="text-[0.92rem] font-semibold text-heading">{event.headline}</p>
                  <p className="mt-1 max-w-3xl text-[0.82rem] text-subtle">{event.explanation}</p>
                </div>

                {clickable && (
                  <div className="pt-1 opacity-0 transition-all duration-200 group-hover:translate-x-0.5 group-hover:opacity-100">
                    <ArrowRight size={15} className="text-primary" />
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex items-center justify-between border-t border-border bg-surface-2/60 px-5 py-3">
        <p className="text-[0.76rem] text-subtle">
          Showing {filteredEvents.length} of {events.length} events
        </p>
        <button
          type="button"
          onClick={onViewTimeline}
          disabled={!onViewTimeline}
          className="button-press inline-flex items-center gap-2 text-[0.8rem] font-semibold text-primary transition-colors hover:text-primary-hover disabled:opacity-40"
        >
          Open full timeline
          <ArrowRight size={13} />
        </button>
      </div>
    </div>
  )
}
