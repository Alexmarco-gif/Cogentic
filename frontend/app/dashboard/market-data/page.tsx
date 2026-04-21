'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { AlertTriangle, BarChart3, Compass, LineChart, RefreshCw, ShieldCheck } from 'lucide-react'
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
  const { hasAccess, loading: featureLoading, resolved: featureResolved } = useFeatureGate('market_data')
  const canUsePremiumMetrics = !featureResolved || hasAccess

  const {
    stats,
    loading: statsLoading,
    error: statsError,
    refresh: refreshStats,
  } = useMarketDataStats(undefined, { enabled: canUsePremiumMetrics })
  const {
    points,
    loading: trendLoading,
    error: trendError,
    refresh: refreshTrend,
  } = useMetricTrend(selectedMetric, { days, enabled: canUsePremiumMetrics })

  const metricMeta = stats?.metrics.find((metric) => metric.metric === selectedMetric)
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
    if (!canUsePremiumMetrics) {
      return
    }
    void refreshStats()
    void refreshTrend()
  }

  if (featureLoading) {
    return (
      <div className="space-y-6 px-3 py-4 sm:px-4 lg:px-0">
        <div className="h-12 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-lg border border-border bg-surface" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1280px] space-y-6 px-3 py-4 sm:px-4 lg:px-0">
      <div className="surface-panel flex flex-col gap-4 p-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-primary-light p-2">
            <BarChart3 className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-heading">Market Data</h1>
            <p className="text-sm text-subtle">
              Monitor tracked indicators, follow trend changes, and jump into adjacent workspaces when you need deeper context.
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} disabled={!canUsePremiumMetrics}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {featureResolved && !hasAccess && (
        <>
          <div className="rounded-2xl border border-border bg-surface p-6">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
              <div className="max-w-2xl">
                <div className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Starter access is active
                </div>
                <h2 className="mt-3 text-lg font-semibold text-heading">Keep using the workspace while premium metrics stay optional</h2>
                <p className="mt-2 text-sm text-subtle">
                  Signals, discovery, briefs, and source research stay available. Historical indicator charts and tracked market metrics unlock when Market Data access is enabled.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2 lg:w-[420px]">
                <Link href="/dashboard/signals" className="rounded-xl border border-border bg-muted/40 p-4 transition-colors hover:bg-muted">
                  <div className="flex items-center gap-2 text-sm font-medium text-heading">
                    <Compass className="h-4 w-4 text-primary" />
                    Open Signals
                  </div>
                  <p className="mt-2 text-xs text-subtle">Follow active signal cards and intelligence updates from the main feed.</p>
                </Link>
                <Link href="/dashboard/marketplace" className="rounded-xl border border-border bg-muted/40 p-4 transition-colors hover:bg-muted">
                  <div className="flex items-center gap-2 text-sm font-medium text-heading">
                    <LineChart className="h-4 w-4 text-primary" />
                    Browse Sources
                  </div>
                  <p className="mt-2 text-xs text-subtle">Explore data and source packs before deciding which indicators deserve tracked coverage.</p>
                </Link>
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm font-medium text-heading">What unlocks here</p>
              <p className="mt-2 text-sm text-subtle">Indicator history, trend charts, and workspace-level metric tracking for operational decisions.</p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm font-medium text-heading">What you can do now</p>
              <p className="mt-2 text-sm text-subtle">Keep using Signals, Discovery, Library, and Marketplace without any interruption.</p>
            </div>
            <div className="rounded-xl border border-border bg-surface p-5">
              <p className="text-sm font-medium text-heading">Best next step</p>
              <p className="mt-2 text-sm text-subtle">Investigate live signals first, then expand into Market Data once you know which indicators matter most.</p>
            </div>
          </div>
        </>
      )}

      {combinedError && (
        <div className="flex flex-col gap-3 rounded-lg border border-rose-200 bg-rose-50 p-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-2 text-sm text-rose-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-600" />
            <span>{combinedError}</span>
          </div>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={!canUsePremiumMetrics}>
            Try again
          </Button>
        </div>
      )}

      {canUsePremiumMetrics ? (
        <>
          <MetricStatsBar stats={stats} loading={statsLoading} />

          {!statsLoading && (!stats || stats.metrics.length === 0) && !combinedError && (
            <div className="rounded-lg border border-border bg-surface p-6 text-center">
              <h2 className="text-base font-semibold text-heading">No market metrics yet</h2>
              <p className="mt-2 text-sm text-subtle">
                Market data appears here after tracked indicators are ingested for your workspace. Activate the right managed sources first, then return once the first metrics have been collected.
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-3">
                <Link href="/dashboard/marketplace" className="rounded-full bg-primary px-4 py-2 text-xs font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover">
                  Browse sources
                </Link>
                <Link href="/dashboard/signals" className="rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold text-heading transition-colors hover:bg-muted">
                  Open Signals
                </Link>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(18rem,0.72fr)_minmax(0,1.28fr)]">
            <div className="min-w-0">
              <MetricSelector
                metrics={stats?.metrics ?? []}
                selectedMetric={selectedMetric}
                onSelect={setSelectedMetric}
                loading={statsLoading}
              />
            </div>

            <div className="min-w-0 space-y-4">
              <div className="surface-panel flex flex-wrap items-center gap-2 p-4">
                <span className="mr-2 text-sm text-subtle">Period:</span>
                {DAYS_OPTIONS.map((value) => (
                  <button
                    key={value}
                    onClick={() => setDays(value)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                      days === value
                        ? 'bg-primary-light text-primary'
                        : 'bg-muted text-body hover:bg-border'
                    }`}
                  >
                    {value}d
                  </button>
                ))}
              </div>

              <MetricTrendChart
                points={points}
                loading={trendLoading}
                metric={selectedMetric}
                unit={metricMeta?.unit}
                currency={metricMeta?.currency}
              />

              {metricMeta && (
                <div className="grid grid-cols-2 gap-4 rounded-lg border border-border bg-surface p-4 text-sm md:grid-cols-4">
                  <div>
                    <span className="text-subtle">Latest</span>
                    <p className="font-semibold text-heading">
                      {metricMeta.currency ?? ''} {metricMeta.latest_value?.toLocaleString() ?? '-'}
                    </p>
                  </div>
                  <div>
                    <span className="text-subtle">Average</span>
                    <p className="font-semibold text-heading">
                      {metricMeta.avg_value?.toLocaleString() ?? '-'}
                    </p>
                  </div>
                  <div>
                    <span className="text-subtle">Min</span>
                    <p className="font-semibold text-heading">
                      {metricMeta.min_value?.toLocaleString() ?? '-'}
                    </p>
                  </div>
                  <div>
                    <span className="text-subtle">Max</span>
                    <p className="font-semibold text-heading">
                      {metricMeta.max_value?.toLocaleString() ?? '-'}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
