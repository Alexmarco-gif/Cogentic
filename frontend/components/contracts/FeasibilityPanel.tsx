'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import type { FeasibilityPoint } from '@/lib/hooks/useContractStudio'

// ── Custom tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: { name: string; value: number; color: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-border bg-surface p-3 shadow-modal">
      <p className="mb-2 text-[11px] font-semibold text-heading">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 text-[11px]">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          <span className="text-subtle capitalize">{p.name}</span>
          <span className="ml-auto font-medium text-heading">{p.value.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface FeasibilityPanelProps {
  data: FeasibilityPoint[]
  className?: string
}

export function FeasibilityPanel({ data, className = '' }: FeasibilityPanelProps) {
  if (data.length === 0) return null

  const avgAvailability = Math.round(data.reduce((a, b) => a + b.availability, 0) / data.length)
  const avgQuality      = Math.round(data.reduce((a, b) => a + b.quality, 0) / data.length)
  const avgCoverage     = Math.round(data.reduce((a, b) => a + b.coverage, 0) / data.length)

  const grade =
    avgAvailability >= 80 && avgQuality >= 75 ? 'High'
    : avgAvailability >= 60 ? 'Medium'
    : 'Low'

  const gradeColor =
    grade === 'High'   ? 'text-emerald-600 bg-emerald-50 border-emerald-200'
    : grade === 'Medium' ? 'text-amber-600 bg-amber-50 border-amber-200'
    : 'text-rose-600 bg-rose-50 border-rose-200'

  return (
    <div className={`flex flex-col gap-4 ${className}`}>
      {/* Summary stat row */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Data Availability', value: `${avgAvailability}%`, sub: 'across 12 months' },
          { label: 'Source Quality',    value: `${avgQuality}%`,      sub: 'weighted avg' },
          { label: 'Geo Coverage',      value: `${avgCoverage}%`,     sub: 'of target region' },
          { label: 'Feasibility Grade', value: grade,                 sub: 'overall signal', badge: true, badgeClass: gradeColor },
        ].map(s => (
          <div key={s.label} className="rounded-xl border border-border bg-surface p-3">
            <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-subtle">{s.label}</p>
            {s.badge ? (
              <span className={`inline-flex items-center rounded-pill border px-2 py-0.5 text-sm font-medium ${s.badgeClass}`}>
                {s.value}
              </span>
            ) : (
              <p className="text-[22px] font-light tracking-tight text-heading">{s.value}</p>
            )}
            <p className="mt-0.5 text-[9px] text-subtle">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 12, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 10, fill: 'var(--color-subtle)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: 'var(--color-subtle)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              iconSize={8}
              wrapperStyle={{ fontSize: '10px', color: 'var(--color-subtle)' }}
            />
            <Line
              type="monotone"
              dataKey="availability"
              stroke="#4F46E5"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#4F46E5' }}
            />
            <Line
              type="monotone"
              dataKey="quality"
              stroke="#059669"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#059669' }}
            />
            <Line
              type="monotone"
              dataKey="coverage"
              stroke="#D97706"
              strokeWidth={2}
              strokeDasharray="5 3"
              dot={false}
              activeDot={{ r: 4, fill: '#D97706' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
