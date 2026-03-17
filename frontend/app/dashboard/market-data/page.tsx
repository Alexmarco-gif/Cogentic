'use client'

import { useState } from 'react'
import { BarChart3, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { MetricStatsBar } from '@/components/market-data/MetricStatsBar'
import { MetricSelector } from '@/components/market-data/MetricSelector'
import { MetricTrendChart } from '@/components/market-data/MetricTrendChart'
import { useMarketDataStats, useMetricTrend } from '@/lib/hooks/useMarketData'

const DAYS_OPTIONS = [7, 14, 30, 60, 90] as const

export default function MarketDataPage() {
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null)
  const [days, setDays] = useState<number>(30)

  const { stats, loading: statsLoading, refresh: refreshStats } = useMarketDataStats()
  const { points, loading: trendLoading, refresh: refreshTrend } = useMetricTrend(selectedMetric, { days })

  // Derive unit/currency from stats for the chart
  const metricMeta = stats?.metrics.find((m) => m.metric === selectedMetric)

  const handleRefresh = () => {
    refreshStats()
    refreshTrend()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary-light p-2">
            <BarChart3 className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-heading">Market Data</h1>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4 mr-1.5" />
          Refresh
        </Button>
      </div>

      {/* Stats bar */}
      <MetricStatsBar stats={stats} loading={statsLoading} />

      {/* Main content — Metric selector + Trend chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sidebar: metric selector */}
        <div className="lg:col-span-1">
          <MetricSelector
            metrics={stats?.metrics ?? []}
            selectedMetric={selectedMetric}
            onSelect={setSelectedMetric}
            loading={statsLoading}
          />
        </div>

        {/* Main: trend chart + controls */}
        <div className="lg:col-span-2 space-y-4">
          {/* Days toggle */}
          <div className="flex items-center gap-1">
            <span className="text-sm text-subtle mr-2">Period:</span>
            {DAYS_OPTIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                  days === d
                    ? 'bg-primary-light text-primary'
                    : 'bg-muted text-body hover:bg-border'
                }`}
              >
                {d}d
              </button>
            ))}
          </div>

          {/* Chart */}
          <MetricTrendChart
            points={points}
            loading={trendLoading}
            metric={selectedMetric}
            unit={metricMeta?.unit}
            currency={metricMeta?.currency}
          />

          {/* Latest values panel */}
          {metricMeta && (
            <div className="rounded-lg border border-border bg-surface p-4 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-subtle">Latest</span>
                <p className="font-semibold text-heading">
                  {metricMeta.currency ?? ''} {metricMeta.latest_value?.toLocaleString() ?? '—'}
                </p>
              </div>
              <div>
                <span className="text-subtle">Average</span>
                <p className="font-semibold text-heading">
                  {metricMeta.avg_value?.toLocaleString() ?? '—'}
                </p>
              </div>
              <div>
                <span className="text-subtle">Min</span>
                <p className="font-semibold text-heading">
                  {metricMeta.min_value?.toLocaleString() ?? '—'}
                </p>
              </div>
              <div>
                <span className="text-subtle">Max</span>
                <p className="font-semibold text-heading">
                  {metricMeta.max_value?.toLocaleString() ?? '—'}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
