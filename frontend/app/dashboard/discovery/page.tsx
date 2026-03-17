'use client'

import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Radar, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Dialog } from '@/components/ui/Dialog'
import { DiscoveryStatsBar } from '@/components/discovery/DiscoveryStatsBar'
import { SourcesTable } from '@/components/discovery/SourcesTable'
import { EntityReviewPanel } from '@/components/discovery/EntityReviewPanel'
import { useDiscoveredSources, usePendingEntities } from '@/lib/hooks/useDiscovery'
import { getIndustries, type IndustryItem } from '@/lib/api/discovered_sources'

type StatusTab = 'all' | 'recommended' | 'activated' | 'dismissed'

const TABS: { id: StatusTab; label: string }[] = [
  { id: 'all',         label: 'All Sources' },
  { id: 'recommended', label: 'Recommended' },
  { id: 'activated',   label: 'Activated' },
  { id: 'dismissed',   label: 'Dismissed' },
]

export default function DiscoveryPage() {
  const [tab, setTab] = useState<StatusTab>('all')

  const statusFilter = tab === 'all' ? undefined : tab
  const { sources, stats, loading, refresh, activate, dismiss } =
    useDiscoveredSources(statusFilter as 'recommended' | 'activated' | 'dismissed' | undefined)

  const {
    entities,
    loading: entitiesLoading,
    approve,
    reject,
  } = usePendingEntities()

  // Industry picker state
  const [industries, setIndustries] = useState<IndustryItem[]>([])
  const [industriesError, setIndustriesError] = useState(false)
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null)
  const [activating, setActivating] = useState(false)

  useEffect(() => {
    getIndustries().then(setIndustries).catch(() => setIndustriesError(true))
  }, [])

  const handleActivate = useCallback((sourceId: string) => {
    setPendingSourceId(sourceId)
  }, [])

  const handleConfirmActivate = useCallback(async (industryId: string) => {
    if (!pendingSourceId) return
    setActivating(true)
    try {
      await activate(pendingSourceId, industryId)
    } finally {
      setActivating(false)
      setPendingSourceId(null)
    }
  }, [pendingSourceId, activate])

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-6">

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
          ) : industries.length === 0 ? (
            <p className="text-sm text-subtle py-4 text-center">Loading industries…</p>
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
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Radar size={20} className="text-primary" />
            <h1 className="font-display text-xl font-semibold text-heading">
              Source Discovery
            </h1>
          </div>
        </div>
        <Button size="sm" variant="outline" onClick={refresh}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>

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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Sources table — takes 2 cols on lg */}
        <div className="lg:col-span-2">
          <SourcesTable
            sources={sources}
            loading={loading}
            onActivate={handleActivate}
            onDismiss={dismiss}
          />
        </div>

        {/* Entity review sidebar — 1 col */}
        <div>
          <EntityReviewPanel
            entities={entities}
            loading={entitiesLoading}
            onApprove={approve}
            onReject={reject}
          />
        </div>
      </div>
    </div>
  )
}
