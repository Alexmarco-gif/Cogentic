'use client'

import { memo } from 'react'
import { X, MapPin, Zap, TrendingUp, Radio, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MapRegion } from '@/lib/hooks/useDomainMap'
import { RISK_LEVEL_STYLES } from '@/lib/hooks/useDomainMap'
import { getDomainDot } from '@/lib/domain-colors'

// ── Domain short labels ───────────────────────────────────────────────────────

/** Shorten a domain name to a short label (first word or truncated) */
function domainLabel(d: string): string {
  if (d.length <= 12) return d
  return d.split(/[\s&]/)[0] || d.slice(0, 12)
}

// ── Opportunity bar ───────────────────────────────────────────────────────────

function OpportunityBar({ score }: { score: number }) {
  const color =
    score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-slate-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/8">
        <div
          className={cn('h-full rounded-full transition-all duration-500', color)}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="w-8 text-right text-[11px] font-medium text-body tabular-nums">
        {score}
      </span>
    </div>
  )
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface RegionPopoverProps {
  region: MapRegion | null
  onClose: () => void
  className?: string
}

// ── Component ─────────────────────────────────────────────────────────────────

export const RegionPopover = memo(function RegionPopover({
  region,
  onClose,
  className,
}: RegionPopoverProps) {
  if (!region) return null

  const riskStyle = RISK_LEVEL_STYLES[region.riskLevel]

  return (
    <div
      className={cn(
        'flex flex-col overflow-hidden',
        'rounded-xl border border-border',
        'bg-[#0F1117]/95 backdrop-blur-xl',
        'shadow-[0_16px_48px_rgba(0,0,0,0.6)]',
        'w-72',
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 py-3 border-b border-border/50">
        <div>
          <div className="flex items-center gap-1.5">
            <MapPin className="h-3 w-3 text-subtle" />
            <span className="text-xs text-subtle">{region.state}</span>
          </div>
          <h3 className="mt-0.5 text-base font-semibold text-heading">{region.name}</h3>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1.5 text-subtle transition-colors hover:bg-white/8 hover:text-body"
          aria-label="Close"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 divide-x divide-border/50 border-b border-border/50">
        <div className="flex flex-col items-center py-2.5">
          <span className="font-display text-lg font-bold text-heading tabular-nums">
            {region.signalCount}
          </span>
          <span className="text-[9px] font-medium uppercase tracking-wide text-subtle">
            Signals
          </span>
        </div>
        <div className="flex flex-col items-center py-2.5">
          <span
            className={cn(
              'rounded-full border px-2 py-0.5 text-[10px] font-semibold capitalize',
              riskStyle,
            )}
          >
            {region.riskLevel}
          </span>
          <span className="mt-0.5 text-[9px] font-medium uppercase tracking-wide text-subtle">
            Risk
          </span>
        </div>
        <div className="flex flex-col items-center py-2.5">
          <span className="font-display text-lg font-bold text-emerald-400 tabular-nums">
            {region.opportunityScore}
          </span>
          <span className="text-[9px] font-medium uppercase tracking-wide text-subtle">
            Opp. Score
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-col gap-3 px-4 py-3">
        {/* Summary */}
        <p className="text-[12px] leading-relaxed text-body">{region.summary}</p>

        {/* Opportunity bar */}
        <div>
          <div className="mb-1 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-subtle/70">
            <TrendingUp className="h-3 w-3" />
            Opportunity Score
          </div>
          <OpportunityBar score={region.opportunityScore} />
        </div>

        {/* Domains */}
        <div>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-subtle/70">
            Active Domains
          </p>
          <div className="flex flex-wrap gap-1.5">
            {region.domains.map((d) => (
              <span
                key={d}
                className="flex items-center gap-1 rounded-full bg-white/6 px-2 py-0.5 text-[10px] text-body"
              >
                <span className={cn('h-1.5 w-1.5 rounded-full', getDomainDot(d))} />
                {domainLabel(d)}
              </span>
            ))}
          </div>
        </div>

        {/* Top signal */}
        <div className="rounded-lg border border-border/50 bg-white/4 px-3 py-2.5">
          <div className="mb-1 flex items-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-subtle/70">
            <Radio className="h-3 w-3" />
            Top Signal
          </div>
          <p className="text-[11px] leading-snug text-body">{region.topSignal}</p>
        </div>
      </div>

      {/* Footer action */}
      <div className="flex items-center justify-between border-t border-border/50 px-4 py-2.5">
        <div className="flex items-center gap-1.5">
          <Zap className="h-3 w-3 text-indigo-400" />
          <span className="text-[11px] text-subtle">
            {region.signalCount} active signal{region.signalCount !== 1 ? 's' : ''}
          </span>
        </div>
        <button
          className={cn(
            'flex items-center gap-1 rounded-md px-2.5 py-1.5',
            'bg-indigo-500/15 text-indigo-400 text-[11px] font-medium',
            'transition-colors hover:bg-indigo-500/25',
          )}
        >
          Investigate
          <ExternalLink className="h-3 w-3" />
        </button>
      </div>
    </div>
  )
})
