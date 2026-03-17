'use client'

/**
 * MetricStatsBar — top-level aggregate stats for market data dashboard.
 *
 * Shows card grid: Total Data Points, Unique Metrics, Countries Tracked,
 * plus a highlighted metric summary card.
 */

import { Database, BarChart3, Globe, TrendingUp } from 'lucide-react'
import type { MarketDataStatsResponse } from '@/lib/api/types'

interface MetricStatsBarProps {
  stats: MarketDataStatsResponse | null
  loading: boolean
}

const STAT_CARDS = [
  { key: 'total_points',     label: 'Data Points',  icon: Database,    color: 'text-blue-600   bg-blue-50' },
  { key: 'unique_metrics',   label: 'Metrics',      icon: BarChart3,   color: 'text-emerald-600 bg-emerald-50' },
  { key: 'countries_covered', label: 'Countries',    icon: Globe,       color: 'text-amber-600  bg-amber-50' },
] as const

export function MetricStatsBar({ stats, loading }: MetricStatsBarProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="rounded-lg border bg-white p-4 animate-pulse">
            <div className="h-4 w-20 bg-gray-200 rounded mb-2" />
            <div className="h-8 w-16 bg-gray-200 rounded" />
          </div>
        ))}
      </div>
    )
  }

  const topMetric = stats?.metrics?.[0]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {STAT_CARDS.map(({ key, label, icon: Icon, color }) => (
        <div key={key} className="rounded-lg border bg-white p-4">
          <div className="flex items-center gap-2 mb-1">
            <div className={`rounded-md p-1.5 ${color}`}>
              <Icon className="h-4 w-4" />
            </div>
            <span className="text-sm text-gray-500">{label}</span>
          </div>
          <p className="text-2xl font-semibold text-gray-900">
            {stats ? (stats[key as keyof MarketDataStatsResponse] as number).toLocaleString() : '—'}
          </p>
        </div>
      ))}

      {/* Top metric card */}
      <div className="rounded-lg border bg-white p-4">
        <div className="flex items-center gap-2 mb-1">
          <div className="rounded-md p-1.5 text-violet-600 bg-violet-50">
            <TrendingUp className="h-4 w-4" />
          </div>
          <span className="text-sm text-gray-500">Top Metric</span>
        </div>
        {topMetric ? (
          <div>
            <p className="text-lg font-semibold text-gray-900 truncate">
              {topMetric.metric.replace(/_/g, ' ')}
            </p>
            <p className="text-xs text-gray-500">
              {topMetric.count} points · latest {topMetric.latest_value?.toLocaleString()} {topMetric.unit ?? ''}
            </p>
          </div>
        ) : (
          <p className="text-2xl font-semibold text-gray-400">—</p>
        )}
      </div>
    </div>
  )
}
