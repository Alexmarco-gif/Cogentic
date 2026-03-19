'use client'

import { useCallback, useState } from 'react'
import dynamic from 'next/dynamic'
import { AlertTriangle, Globe, Radio } from 'lucide-react'
import { useDomainMap } from '@/lib/hooks/useDomainMap'
import type { MapRegion } from '@/lib/hooks/useDomainMap'
import { useSignals } from '@/lib/hooks/useSignals'
import { RegionSidebar } from '@/components/domains/RegionSidebar'
import { SignalDrawer } from '@/components/signals/SignalDrawer'

// Leaflet MUST be dynamically imported — it references `window`
const MapCanvas = dynamic(() => import('@/components/domains/MapCanvas'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-50">
      <div className="flex flex-col items-center gap-3">
        <Globe className="h-8 w-8 animate-pulse text-indigo-400/50" />
        <span className="text-sm text-subtle">Loading map…</span>
      </div>
    </div>
  ),
})

// ── Slim top header strip ─────────────────────────────────────────────────────

function PageHeader({
  totalSignals,
  criticalCount,
}: {
  totalSignals: number
  criticalCount: number
}) {
  return (
    <div className="flex shrink-0 items-center justify-between border-b border-border bg-surface/80 px-6 py-3 backdrop-blur-sm">
      <div>
        <h1 className="font-display text-base font-semibold text-heading">
          Domain Intelligence Map
        </h1>
        <p className="text-xs text-subtle">Sector signal geography · click any region for full brief</p>
      </div>
      <div className="flex items-center gap-3">
        {criticalCount > 0 && (
          <div className="flex items-center gap-1.5 rounded-full border border-red-500/25 bg-red-500/10 px-3 py-1">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-red-400" />
            </span>
            <span className="text-xs font-medium text-red-400">
              {criticalCount} critical region{criticalCount !== 1 ? 's' : ''}
            </span>
          </div>
        )}
        <div className="flex items-center gap-1.5 text-xs text-subtle">
          <Radio className="h-3 w-3 text-indigo-400" />
          {totalSignals} signals mapped
        </div>
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DomainsPage() {
  const {
    activeDomain,
    setActiveDomain,
    layers,
    toggleLayer,
    activeRegion,
    selectRegion,
    filteredRegions,
    criticalCount,
    totalSignals,
    availableDomains,
    loading,
    error,
    refresh,
  } = useDomainMap()

  const {
    activeDrawerSignal,
    error: drawerError,
    openDrawerById,
    closeDrawer,
    toggleSave,
  } = useSignals({ enabled: false, mode: 'feed' })
  const [pageMessage, setPageMessage] = useState<string | null>(null)

  // Called from both the sidebar card and the map marker
  const handleRegionOpen = useCallback(async (region: MapRegion | null) => {
    selectRegion(region)
    if (!region) {
      setPageMessage(null)
      closeDrawer()
      return
    }

    if (!region.topSignalId) {
      setPageMessage(`No live signal detail is currently available for ${region.name}.`)
      closeDrawer()
      return
    }

    setPageMessage(null)
    await openDrawerById(region.topSignalId)
  }, [closeDrawer, openDrawerById, selectRegion])

  const handleBriefClose = useCallback(() => {
    selectRegion(null)
    setPageMessage(null)
    closeDrawer()
  }, [closeDrawer, selectRegion])

  return (
    <div
      className="flex flex-col overflow-hidden"
      style={{ height: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* Top strip */}
      <PageHeader totalSignals={totalSignals} criticalCount={criticalCount} />

      {(error || drawerError || pageMessage) && (
        <div className="border-b border-border bg-rose-500/10 px-6 py-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-2 text-sm text-rose-100">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-300" />
              <span>{pageMessage ?? drawerError ?? error}</span>
            </div>
            <button
              onClick={() => {
                setPageMessage(null)
                void refresh()
              }}
              className="rounded-md border border-rose-300/30 px-3 py-1 text-xs font-medium text-rose-100 hover:bg-rose-500/10"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* ── Main split layout ────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden lg:flex-row">

        {/* ── Left sidebar ─────────────────────────────────────────────────── */}
        <RegionSidebar
          activeDomain={activeDomain}
          onDomainChange={setActiveDomain}
          layers={layers}
          onToggleLayer={toggleLayer}
          regions={filteredRegions}
          activeRegion={activeRegion}
          onRegionSelect={handleRegionOpen}
          totalSignals={totalSignals}
          criticalCount={criticalCount}
          availableDomains={availableDomains}
          loading={loading}
          error={error}
          onRetry={() => { void refresh() }}
        />

        {/* ── Right: map card ───────────────────────────────────────────────── */}
        <div className="relative z-0 flex flex-1 flex-col overflow-hidden bg-canvas/40 p-4">

          {/* Contained map card — rounded, bordered, not full-screen */}
          {/* isolate keeps Leaflet's internal z-indices from escaping this stacking context */}
          <div className="relative isolate flex-1 overflow-hidden rounded-xl border border-border shadow-[0_4px_24px_rgba(0,0,0,0.18)]">
            <MapCanvas
              regions={filteredRegions}
              activeRegionId={activeRegion?.id ?? null}
              layers={layers}
              onRegionClick={handleRegionOpen}
            />
          </div>
        </div>
      </div>

      {/* ── Full Intelligence Brief drawer ───────────────────────────────────── */}
      {/* Reuses the exact same SignalDrawer used throughout the app */}
      <SignalDrawer
        signal={activeDrawerSignal}
        onClose={handleBriefClose}
        onSave={toggleSave}
      />
    </div>
  )
}
