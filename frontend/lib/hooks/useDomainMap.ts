'use client'

import { useState, useMemo, useCallback, useEffect } from 'react'
import { getSignalRegions } from '@/lib/api/signals'
import { friendlyErrorMessage } from '@/lib/api'

// ── Region type (generic — works for any country) ─────────────────────────────

export type RiskLevel = 'critical' | 'elevated' | 'moderate' | 'stable'

/**
 * Renamed from NigeriaRegion → MapRegion.
 * The old name is re-exported below for backward compat while consumers migrate.
 */
export interface MapRegion {
  id: string
  name: string
  /** State / province / sub-national division */
  state: string
  lat: number
  lng: number
  signalCount: number
  severity: 'critical' | 'high' | 'medium' | 'low'
  domains: string[]
  topSignal: string
  topSignalId?: string | null
  riskLevel: RiskLevel
  opportunityScore: number // 0–100
  summary: string
}

/** @deprecated — use MapRegion instead */
export type NigeriaRegion = MapRegion

// ── Layer config ──────────────────────────────────────────────────────────────

export interface DomainLayers {
  riskHeatmap: boolean
  opportunities: boolean
  signalDensity: boolean
}

// ── Risk level colours ────────────────────────────────────────────────────────

export const RISK_LEVEL_STYLES: Record<RiskLevel, string> = {
  critical: 'bg-red-500/15 text-red-400 border-red-500/25',
  elevated: 'bg-orange-500/15 text-orange-400 border-orange-500/25',
  moderate: 'bg-amber-500/15 text-amber-400 border-amber-500/25',
  stable:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/25',
}

// ── API helpers ───────────────────────────────────────────────────────────────

/**
 * Fetch region intelligence from the backend.
 * Falls back to an empty array when the endpoint is unavailable.
 */
const DOMAIN_LABELS: Record<string, string> = {
  financial: 'Finance',
  regulatory: 'Regulatory',
  market: 'Market',
  technology: 'Technology',
  news: 'News',
  social: 'Social',
}

function toDomainLabel(domain: string): string {
  if (!domain) return 'General'
  return DOMAIN_LABELS[domain.toLowerCase()] ?? domain
}

function normalizeRegion(raw: unknown): MapRegion {
  const region = (raw ?? {}) as Record<string, unknown>
  const domains = Array.isArray(region.domains)
    ? Array.from(
        new Set(
          region.domains
            .filter((value): value is string => typeof value === 'string')
            .map(toDomainLabel),
        ),
      )
    : []

  return {
    id: String(region.id ?? ''),
    name: String(region.name ?? region.state ?? 'Unknown'),
    state: String(region.state ?? region.name ?? 'Unknown'),
    lat: Number(region.lat ?? 0),
    lng: Number(region.lng ?? 0),
    signalCount: Number(region.signalCount ?? 0),
    severity: (region.severity as MapRegion['severity']) ?? 'low',
    domains,
    topSignal: String(region.topSignal ?? ''),
    topSignalId: typeof region.topSignalId === 'string' ? region.topSignalId : null,
    riskLevel: (region.riskLevel as RiskLevel) ?? 'stable',
    opportunityScore: Number(region.opportunityScore ?? 0),
    summary: String(region.summary ?? ''),
  }
}

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useDomainMap() {
  const [activeDomain, setActiveDomain] = useState<string>('All')
  const [layers, setLayers] = useState<DomainLayers>({
    riskHeatmap: true,
    opportunities: false,
    signalDensity: true,
  })
  const [activeRegion, setActiveRegion] = useState<MapRegion | null>(null)
  const [allRegions, setAllRegions] = useState<MapRegion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch regions on mount
  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getSignalRegions()
      setAllRegions(Array.isArray(data) ? data.map(normalizeRegion) : [])
    } catch (err) {
      setAllRegions([])
      setError(friendlyErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const filteredRegions = useMemo(() => {
    if (activeDomain === 'All') return allRegions
    return allRegions.filter((r) => r.domains.includes(activeDomain))
  }, [activeDomain, allRegions])

  const toggleLayer = useCallback((key: keyof DomainLayers) => {
    setLayers((prev) => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const selectRegion = useCallback((region: MapRegion | null) => {
    setActiveRegion(region)
  }, [])

  // Summary counts
  const criticalCount = filteredRegions.filter((r) => r.severity === 'critical').length
  const totalSignals = filteredRegions.reduce((sum, r) => sum + r.signalCount, 0)
  const availableDomains = useMemo(
    () => Array.from(new Set(allRegions.flatMap((region) => region.domains))).sort(),
    [allRegions],
  )

  return {
    activeDomain,
    setActiveDomain,
    layers,
    toggleLayer,
    activeRegion,
    selectRegion,
    filteredRegions,
    allRegions,
    availableDomains,
    loading,
    error,
    criticalCount,
    totalSignals,
    refresh,
  }
}
