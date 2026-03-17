'use client'

/**
 * MetricTrendChart — Recharts line chart for a single metric over time.
 *
 * Renders a responsive time-series line chart with tooltip and axis formatting.
 */

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { MarketDataPointResponse } from '@/lib/api/types'

interface MetricTrendChartProps {
  points: MarketDataPointResponse[]
  loading: boolean
  metric: string | null
  unit?: string | null
  currency?: string | null
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

function formatValue(v: number, currency?: string | null): string {
  if (currency) {
    return `${currency} ${v.toLocaleString()}`
  }
  return v.toLocaleString()
}

export function MetricTrendChart({
  points,
  loading,
  metric,
  unit,
  currency,
}: MetricTrendChartProps) {
  if (loading) {
    return (
      <div className="h-[320px] flex items-center justify-center bg-gray-50 rounded-lg border animate-pulse">
        <span className="text-gray-400">Loading trend...</span>
      </div>
    )
  }

  if (!metric) {
    return (
      <div className="h-[320px] flex items-center justify-center bg-gray-50 rounded-lg border">
        <span className="text-gray-400">Select a metric to view its trend</span>
      </div>
    )
  }

  if (points.length === 0) {
    return (
      <div className="h-[320px] flex items-center justify-center bg-gray-50 rounded-lg border">
        <span className="text-gray-400">No data available for &ldquo;{metric.replace(/_/g, ' ')}&rdquo;</span>
      </div>
    )
  }

  const chartData = points.map((p) => ({
    date: formatDate(p.observed_at),
    fullDate: p.observed_at,
    value: p.value,
    context: p.context,
  }))

  return (
    <div className="rounded-lg border bg-white p-4">
      <div className="mb-3 flex items-baseline gap-2">
        <h3 className="text-sm font-medium text-gray-900 capitalize">
          {metric.replace(/_/g, ' ')}
        </h3>
        {unit && <span className="text-xs text-gray-500">({unit})</span>}
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickMargin={8}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => v.toLocaleString()}
            width={70}
          />
          <Tooltip
            formatter={(value) => {
              const numericValue = typeof value === 'number' ? value : Number(value ?? 0)
              return [formatValue(numericValue, currency), 'Value']
            }}
            labelFormatter={(_, payload) => {
              if (payload?.[0]?.payload?.fullDate) {
                return new Date(payload[0].payload.fullDate).toLocaleString()
              }
              return ''
            }}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
