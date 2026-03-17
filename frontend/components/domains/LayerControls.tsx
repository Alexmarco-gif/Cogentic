'use client'

import { memo } from 'react'
import { Layers, Eye, EyeOff, ChevronDown, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SignalDomain } from '@/lib/hooks/useSignals'
import type { DomainLayers } from '@/lib/hooks/useDomainMap'

// ── Domain tab options ────────────────────────────────────────────────────────

type DomainOption = SignalDomain | 'All'

const DOMAIN_TABS: { id: DomainOption; label: string; color: string }[] = [
  { id: 'All', label: 'All', color: 'text-indigo-400' },
  { id: 'E-Commerce & Retail', label: 'E-Commerce', color: 'text-violet-400' },
  { id: 'Financial Services', label: 'Finance', color: 'text-emerald-400' },
  { id: 'Media & Brand', label: 'Media', color: 'text-pink-400' },
  { id: 'Telecom & Digital', label: 'Telecom', color: 'text-blue-400' },
  { id: 'Agriculture & Agritech', label: 'Agriculture', color: 'text-amber-400' },
]

// ── Layer toggle row ──────────────────────────────────────────────────────────

interface LayerRowProps {
  label: string
  description: string
  enabled: boolean
  onToggle: () => void
  dotColor: string
}

function LayerRow({ label, description, enabled, onToggle, dotColor }: LayerRowProps) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left',
        'transition-colors duration-150',
        enabled ? 'bg-white/5' : 'hover:bg-white/4',
      )}
    >
      {/* Colored dot indicator */}
      <span
        className={cn(
          'h-2 w-2 shrink-0 rounded-full transition-opacity',
          dotColor,
          enabled ? 'opacity-100' : 'opacity-30',
        )}
      />

      {/* Text */}
      <div className="min-w-0 flex-1">
        <div className={cn('text-xs font-medium', enabled ? 'text-heading' : 'text-subtle')}>
          {label}
        </div>
        <div className="text-[10px] text-subtle/70">{description}</div>
      </div>

      {/* Eye toggle */}
      <span className={cn('shrink-0 transition-colors', enabled ? 'text-body' : 'text-subtle/40')}>
        {enabled ? (
          <Eye className="h-3.5 w-3.5" />
        ) : (
          <EyeOff className="h-3.5 w-3.5" />
        )}
      </span>
    </button>
  )
}

// ── Legend row ────────────────────────────────────────────────────────────────

function RiskLegend() {
  const items = [
    { label: 'Critical', color: 'bg-red-500' },
    { label: 'Elevated', color: 'bg-orange-400' },
    { label: 'Moderate', color: 'bg-amber-400' },
    { label: 'Stable', color: 'bg-emerald-500' },
  ]
  return (
    <div className="border-t border-border/50 px-3 py-2.5">
      <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-widest text-subtle/60">
        Risk Legend
      </p>
      <div className="grid grid-cols-2 gap-1">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-1.5">
            <span className={cn('h-2 w-2 rounded-full', item.color)} />
            <span className="text-[10px] text-subtle">{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface LayerControlsProps {
  activeDomain: DomainOption
  onDomainChange: (d: DomainOption) => void
  layers: DomainLayers
  onToggleLayer: (key: keyof DomainLayers) => void
  totalSignals: number
  criticalCount: number
}

// ── Main component ────────────────────────────────────────────────────────────

export const LayerControls = memo(function LayerControls({
  activeDomain,
  onDomainChange,
  layers,
  onToggleLayer,
  totalSignals,
  criticalCount,
}: LayerControlsProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-0 overflow-hidden',
        'rounded-xl border border-border',
        'bg-[#0F1117]/90 backdrop-blur-md',
        'shadow-[0_8px_32px_rgba(0,0,0,0.4)]',
        'w-56',
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-border/50">
        <Layers className="h-3.5 w-3.5 shrink-0 text-indigo-400" />
        <span className="text-xs font-semibold text-heading">Map Layers</span>
        <div className="ml-auto flex items-center gap-1.5">
          {criticalCount > 0 && (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-red-500/20 text-[9px] font-bold text-red-400">
              {criticalCount}
            </span>
          )}
          <span className="text-[10px] text-subtle">{totalSignals} signals</span>
        </div>
      </div>

      {/* Domain filter tabs */}
      <div className="px-3 py-2 border-b border-border/50">
        <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-widest text-subtle/60">
          Domain
        </p>
        <div className="flex flex-col gap-0.5">
          {DOMAIN_TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onDomainChange(tab.id)}
              className={cn(
                'flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-[11px] transition-colors',
                activeDomain === tab.id
                  ? cn('font-semibold', tab.color, 'bg-white/8')
                  : 'text-subtle hover:text-body hover:bg-white/4',
              )}
            >
              {activeDomain === tab.id && (
                <span className={cn('h-1 w-1 rounded-full', tab.color.replace('text-', 'bg-'))} />
              )}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Layer toggles */}
      <div className="px-0 py-1.5">
        <p className="mb-1 px-3 text-[9px] font-semibold uppercase tracking-widest text-subtle/60">
          Overlays
        </p>
        <LayerRow
          label="Risk Heatmap"
          description="Colour markers by severity"
          enabled={layers.riskHeatmap}
          onToggle={() => onToggleLayer('riskHeatmap')}
          dotColor="bg-red-500"
        />
        <LayerRow
          label="Opportunities"
          description="Highlight high-opportunity zones"
          enabled={layers.opportunities}
          onToggle={() => onToggleLayer('opportunities')}
          dotColor="bg-emerald-500"
        />
        <LayerRow
          label="Signal Density"
          description="Scale markers by signal volume"
          enabled={layers.signalDensity}
          onToggle={() => onToggleLayer('signalDensity')}
          dotColor="bg-indigo-400"
        />
      </div>

      {/* Risk legend */}
      <RiskLegend />
    </div>
  )
})
