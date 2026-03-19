'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, BarChart3, Lock, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { MetricStatsBar } from '@/components/market-data/MetricStatsBar'
import { MetricSelector } from '@/components/market-data/MetricSelector'
import { MetricTrendChart } from '@/components/market-data/MetricTrendChart'
import { useFeatureGate } from '@/lib/hooks/useFeatureGate'
import { useMarketDataStats, useMetricTrend } from '@/lib/hooks/useMarketData'

const DAYS_OPTIONS = [7, 14, 30, 60, 90] as const

export default function MarketDataPage() {
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null)
  const [days, setDays] = useState<number>(30)
  const { hasAccess, loading: featureLoading, currentTier } = useFeatureGate('market_data')

  const {
    stats,
    loading: statsLoading,
    error: statsError,
    refresh: refreshStats,
  } = useMarketDataStats()
  const {
    points,
    loading: trendLoading,
    error: trendError,
    refresh: refreshTrend,
  } = useMetricTrend(selectedMetric, { days })

  // Derive unit/currency from stats for the chart
  const metricMeta = stats?.metrics.find((m) => m.metric === selectedMetric)
  const combinedError = statsError ?? trendError

  useEffect(() => {
    if (!stats?.metrics?.length) {
      if (selectedMetric) {
        setSelectedMetric(null)
      }
      return
    }

    const metricStillVisible = stats.metrics.some((metric) => metric.metric === selectedMetric)
    if (!selectedMetric || !metricStillVisible) {
      setSelectedMetric(stats.metrics[0]?.metric ?? null)
    }
  }, [selectedMetric, stats])

  const handleRefresh = () => {
    void refreshStats()
    void refreshTrend()
  }

  if (featureLoading) {
    return (
      <div className="space-y-6">
        <div className="h-12 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-lg border border-border bg-surface" />
          ))}
        </div>
      </div>
    )
  }

  if (!hasAccess) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary-light p-2">
            <BarChart3 className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-heading">Market Data</h1>
            <p className="text-sm text-subtle">
              Track prices, rates, and indicator trends once Market Data access is enabled.
            </p>
          </div>
        </div>

        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="flex items-start gap-3">
              <div className="rounded-full bg-amber-100 p-2 text-amber-700">
                <Lock className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-amber-950">Market Data is on a paid plan</h2>
                <p className="mt-1 text-sm text-amber-900">
                  Your current tier is <span className="font-semibold capitalize">{currentTier}</span>. You can
                  still use Signals, Discovery, and the Library while this premium dashboard stays gated.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => { window.location.href = '/dashboard/signals' }}>
                Open Signals
              </Button>
              <Button size="sm" onClick={() => { window.location.href = '/dashboard/marketplace' }}>
                Browse Marketplace
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
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

      {combinedError && (
        <div className="flex flex-col gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-2 text-sm text-rose-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <span>{combinedError}</span>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh}>
            Try again
          </Button>
        </div>
      )}

      {/* Stats bar */}
      <MetricStatsBar stats={stats} loading={statsLoading} />

      {!statsLoading && (!stats || stats.metrics.length === 0) && !combinedError && (
        <div className="rounded-lg border border-border bg-surface p-6 text-center">
          <h2 className="text-base font-semibold text-heading">No market metrics yet</h2>
          <p className="mt-2 text-sm text-subtle">
            Market data will appear here after tracked indicators are ingested for your workspace.
          </p>
        </div>
      )}

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
