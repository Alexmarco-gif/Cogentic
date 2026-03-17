'use client'

import { useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  TrendingUp,
  Shield,
  MapPin,
  GitBranch,
  Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { IntelligenceSignalResponse } from '@/lib/api/types'

// ── Country flag emoji helper ─────────────────────────────────────────────────

function countryFlag(iso3: string | null | undefined): string {
  if (!iso3) return ''
  // Map common ISO 3166-1 alpha-3 → alpha-2 for flag emoji
  const MAP: Record<string, string> = {
    NGA: 'NG', KEN: 'KE', GHA: 'GH', ZAF: 'ZA', EGY: 'EG',
    ETH: 'ET', TZA: 'TZ', UGA: 'UG', RWA: 'RW', SEN: 'SN',
    CIV: 'CI', CMR: 'CM', ZMB: 'ZM', ZWE: 'ZW', MOZ: 'MZ',
    USA: 'US', GBR: 'GB', FRA: 'FR', DEU: 'DE',
  }
  const a2 = MAP[iso3.toUpperCase()]
  if (!a2) return ''
  return a2.toUpperCase().replace(/./g, (c) =>
    String.fromCodePoint(c.charCodeAt(0) + 127397)
  )
}

// ── Anomaly badge ─────────────────────────────────────────────────────────────

function AnomalyBadge({ score }: { score: number | null | undefined }) {
  if (score == null || score < 0.5) return null
  const isHigh = score >= 0.75
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[10px] font-semibold',
        isHigh
          ? 'bg-red-500/15 text-red-400'
          : 'bg-amber-500/15 text-amber-400',
      )}
    >
      <AlertTriangle className="h-2.5 w-2.5" />
      {Math.round(score * 100)}% anomaly
    </span>
  )
}

// ── Single intelligence card ──────────────────────────────────────────────────

function IntelCard({ item }: { item: IntelligenceSignalResponse }) {
  const flag = countryFlag(item.primary_country)

  return (
    <div
      className={cn(
        'flex flex-col gap-2 rounded-lg border border-white/6 bg-white/3',
        'p-3 transition-colors hover:border-white/10 hover:bg-white/5',
      )}
    >
      {/* Top row: country + anomaly badge */}
      <div className="flex items-center gap-2">
        {flag && (
          <span className="text-sm" aria-hidden>
            {flag}
          </span>
        )}
        {item.primary_country && (
          <span className="flex items-center gap-1 text-[10px] text-subtle">
            <MapPin className="h-2.5 w-2.5" />
            {item.primary_country}
            {item.primary_region ? ` · ${item.primary_region}` : ''}
          </span>
        )}
        <div className="ml-auto">
          <AnomalyBadge score={item.anomaly_score} />
        </div>
      </div>

      {/* Title */}
      <p className="line-clamp-2 text-xs font-medium text-heading leading-snug">
        {item.title ?? '—'}
      </p>

      {/* Causal summary */}
      {item.causal_summary && (
        <p className="line-clamp-2 text-[11px] text-subtle leading-relaxed">
          <GitBranch className="mr-1 inline h-3 w-3 text-indigo-400" />
          {item.causal_summary}
        </p>
      )}

      {/* Footer: regulatory flag + trending score */}
      <div className="flex items-center gap-2 mt-0.5">
        {item.regulatory_flag && (
          <span className="flex items-center gap-1 rounded-full bg-purple-500/15 px-1.5 py-0.5 text-[10px] font-medium text-purple-400">
            <Shield className="h-2.5 w-2.5" />
            {item.regulatory_body ?? 'Regulatory'}
          </span>
        )}
        {item.causal_event_type && (
          <span className="rounded-full bg-blue-500/10 px-1.5 py-0.5 text-[10px] text-blue-400">
            {item.causal_event_type}
          </span>
        )}
        {item.trending_score != null && item.trending_score >= 0.5 && (
          <span className="ml-auto flex items-center gap-0.5 text-[10px] text-emerald-400">
            <TrendingUp className="h-2.5 w-2.5" />
            {Math.round(item.trending_score * 100)}
          </span>
        )}
      </div>
    </div>
  )
}

// ── Loading skeleton ──────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div
          key={i}
          className="h-28 rounded-lg border border-white/6 bg-white/3 animate-pulse"
        />
      ))}
    </div>
  )
}

// ── Country filter pill options ─────────────────────────────────────────────

const COUNTRY_OPTIONS = [
  { value: 'NGA', label: '🇳🇬 Nigeria' },
  { value: 'KEN', label: '🇰🇪 Kenya' },
  { value: 'GHA', label: '🇬🇭 Ghana' },
  { value: 'ZAF', label: '🇿🇦 South Africa' },
  { value: '', label: '🌍 All Africa' },
]

// ── Panel ─────────────────────────────────────────────────────────────────────

interface IntelligenceHighlightsPanelProps {
  items: IntelligenceSignalResponse[]
  loading: boolean
  error: string | null
  selectedCountry?: string
  onCountryChange?: (country: string) => void
  className?: string
}

export function IntelligenceHighlightsPanel({
  items,
  loading,
  error,
  selectedCountry = 'NGA',
  onCountryChange,
  className,
}: IntelligenceHighlightsPanelProps) {
  const [expanded, setExpanded] = useState(true)

  // Don't render if nothing interesting to show
  if (!loading && !error && items.length === 0) return null

  const displayed = items.slice(0, 8)

  return (
    <section
      className={cn(
        'rounded-xl border border-indigo-500/20 bg-indigo-500/5',
        className,
      )}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className={cn(
          'flex w-full items-center gap-3 px-4 py-3',
          'text-left transition-colors hover:bg-white/3 rounded-xl',
        )}
        aria-expanded={expanded}
      >
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-500/20">
          <TrendingUp className="h-3 w-3 text-indigo-400" />
        </span>
        <span className="text-sm font-semibold text-heading">Intelligence Highlights</span>
        {loading && (
          <Loader2 className="ml-1 h-3.5 w-3.5 animate-spin text-subtle" />
        )}
        {/* Country filter pills — stop propagation so the expand toggle isn't triggered */}
        {onCountryChange && (
          <div
            className="ml-2 flex items-center gap-1"
            onClick={(e) => e.stopPropagation()}
          >
            {COUNTRY_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => onCountryChange(opt.value)}
                className={cn(
                  'rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors',
                  selectedCountry === opt.value
                    ? 'bg-indigo-500/30 text-indigo-300'
                    : 'text-subtle hover:bg-white/5 hover:text-heading',
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        )}
        <span className="ml-auto text-subtle">
          {expanded ? (
            <ChevronUp className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
        </span>
      </button>

      {/* Content */}
      {expanded && (
        <div className="px-4 pb-4">
          {loading && <LoadingSkeleton />}
          {!loading && error && (
            <p className="text-xs text-subtle py-2">
              Intelligence feed unavailable: {error}
            </p>
          )}
          {!loading && !error && displayed.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {displayed.map((item) => (
                <IntelCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
