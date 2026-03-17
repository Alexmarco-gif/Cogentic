'use client'

/**
 * MetricSelector — searchable dropdown for picking a metric to chart.
 *
 * Also shows a summary table of all tracked metrics with latest values.
 */

import { useState } from 'react'
import { Search, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { MetricSummary } from '@/lib/api/types'

interface MetricSelectorProps {
  metrics: MetricSummary[]
  selectedMetric: string | null
  onSelect: (metric: string) => void
  loading: boolean
}

function trendIcon(metric: MetricSummary) {
  if (metric.latest_value == null || metric.avg_value == null) {
    return <Minus className="h-3.5 w-3.5 text-gray-400" />
  }
  if (metric.latest_value > metric.avg_value * 1.02) {
    return <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
  }
  if (metric.latest_value < metric.avg_value * 0.98) {
    return <TrendingDown className="h-3.5 w-3.5 text-red-500" />
  }
  return <Minus className="h-3.5 w-3.5 text-gray-400" />
}

export function MetricSelector({
  metrics,
  selectedMetric,
  onSelect,
  loading,
}: MetricSelectorProps) {
  const [search, setSearch] = useState('')

  const filtered = metrics.filter((m) =>
    m.metric.toLowerCase().includes(search.toLowerCase()),
  )

  if (loading) {
    return (
      <div className="rounded-lg border bg-white p-4">
        <div className="h-8 w-40 bg-gray-200 rounded animate-pulse mb-3" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-10 bg-gray-100 rounded mb-2 animate-pulse" />
        ))}
      </div>
    )
  }

  if (metrics.length === 0) {
    return (
      <div className="rounded-lg border bg-white p-6 text-center">
        <p className="text-gray-500 text-sm">No metrics tracked yet</p>
        <p className="text-gray-400 text-xs mt-1">
          Market data will appear once signals are processed through NER
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-white">
      {/* Search */}
      <div className="p-3 border-b">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search metrics..."
            className="w-full pl-9 pr-3 py-2 text-sm border rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Metric list */}
      <div className="max-h-[420px] overflow-y-auto divide-y">
        {filtered.map((m) => (
          <button
            key={m.metric}
            onClick={() => onSelect(m.metric)}
            className={`w-full text-left px-3 py-2.5 flex items-center justify-between hover:bg-gray-50 transition-colors ${
              selectedMetric === m.metric ? 'bg-indigo-50 border-l-2 border-indigo-500' : ''
            }`}
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 truncate capitalize">
                {m.metric.replace(/_/g, ' ')}
              </p>
              <p className="text-xs text-gray-500">
                {m.count} points · {m.unit ?? ''}
              </p>
            </div>
            <div className="flex items-center gap-2 ml-2 shrink-0">
              {trendIcon(m)}
              <span className="text-sm font-mono text-gray-700">
                {m.latest_value?.toLocaleString() ?? '—'}
              </span>
            </div>
          </button>
        ))}
        {filtered.length === 0 && (
          <div className="p-4 text-center text-gray-400 text-sm">
            No metrics match &ldquo;{search}&rdquo;
          </div>
        )}
      </div>
    </div>
  )
}
