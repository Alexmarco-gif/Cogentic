'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { AlertTriangle, ExternalLink, Lock, Zap, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import type { DiscoveredSourceResponse } from '@/lib/api/types'

// ── Helpers ────────────────────────────────────────────────────────────────────

function statusVariant(status: string) {
  switch (status) {
    case 'recommended': return 'warning'
    case 'activated':   return 'success'
    case 'dismissed':   return 'neutral'
    default:            return 'default'
  }
}

function formatDate(iso: string) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

// ── Source Row ──────────────────────────────────────────────────────────────────

interface SourceRowProps {
  source: DiscoveredSourceResponse
  onActivate: (id: string) => void | Promise<void>
  onDismiss: (id: string) => void | Promise<void>
  activating?: boolean
  actionsEnabled?: boolean
  actionsDisabledReason?: string
}

function SourceRow({
  source,
  onActivate,
  onDismiss,
  activating,
  actionsEnabled = true,
  actionsDisabledReason,
}: SourceRowProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border-b border-border last:border-0">
      <div
        className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-hover/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {/* Domain + URL */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-heading truncate">{source.domain}</p>
          <p className="text-[11px] text-subtle truncate">{source.url}</p>
        </div>

        {/* Type badge */}
        <Badge variant="outline" className="shrink-0 text-[10px]">
          {source.source_type}
        </Badge>

        {/* Mentions */}
        <div className="text-right shrink-0 w-16">
          <p className="text-sm font-medium text-heading tabular-nums">{source.mention_count}</p>
          <p className="text-[10px] text-subtle">mentions</p>
        </div>

        {/* Relevance */}
        <div className="shrink-0 w-20">
          <div className="flex items-center gap-1.5">
            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  source.relevance_score >= 0.8
                    ? 'bg-emerald-500'
                    : source.relevance_score >= 0.5
                      ? 'bg-amber-500'
                      : 'bg-neutral-400',
                )}
                style={{ width: `${Math.round(source.relevance_score * 100)}%` }}
              />
            </div>
            <span className="text-[10px] text-subtle tabular-nums">
              {(source.relevance_score * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Status */}
        <Badge variant={statusVariant(source.status)} className="shrink-0">
          {source.status}
        </Badge>

        {/* Expand */}
        {expanded ? <ChevronUp size={14} className="text-subtle" /> : <ChevronDown size={14} className="text-subtle" />}
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="flex flex-col gap-3 px-4 pb-3 text-xs text-subtle lg:flex-row lg:items-center">
          <span>First seen: {formatDate(source.created_at)}</span>
          <span className="text-border">|</span>
          <span>Last seen: {formatDate(source.last_seen_at)}</span>
          {source.signal_type && (
            <>
              <span className="text-border">|</span>
              <span>Signal type: {source.signal_type}</span>
            </>
          )}
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-primary hover:underline ml-auto"
            onClick={e => e.stopPropagation()}
          >
            Open <ExternalLink size={11} />
          </a>

          {source.status === 'recommended' && (
            <div className="ml-auto flex flex-col items-start gap-2 sm:flex-row sm:items-center">
              <Button
                size="sm"
                variant="primary"
                loading={activating}
                disabled={!actionsEnabled || activating}
                onClick={e => { e.stopPropagation(); onActivate(source.id) }}
              >
                <Zap size={12} /> Activate
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={!actionsEnabled || activating}
                onClick={e => { e.stopPropagation(); onDismiss(source.id) }}
              >
                <XCircle size={12} /> Dismiss
              </Button>
              {!actionsEnabled && actionsDisabledReason && (
                <span className="inline-flex items-center gap-1 text-[11px] text-amber-600">
                  <Lock size={11} />
                  {actionsDisabledReason}
                </span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Sources Table ──────────────────────────────────────────────────────────────

interface SourcesTableProps {
  sources: DiscoveredSourceResponse[]
  loading?: boolean
  loadingMore?: boolean
  hasMore?: boolean
  error?: string | null
  actioningId?: string | null
  actionsEnabled?: boolean
  actionsDisabledReason?: string
  onLoadMore?: () => void | Promise<void>
  onRetry?: () => void | Promise<void>
  onActivate: (id: string) => void | Promise<void>
  onDismiss: (id: string) => void | Promise<void>
}

export function SourcesTable({
  sources,
  loading,
  loadingMore,
  hasMore,
  error,
  actioningId,
  actionsEnabled = true,
  actionsDisabledReason,
  onLoadMore,
  onRetry,
  onActivate,
  onDismiss,
}: SourcesTableProps) {
  if (loading) {
    return (
      <Card noPadding>
        <div className="p-4 space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-muted rounded animate-pulse" />
          ))}
        </div>
      </Card>
    )
  }

  if (sources.length === 0) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          {error ? (
            <>
              <AlertTriangle size={32} className="mb-3 text-rose-400" />
              <p className="text-sm font-medium text-heading">Discovery could not load right now.</p>
              <p className="mt-1 text-sm text-subtle">{error}</p>
              {onRetry && (
                <Button size="sm" variant="outline" className="mt-4" onClick={onRetry}>
                  Retry
                </Button>
              )}
            </>
          ) : (
            <>
              <Zap size={32} className="text-subtle mb-3" />
              <p className="text-sm text-subtle">
                No discovered sources yet. As signals are processed, referenced URLs
                will appear here automatically.
              </p>
            </>
          )}
        </div>
      </Card>
    )
  }

  return (
    <Card noPadding>
      <CardHeader className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-heading">Discovered Sources</h3>
        <span className="text-[11px] text-subtle">{sources.length} sources</span>
      </CardHeader>
      <CardBody className="mt-0">
        {sources.map(s => (
          <SourceRow
            key={s.id}
            source={s}
            onActivate={onActivate}
            onDismiss={onDismiss}
            activating={actioningId === s.id}
            actionsEnabled={actionsEnabled}
            actionsDisabledReason={actionsDisabledReason}
          />
        ))}
        {hasMore && onLoadMore && (
          <div className="border-t border-border px-4 py-3">
            <Button size="sm" variant="outline" onClick={onLoadMore} loading={loadingMore}>
              Load more sources
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
