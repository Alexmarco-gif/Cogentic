'use client'

/**
 * Pipeline admin page — scheduler controls + source health monitoring.
 *
 * Admin-only page for managing the signal acquisition pipeline:
 * - Start/stop scheduler
 * - Trigger manual tier fetches
 * - View source health (healthy/stale/degraded/critical)
 * - See auto-discovered sources status
 */

import { useCallback, useEffect, useState } from 'react'
import {
  Activity, Play, Square, RefreshCw, AlertTriangle, CheckCircle,
  Clock, XCircle, Zap, Globe,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import {
  getPipelineStatus,
  startScheduler,
  stopScheduler,
  triggerTierFetch,
  getSourceHealth,
} from '@/lib/api/pipeline'
import type { SourceHealthSummary, SourceHealthContract } from '@/lib/api/pipeline'

// ── Types ───────────────────────────────────────────────────────────────────

interface PipelineStatus {
  scheduler_running: boolean
  active_contracts: number
  degraded_contracts: number
  degraded_names: string[]
  queues: Record<string, { name: string; count: number; failed: number; scheduled: number }>
  workers_online: number
  workers: Array<{
    name: string
    state: string
    queues: string[]
    current_job_id: string | null
    last_heartbeat: string | null
  }>
  provider_readiness: Record<string, boolean>
}

// ── Health badge ────────────────────────────────────────────────────────────

const HEALTH_CONFIG = {
  healthy:  { icon: CheckCircle,   color: 'text-emerald-600 bg-emerald-50', label: 'Healthy'  },
  stale:    { icon: Clock,         color: 'text-amber-600 bg-amber-50',     label: 'Stale'    },
  degraded: { icon: AlertTriangle, color: 'text-orange-600 bg-orange-50',   label: 'Degraded' },
  critical: { icon: XCircle,       color: 'text-red-600 bg-red-50',         label: 'Critical' },
} as const

function HealthBadge({ health }: { health: keyof typeof HEALTH_CONFIG }) {
  const cfg = HEALTH_CONFIG[health]
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  )
}

// ── Contract row ────────────────────────────────────────────────────────────

