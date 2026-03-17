'use client'

import { useCallback, useState } from 'react'
import dynamic from 'next/dynamic'
import { Globe, Radio } from 'lucide-react'
import { useDomainMap } from '@/lib/hooks/useDomainMap'
import type { MapRegion } from '@/lib/hooks/useDomainMap'
import type { Signal } from '@/lib/hooks/useSignals'
import { useDomains } from '@/lib/hooks/useDomains'
import { RegionSidebar } from '@/components/domains/RegionSidebar'
import { SignalDrawer } from '@/components/signals/SignalDrawer'
import { buildRegionSignal } from '@/lib/utils/buildRegionSignal'

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
  } = useDomainMap()

  const { names: domainNames } = useDomains()

  // ── Brief drawer state ────────────────────────────────────────────────────
  const [briefSignal, setBriefSignal] = useState<Signal | null>(null)

  // Called from both the sidebar card and the map marker
  const handleRegionOpen = useCallback((region: MapRegion | null) => {
    selectRegion(region)
    if (region) {
      setBriefSignal(buildRegionSignal(region))
    }
  }, [selectRegion])

  const handleBriefClose = useCallback(() => {
    setBriefSignal(null)
    selectRegion(null)
  }, [selectRegion])

  return (
    <div
      className="flex flex-col overflow-hidden"
      style={{ height: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* Top strip */}
      <PageHeader totalSignals={totalSignals} criticalCount={criticalCount} />

      {/* ── Main split layout ────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

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
          availableDomains={domainNames}
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
        signal={briefSignal}
        onClose={handleBriefClose}
        onSave={() => {/* region briefs are not saveable from this surface */}}
      />
    </div>
  )
}
