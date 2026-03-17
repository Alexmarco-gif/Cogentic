'use client'

import { memo } from 'react'
import { Layers, Eye, EyeOff, MapPin, Zap, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MapRegion, DomainLayers, RiskLevel } from '@/lib/hooks/useDomainMap'
import { RISK_LEVEL_STYLES } from '@/lib/hooks/useDomainMap'
import { getDomainDot, getDomainAccent } from '@/lib/domain-colors'

// ── Domain tab config — now data-driven ───────────────────────────────────────

type DomainOption = string

/** Build domain tabs dynamically from whatever domains exist in the data */
export function buildDomainTabs(domains: string[]): { id: DomainOption; label: string; accent: string; dot: string }[] {
  const allTab = { id: 'All', label: 'All Domains', accent: 'text-indigo-500', dot: 'bg-indigo-500' }
  const unique = Array.from(new Set(domains)).sort()
  return [
    allTab,
    ...unique.map(d => ({
      id: d,
      label: d.length > 14 ? d.split(' ')[0] : d,
      accent: getDomainAccent(d),
      dot: getDomainDot(d),
    })),
  ]
}

// ── Severity left-bar colors ──────────────────────────────────────────────────

const SEVERITY_BAR: Record<string, string> = {
  critical: 'bg-red-500',
  high:     'bg-orange-400',
  medium:   'bg-amber-400',
  low:      'bg-slate-400',
}

// ── Opportunity progress bar ──────────────────────────────────────────────────

function OpportunityBar({ score }: { score: number }) {
  const fill = score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-slate-400'
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-border/60">
        <div className={cn('h-full rounded-full', fill)} style={{ width: `${score}%` }} />
      </div>
      <span className="w-7 text-right text-[10px] tabular-nums text-subtle">{score}</span>
    </div>
  )
}

// ── Individual region card ────────────────────────────────────────────────────

interface RegionCardProps {
  region: MapRegion
  isActive: boolean
  onSelect: () => void
}

function RegionCard({ region, isActive, onSelect }: RegionCardProps) {
  const riskStyle = RISK_LEVEL_STYLES[region.riskLevel]

  return (
    <button
      onClick={onSelect}
      className={cn(
        'group relative flex w-full gap-0 overflow-hidden rounded-lg border text-left transition-all duration-150',
        isActive
          ? 'border-indigo-500/40 bg-indigo-500/8 shadow-sm'
          : 'border-border/60 bg-surface hover:border-border hover:bg-surface/80',
      )}
    >
      {/* Left severity strip */}
      <div className={cn('w-1 shrink-0 rounded-l-lg', SEVERITY_BAR[region.severity])} />

      {/* Content */}
      <div className="min-w-0 flex-1 px-3 py-2.5">
        {/* Name row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className={cn(
              'truncate text-sm font-semibold transition-colors',
              isActive ? 'text-indigo-400' : 'text-heading group-hover:text-heading/90',
            )}>
              {region.name}
            </p>
            <div className="flex items-center gap-1 mt-0.5">
              <MapPin className="h-2.5 w-2.5 shrink-0 text-subtle/60" />
              <span className="text-[10px] text-subtle truncate">{region.state}</span>
            </div>
          </div>

          {/* Signal count bubble */}
          <div className="shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-white/8 text-[11px] font-bold tabular-nums text-body">
            {region.signalCount}
          </div>
        </div>

        {/* Risk + opportunity row */}
        <div className="mt-2 flex items-center gap-2">
          <span className={cn(
            'rounded-full border px-1.5 py-0.5 text-[9px] font-semibold capitalize leading-none',
            riskStyle,
          )}>
            {region.riskLevel}
          </span>
          <div className="flex flex-1 items-center gap-1">
            <TrendingUp className="h-2.5 w-2.5 shrink-0 text-subtle/60" />
            <OpportunityBar score={region.opportunityScore} />
          </div>
        </div>

        {/* Top signal preview */}
        {isActive && (
          <p className="mt-2 line-clamp-2 text-[10px] leading-relaxed text-subtle border-t border-border/40 pt-2">
            {region.topSignal}
          </p>
        )}
      </div>
    </button>
  )
}

// ── Layer toggle row ──────────────────────────────────────────────────────────

function LayerToggle({
  label,
  description,
  enabled,
  onToggle,
  dotColor,
}: {
  label: string
  description: string
  enabled: boolean
  onToggle: () => void
  dotColor: string
}) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left transition-colors',
        enabled ? 'bg-white/5' : 'hover:bg-white/4',
      )}
    >
      <span className={cn('h-2 w-2 shrink-0 rounded-full transition-opacity', dotColor, enabled ? 'opacity-100' : 'opacity-25')} />
      <div className="min-w-0 flex-1">
        <p className={cn('text-xs font-medium', enabled ? 'text-heading' : 'text-subtle')}>{label}</p>
        <p className="text-[10px] text-subtle/60">{description}</p>
      </div>
      <span className={cn('shrink-0', enabled ? 'text-body' : 'text-subtle/30')}>
        {enabled ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
      </span>
    </button>
  )
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface RegionSidebarProps {
  activeDomain: DomainOption
  onDomainChange: (d: DomainOption) => void
  layers: DomainLayers
  onToggleLayer: (key: keyof DomainLayers) => void
  regions: MapRegion[]
  activeRegion: MapRegion | null
  onRegionSelect: (region: MapRegion | null) => void
  totalSignals: number
  criticalCount: number
  availableDomains?: string[]
}

