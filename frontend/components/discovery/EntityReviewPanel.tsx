'use client'

import { CheckCircle2, XCircle, Bot, User, Loader2, AlertTriangle, Lock } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Card, CardHeader, CardBody } from '@/components/ui/Card'
import type { EntityDiscoveryItem } from '@/lib/api/types'

// ── Helpers ────────────────────────────────────────────────────────────────────

function sourceIcon(source: string) {
  switch (source) {
    case 'auto_extracted': return <Bot size={13} className="text-primary" />
    case 'agent':          return <Bot size={13} className="text-indigo-500" />
    case 'manual':         return <User size={13} className="text-emerald-600" />
    default:               return null
  }
}

function sourceLabel(source: string) {
  switch (source) {
    case 'auto_extracted': return 'NER'
    case 'agent':          return 'Agent'
    case 'manual':         return 'Manual'
    default:               return source
  }
}

// ── Entity Row ─────────────────────────────────────────────────────────────────

interface EntityRowProps {
  entity: EntityDiscoveryItem
  onApprove: (id: string) => void | Promise<void>
  onReject: (id: string) => void | Promise<void>
  actioning?: boolean
  actionsEnabled?: boolean
}

function EntityRow({ entity, onApprove, onReject, actioning, actionsEnabled = true }: EntityRowProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-0 hover:bg-hover/30 transition-colors">
      {/* Name + type */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-heading truncate">{entity.name}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <Badge variant="outline" className="text-[10px]">{entity.entity_type}</Badge>
          <span className="flex items-center gap-1 text-[10px] text-subtle">
            {sourceIcon(entity.discovery_source)}
            {sourceLabel(entity.discovery_source)}
          </span>
        </div>
      </div>

      {/* Date */}
      <span className="text-[11px] text-subtle shrink-0">
        {new Date(entity.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
      </span>

      {/* Actions */}
      <div className="flex gap-1.5 shrink-0">
        <Button
          size="sm"
          variant="primary"
          className="h-7 px-2.5 text-xs"
          loading={actioning}
          disabled={!actionsEnabled || actioning}
          onClick={() => onApprove(entity.id)}
        >
          <CheckCircle2 size={12} /> Approve
        </Button>
        <Button
          size="sm"
          variant="ghost"
          className="h-7 px-2.5 text-xs text-red-500 hover:text-red-600"
          disabled={!actionsEnabled || actioning}
          onClick={() => onReject(entity.id)}
        >
          <XCircle size={12} /> Reject
        </Button>
      </div>
    </div>
  )
}

// ── Panel ──────────────────────────────────────────────────────────────────────

interface EntityReviewPanelProps {
  entities: EntityDiscoveryItem[]
  loading?: boolean
  loadingMore?: boolean
  hasMore?: boolean
  error?: string | null
  actionsEnabled?: boolean
  actioningId?: string | null
  onRetry?: () => void | Promise<void>
  onLoadMore?: () => void | Promise<void>
  onApprove: (id: string) => void | Promise<void>
  onReject: (id: string) => void | Promise<void>
}

export function EntityReviewPanel({
  entities,
  loading,
  loadingMore,
  hasMore,
  error,
  actionsEnabled = true,
  actioningId,
  onRetry,
  onLoadMore,
  onApprove,
  onReject,
}: EntityReviewPanelProps) {
  if (loading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-10">
          <Loader2 size={20} className="animate-spin text-subtle" />
        </div>
      </Card>
    )
  }

  if (!actionsEnabled) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <Lock size={28} className="mb-2 text-amber-500" />
          <p className="text-sm font-medium text-heading">Admin review required</p>
          <p className="mt-1 text-sm text-subtle">
            Pending entity review is only available to admin or owner accounts.
          </p>
        </div>
      </Card>
    )
  }

  if (error && entities.length === 0) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <AlertTriangle size={28} className="mb-2 text-rose-400" />
          <p className="text-sm font-medium text-heading">Pending review could not load.</p>
          <p className="mt-1 text-sm text-subtle">{error}</p>
          {onRetry && (
            <Button size="sm" variant="outline" className="mt-4" onClick={onRetry}>
              Retry
            </Button>
          )}
        </div>
      </Card>
    )
  }

  if (entities.length === 0) {
    return (
      <Card>
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <CheckCircle2 size={28} className="text-emerald-500 mb-2" />
          <p className="text-sm text-subtle">All entities reviewed — nothing pending.</p>
        </div>
      </Card>
    )
  }

  return (
    <Card noPadding>
      <CardHeader className="px-4 pt-4 pb-2">
        <h3 className="text-sm font-medium text-heading">Pending Entity Review</h3>
        <Badge variant="warning">{entities.length} pending</Badge>
      </CardHeader>
      <CardBody className="mt-0">
        {entities.map(e => (
          <EntityRow
            key={e.id}
            entity={e}
            onApprove={onApprove}
            onReject={onReject}
            actioning={actioningId === e.id}
            actionsEnabled={actionsEnabled}
          />
        ))}
        {hasMore && onLoadMore && (
          <div className="border-t border-border px-4 py-3">
            <Button size="sm" variant="outline" onClick={onLoadMore} loading={loadingMore}>
              Load more entities
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  )
}
