'use client'

import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { AlertTriangle, Lock, Radar, RefreshCw, ShieldCheck } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Dialog } from '@/components/ui/Dialog'
import { DiscoveryStatsBar } from '@/components/discovery/DiscoveryStatsBar'
import { SourcesTable } from '@/components/discovery/SourcesTable'
import { EntityReviewPanel } from '@/components/discovery/EntityReviewPanel'
import { useDiscoveredSources, usePendingEntities } from '@/lib/hooks/useDiscovery'
import { friendlyErrorMessage, getCurrentUser, getIndustries, type IndustryItem } from '@/lib/api'

type StatusTab = 'all' | 'recommended' | 'activated' | 'dismissed'

const TABS: { id: StatusTab; label: string }[] = [
  { id: 'all',         label: 'All Sources' },
  { id: 'recommended', label: 'Recommended' },
  { id: 'activated',   label: 'Activated' },
  { id: 'dismissed',   label: 'Dismissed' },
]

export default function DiscoveryPage() {
  const [tab, setTab] = useState<StatusTab>('all')
  const [currentRole, setCurrentRole] = useState<string | null>(null)
  const [accessLoading, setAccessLoading] = useState(true)
  const [pageMessage, setPageMessage] = useState<string | null>(null)
  const [sourceActionId, setSourceActionId] = useState<string | null>(null)
  const [entityActionId, setEntityActionId] = useState<string | null>(null)

  const statusFilter = tab === 'all' ? undefined : tab
  const {
    sources,
    stats,
    loading,
    loadingMore,
    hasMore,
    error,
    refresh,
    loadMore,
    activate,
    dismiss,
  } =
    useDiscoveredSources(statusFilter as 'recommended' | 'activated' | 'dismissed' | undefined)

  const canManageDiscovery = ['admin', 'owner'].includes(currentRole ?? '')

  const {
    entities,
    loading: entitiesLoading,
    loadingMore: entitiesLoadingMore,
    hasMore: entitiesHasMore,
    error: entitiesError,
    refresh: refreshEntities,
    loadMore: loadMoreEntities,
    approve,
    reject,
  } = usePendingEntities(!accessLoading && canManageDiscovery)

  // Industry picker state
  const [industries, setIndustries] = useState<IndustryItem[]>([])
  const [industriesError, setIndustriesError] = useState(false)
  const [industriesLoading, setIndustriesLoading] = useState(false)
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null)
  const [activating, setActivating] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function loadAccess() {
      setAccessLoading(true)
      try {
        const auth = await getCurrentUser()
        if (!cancelled) {
          setCurrentRole(auth.organization.role)
        }
      } catch {
        if (!cancelled) {
          setCurrentRole(null)
        }
      } finally {
        if (!cancelled) {
          setAccessLoading(false)
        }
      }
    }

    loadAccess()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!canManageDiscovery) {
      setIndustries([])
      setIndustriesError(false)
      setIndustriesLoading(false)
      return
    }

    let cancelled = false
    setIndustriesLoading(true)
    getIndustries()
      .then((data) => {
        if (!cancelled) {
          setIndustries(data)
          setIndustriesError(false)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setIndustries([])
          setIndustriesError(true)
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIndustriesLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [canManageDiscovery])

  const handleActivate = useCallback((sourceId: string) => {
    if (!canManageDiscovery) return
    setPageMessage(null)
    setPendingSourceId(sourceId)
  }, [canManageDiscovery])

  const handleConfirmActivate = useCallback(async (industryId: string) => {
    if (!pendingSourceId) return
    setActivating(true)
    try {
      setPageMessage(null)
      setSourceActionId(pendingSourceId)
      await activate(pendingSourceId, industryId)
    } catch (error) {
      setPageMessage(friendlyErrorMessage(error))
    } finally {
      setActivating(false)
      setSourceActionId(null)
      setPendingSourceId(null)
    }
  }, [pendingSourceId, activate])

  const handleDismiss = useCallback(async (sourceId: string) => {
    if (!canManageDiscovery) return
    setSourceActionId(sourceId)
    setPageMessage(null)
    try {
      await dismiss(sourceId)
    } catch (error) {
      setPageMessage(friendlyErrorMessage(error))
    } finally {
      setSourceActionId(null)
    }
  }, [canManageDiscovery, dismiss])

  const handleApprove = useCallback(async (entityId: string) => {
    setEntityActionId(entityId)
    setPageMessage(null)
    try {
      await approve(entityId)
    } catch (error) {
      setPageMessage(friendlyErrorMessage(error))
    } finally {
      setEntityActionId(null)
    }
  }, [approve])

  const handleReject = useCallback(async (entityId: string) => {
    setEntityActionId(entityId)
    setPageMessage(null)
    try {
      await reject(entityId)
    } catch (error) {
      setPageMessage(friendlyErrorMessage(error))
    } finally {
      setEntityActionId(null)
    }
  }, [reject])

  const handleRefresh = useCallback(async () => {
    setPageMessage(null)
    await Promise.all([
      refresh(),
      canManageDiscovery ? refreshEntities() : Promise.resolve(),
    ])
  }, [canManageDiscovery, refresh, refreshEntities])

  return (
    <div className="mx-auto max-w-[1400px] space-y-6 px-3 py-4 sm:px-4 lg:px-0">

      {/* ── Industry picker modal ──────────────────────── */}
      <Dialog
        open={pendingSourceId !== null}
        onClose={() => setPendingSourceId(null)}
        title="Select Industry"
        description="Choose the industry vertical to associate with this source contract."
        size="sm"
      >
        <div className="flex flex-col gap-2 pt-1">
          {industriesError ? (
            <p className="text-sm text-rose-500 py-4 text-center">Could not load industries. Please close and try again.</p>
          ) : industriesLoading ? (
            <p className="text-sm text-subtle py-4 text-center">Loading industries…</p>
          ) : industries.length === 0 ? (
            <p className="text-sm text-subtle py-4 text-center">
              No industries are available yet. Bootstrap the catalog before activating discovery sources.
            </p>
          ) : (
            industries.map(ind => (
              <button
                key={ind.id}
                disabled={activating}
                onClick={() => handleConfirmActivate(ind.id)}
                className={cn(
                  'w-full text-left px-4 py-3 rounded-lg border border-border text-sm font-medium',
                  'hover:bg-primary/5 hover:border-primary/40 transition-colors',
                  activating && 'opacity-50 cursor-not-allowed',
                )}
              >
                {ind.name}
              </button>
            ))
          )}
        </div>
      </Dialog>

      {/* ── Header ──────────────────────────────────────── */}
      <div className="surface-panel flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Radar size={20} className="text-primary" />
            <h1 className="font-display text-xl font-semibold text-heading">
              Source Discovery
            </h1>
          </div>
          <p className="mt-2 text-sm text-subtle">
            Review recommended sources, activate the right ones, and keep entity intake organized without leaving the page.
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={handleRefresh}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>

      {!accessLoading && !canManageDiscovery && (
        <div className="flex flex-col gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-4 text-sm text-amber-100 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-3">
            <Lock size={18} className="mt-0.5 shrink-0 text-amber-300" />
            <div>
              <p className="font-medium text-amber-50">Discovery review is in read-only mode</p>
              <p className="mt-1 text-amber-100/80">
                You can still browse discovered sources, but only admin or owner accounts can activate sources,
                dismiss recommendations, or review pending entities.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full bg-amber-500/15 px-3 py-1 text-xs font-medium text-amber-200">
            <ShieldCheck size={12} />
            Role: {currentRole ?? 'viewer'}
          </div>
        </div>
      )}

      {(error || entitiesError || pageMessage) && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-2">
              <AlertTriangle size={16} className="mt-0.5 shrink-0 text-rose-300" />
              <span>{pageMessage ?? error ?? entitiesError}</span>
            </div>
            <Button size="sm" variant="outline" onClick={handleRefresh} className="border-rose-400/30 bg-transparent text-rose-100 hover:bg-rose-500/10">
              Retry
            </Button>
          </div>
        </div>
      )}

      {/* ── Stats Bar ───────────────────────────────────── */}
      <DiscoveryStatsBar stats={stats} loading={loading} />

      {/* ── Tabs ────────────────────────────────────────── */}
      <div className="flex gap-1 border-b border-border">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors',
              tab === t.id
                ? 'text-primary border-b-2 border-primary bg-primary/5'
                : 'text-subtle hover:text-body hover:bg-muted/50',
            )}
          >
            {t.label}
            {t.id === 'recommended' && stats && stats.recommended > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-amber-100 text-amber-700 text-[10px] font-medium h-4 min-w-[16px] px-1">
                {stats.recommended}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Main Content Grid ───────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.65fr)_minmax(20rem,0.92fr)]">

        {/* Sources table — takes 2 cols on lg */}
        <div className="min-w-0">
          <SourcesTable
            sources={sources}
            loading={loading}
            loadingMore={loadingMore}
            hasMore={hasMore}
            error={error}
            actioningId={sourceActionId}
            actionsEnabled={canManageDiscovery}
            actionsDisabledReason="Admin or owner access is required to activate or dismiss discovered sources."
            onLoadMore={loadMore}
            onRetry={refresh}
            onActivate={handleActivate}
            onDismiss={handleDismiss}
          />
        </div>

        {/* Entity review sidebar — 1 col */}
        <div className="min-w-0">
          <EntityReviewPanel
            entities={entities}
            loading={accessLoading || entitiesLoading}
            loadingMore={entitiesLoadingMore}
            hasMore={entitiesHasMore}
            error={entitiesError}
            actionsEnabled={canManageDiscovery}
            actioningId={entityActionId}
            onRetry={refreshEntities}
            onLoadMore={loadMoreEntities}
            onApprove={handleApprove}
            onReject={handleReject}
          />
        </div>
      </div>
    </div>
  )
}