// ── Main component ────────────────────────────────────────────────────────────

export const RegionSidebar = memo(function RegionSidebar({
  activeDomain,
  onDomainChange,
  layers,
  onToggleLayer,
  regions,
  activeRegion,
  onRegionSelect,
  totalSignals,
  criticalCount,
  availableDomains = [],
}: RegionSidebarProps) {
  const domainTabs = buildDomainTabs(availableDomains)
  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-border bg-surface overflow-hidden">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="shrink-0 px-4 py-4 border-b border-border">
        <h2 className="font-display text-sm font-semibold text-heading">Region Intelligence</h2>
        <div className="mt-1.5 flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Zap className="h-3 w-3 text-indigo-400" />
            <span className="text-xs text-subtle">{totalSignals} signals</span>
          </div>
          {criticalCount > 0 && (
            <div className="flex items-center gap-1">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-60" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-red-400" />
              </span>
              <span className="text-xs font-medium text-red-400">{criticalCount} critical</span>
            </div>
          )}
        </div>
      </div>

      {/* ── Domain filter tabs ──────────────────────────────────────────────── */}
      <div className="shrink-0 px-3 py-3 border-b border-border">
        <p className="mb-2 text-[9px] font-semibold uppercase tracking-widest text-subtle/50">
          Filter by Domain
        </p>
        <div className="flex flex-col gap-0.5">
          {domainTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onDomainChange(tab.id)}
              className={cn(
                'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-left text-xs transition-all duration-150',
                activeDomain === tab.id
                  ? cn('font-semibold bg-white/8', tab.accent)
                  : 'font-medium text-subtle hover:text-body hover:bg-white/4',
              )}
            >
              <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', tab.dot,
                activeDomain === tab.id ? 'opacity-100' : 'opacity-30')} />
              {tab.label}
              {activeDomain === tab.id && (
                <span className="ml-auto text-[10px] font-normal text-subtle">{regions.length}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Map layer toggles ───────────────────────────────────────────────── */}
      <div className="shrink-0 px-0 py-2 border-b border-border">
        <p className="mb-1 px-3 text-[9px] font-semibold uppercase tracking-widest text-subtle/50">
          Map Overlays
        </p>
        <LayerToggle
          label="Risk Heatmap"
          description="Colour markers by severity level"
          enabled={layers.riskHeatmap}
          onToggle={() => onToggleLayer('riskHeatmap')}
          dotColor="bg-red-500"
        />
        <LayerToggle
          label="Opportunities"
          description="Highlight high-score zones"
          enabled={layers.opportunities}
          onToggle={() => onToggleLayer('opportunities')}
          dotColor="bg-emerald-500"
        />
        <LayerToggle
          label="Signal Density"
          description="Scale marker size by volume"
          enabled={layers.signalDensity}
          onToggle={() => onToggleLayer('signalDensity')}
          dotColor="bg-indigo-400"
        />
      </div>

      {/* ── Region cards list (scrollable) ─────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-3 space-y-2 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
        <div className="flex items-center justify-between mb-1">
          <p className="text-[9px] font-semibold uppercase tracking-widest text-subtle/50">
            {regions.length} region{regions.length !== 1 ? 's' : ''}
          </p>
          {activeRegion && (
            <button
              onClick={() => onRegionSelect(null)}
              className="text-[10px] text-subtle hover:text-body transition-colors"
            >
              Clear selection
            </button>
          )}
        </div>

        {regions.map((region) => (
          <RegionCard
            key={region.id}
            region={region}
            isActive={activeRegion?.id === region.id}
            onSelect={() =>
              onRegionSelect(activeRegion?.id === region.id ? null : region)
            }
          />
        ))}
      </div>

      {/* ── Risk legend footer ──────────────────────────────────────────────── */}
      <div className="shrink-0 border-t border-border px-3 py-2.5">
        <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-widest text-subtle/50">
          Risk Scale
        </p>
        <div className="grid grid-cols-4 gap-1">
          {[
            { label: 'Critical', color: 'bg-red-500' },
            { label: 'Elevated', color: 'bg-orange-400' },
            { label: 'Moderate', color: 'bg-amber-400' },
            { label: 'Stable',   color: 'bg-emerald-500' },
          ].map((item) => (
            <div key={item.label} className="flex flex-col items-center gap-1">
              <span className={cn('h-2 w-2 rounded-full', item.color)} />
              <span className="text-[9px] text-subtle">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
})