function ContractRow({ contract }: { contract: SourceHealthContract }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 hover:bg-muted rounded">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-heading truncate">{contract.name}</p>
          {contract.is_auto_discovered && (
            <span className="text-[10px] bg-violet-100 text-violet-700 rounded px-1.5 py-0.5 font-medium">
              AUTO
            </span>
          )}
        </div>
        <p className="text-xs text-subtle truncate">{contract.source_url}</p>
      </div>
      <div className="flex items-center gap-3 ml-3 shrink-0">
        <span className="text-xs text-subtle">
          {contract.failure_count > 0 ? `${contract.failure_count} failures` : ''}
        </span>
        {contract.last_fetched_at && (
          <span className="text-xs text-subtle">
            {new Date(contract.last_fetched_at).toLocaleDateString()}
          </span>
        )}
        <HealthBadge health={contract.health} />
      </div>
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [health, setHealth] = useState<SourceHealthSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState(false)
  const [fetchingTier, setFetchingTier] = useState<string | null>(null)
  const [tierFetchError, setTierFetchError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const [s, h] = await Promise.all([getPipelineStatus(), getSourceHealth()])
      setStatus(s)
      setHealth(h)
    } catch {
      // Non-admin may not have access
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const handleToggle = async () => {
    if (!status) return
    setToggling(true)
    try {
      if (status.scheduler_running) {
        await stopScheduler()
      } else {
        await startScheduler()
      }
      await refresh()
    } finally {
      setToggling(false)
    }
  }

  const handleTierFetch = async (tier: string) => {
    setFetchingTier(tier)
    setTierFetchError(null)
    try {
      await triggerTierFetch({ tier } as any)
    } catch {
      setTierFetchError(`Failed to trigger ${tier} fetch. Please try again.`)
    } finally {
      setFetchingTier(null)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6 px-3 py-4 sm:px-4 lg:px-0 animate-pulse">
        <div className="h-10 w-48 bg-muted rounded" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-canvas rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  const tiers = ['realtime', 'standard', 'slow', 'daily']

  return (
    <div className="mx-auto max-w-[1240px] space-y-6 px-3 py-4 sm:px-4 lg:px-0">
      {/* Header */}
      <div className="surface-panel flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-success-bg p-2">
            <Activity className="h-5 w-5 text-success" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-heading">Pipeline Admin</h1>
            <p className="text-sm text-subtle">
              Scheduler controls &amp; source health monitoring
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={refresh}>
          <RefreshCw className="h-4 w-4 mr-1.5" />
          Refresh
        </Button>
      </div>

      {/* Scheduler controls */}
      <div className="surface-panel p-5">
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-base font-semibold text-heading">Scheduler</h2>
          <Button
            variant={status?.scheduler_running ? 'destructive' : 'primary'}
            size="sm"
            onClick={handleToggle}
            disabled={toggling}
          >
            {status?.scheduler_running ? (
              <><Square className="h-4 w-4 mr-1.5" />Stop</>
            ) : (
              <><Play className="h-4 w-4 mr-1.5" />Start</>
            )}
          </Button>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
          <div>
            <span className="text-subtle">Status</span>
            <p className="font-medium">
              {status?.scheduler_running ? (
                <span className="text-emerald-600">Running</span>
              ) : (
                <span className="text-red-600">Stopped</span>
              )}
            </p>
          </div>
          <div>
            <span className="text-subtle">Active Contracts</span>
            <p className="font-medium">{status?.active_contracts ?? 0}</p>
          </div>
          <div>
            <span className="text-subtle">Degraded</span>
            <p className="font-medium text-orange-600">{status?.degraded_contracts ?? 0}</p>
          </div>
        </div>

        <div className="mt-4 grid gap-4 border-t border-border pt-4 md:grid-cols-3">
          <div className="rounded-lg border border-border bg-surface p-4">
            <span className="text-sm text-subtle">Workers Online</span>
            <p className={`text-xl font-semibold ${(status?.workers_online ?? 0) > 0 ? 'text-emerald-600' : 'text-red-600'}`}>
              {status?.workers_online ?? 0}
            </p>
            <p className="mt-1 text-xs text-subtle">
              {(status?.workers_online ?? 0) > 0
                ? 'RQ workers are connected and available to process acquisition jobs.'
                : 'No RQ workers are currently visible. Scheduled fetches will queue but not be processed.'}
            </p>
          </div>
          <div className="rounded-lg border border-border bg-surface p-4 md:col-span-2">
            <span className="text-sm text-subtle">Provider Readiness</span>
            <div className="mt-3 flex flex-wrap gap-2">
              {Object.entries(status?.provider_readiness ?? {}).map(([provider, ready]) => (
                <span
                  key={provider}
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${
                    ready ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                  }`}
                >
                  {ready ? <CheckCircle className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                  {provider.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Manual tier fetch buttons */}
        <div className="mt-4 border-t border-border pt-4">
          <span className="text-sm text-subtle mb-2 block">Manual Fetch:</span>
          <div className="flex flex-wrap gap-2">
            {tiers.map((tier) => (
              <Button
                key={tier}
                variant="outline"
                size="sm"
                onClick={() => handleTierFetch(tier)}
                disabled={fetchingTier === tier}
              >
                <Zap className="h-3 w-3 mr-1" />
                {tier}
              </Button>
            ))}
          </div>
          {tierFetchError && (
            <p className="mt-2 text-xs text-rose-500">{tierFetchError}</p>
          )}
        </div>
      </div>

      {status && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <div className="surface-panel p-5">
            <h2 className="text-base font-semibold text-heading">Queue Depth</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {Object.values(status.queues ?? {}).map((queue) => (
                <div key={queue.name} className="rounded-lg border border-border bg-surface p-4">
                  <p className="text-sm font-medium text-heading capitalize">{queue.name}</p>
                  <p className="mt-2 text-xs text-subtle">Queued: {queue.count}</p>
                  <p className="text-xs text-subtle">Failed: {queue.failed}</p>
                  <p className="text-xs text-subtle">Scheduled: {queue.scheduled}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="surface-panel p-5">
            <h2 className="text-base font-semibold text-heading">Worker Heartbeats</h2>
            <div className="mt-4 space-y-3">
              {(status.workers ?? []).length === 0 ? (
                <div className="rounded-lg border border-red-200 bg-red-50/50 p-4 text-sm text-red-800">
                  No workers are currently reporting to Redis. The acquisition pipeline needs at least one running worker to fetch, refine, and refresh intelligence.
                </div>
              ) : (
                status.workers.map((worker) => (
                  <div key={worker.name} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-medium text-heading">{worker.name}</p>
                      <HealthBadge health={worker.state === 'busy' || worker.state === 'idle' ? 'healthy' : 'stale'} />
                    </div>
                    <p className="mt-2 text-xs text-subtle">Queues: {worker.queues.join(', ') || 'None'}</p>
                    <p className="text-xs text-subtle">State: {worker.state}</p>
                    <p className="text-xs text-subtle">Current job: {worker.current_job_id ?? 'Idle'}</p>
                    <p className="text-xs text-subtle">Last heartbeat: {worker.last_heartbeat ? new Date(worker.last_heartbeat).toLocaleString() : 'Unknown'}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Source health summary */}
      {health && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {[
              { label: 'Total Active', value: health.total_active, color: 'text-heading' },
              { label: 'Healthy', value: health.healthy, color: 'text-emerald-600' },
              { label: 'Stale', value: health.stale, color: 'text-amber-600' },
              { label: 'Degraded', value: health.degraded, color: 'text-orange-600' },
              { label: 'Critical', value: health.critical, color: 'text-red-600' },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-lg border border-border bg-surface p-4">
                <span className="text-sm text-subtle">{label}</span>
                <p className={`text-2xl font-semibold ${color}`}>{value}</p>
              </div>
            ))}
          </div>

          {/* Auto-discovered badge */}
          <div className="flex items-center gap-2 text-sm text-body">
            <Globe className="h-4 w-4" />
            <span>{health.auto_discovered_active} auto-discovered sources active</span>
          </div>

          {/* Problem contracts */}
          {health.critical_contracts.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50/50 p-4">
              <h3 className="text-sm font-semibold text-red-800 mb-2">
                Critical ({health.critical_contracts.length})
              </h3>
              <div className="space-y-1">
                {health.critical_contracts.map((c) => (
                  <ContractRow key={c.id} contract={c} />
                ))}
              </div>
            </div>
          )}

          {health.degraded_contracts.length > 0 && (
            <div className="rounded-lg border border-orange-200 bg-orange-50/50 p-4">
              <h3 className="text-sm font-semibold text-orange-800 mb-2">
                Degraded ({health.degraded_contracts.length})
              </h3>
              <div className="space-y-1">
                {health.degraded_contracts.map((c) => (
                  <ContractRow key={c.id} contract={c} />
                ))}
              </div>
            </div>
          )}

          {health.stale_contracts.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
              <h3 className="text-sm font-semibold text-amber-800 mb-2">
                Stale ({health.stale_contracts.length})
              </h3>
              <div className="space-y-1">
                {health.stale_contracts.map((c) => (
                  <ContractRow key={c.id} contract={c} />
                ))}
              </div>
            </div>
          )}

          {health.critical === 0 && health.degraded === 0 && health.stale === 0 && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-6 text-center">
              <CheckCircle className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-emerald-800 font-medium">All sources healthy</p>
              <p className="text-sm text-emerald-600 mt-1">
                {health.total_active} active contracts operating normally
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
