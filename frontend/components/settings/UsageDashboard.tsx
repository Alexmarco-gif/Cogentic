'use client'

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import type { UsagePoint, PlanLimit } from '@/lib/hooks/useSettings'
import { TrendingUp, Zap, Database, Users } from 'lucide-react'

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  unit: string
  icon: React.ElementType
  color: string
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-5 shadow-card">
      <div className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl ${color}`}>
        <Icon className="h-5 w-5 text-white" strokeWidth={1.5} />
      </div>
      <div>
        <p className="text-[11px] font-medium uppercase tracking-wider text-subtle">{label}</p>
        <p className="mt-0.5 tabular-nums text-2xl font-semibold text-heading">
          {value}
          <span className="ml-1 text-sm font-normal text-subtle">{unit}</span>
        </p>
      </div>
    </div>
  )
}

// ── Limit bar ─────────────────────────────────────────────────────────────────

function LimitBar({ limit }: { limit: PlanLimit }) {
  const pct = Math.min((limit.used / limit.total) * 100, 100)
  const isWarning = pct >= 80
  const isDanger  = pct >= 95

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-body">{limit.label}</span>
        <span className="text-[11px] text-subtle">
          {limit.used.toLocaleString()} / {limit.total.toLocaleString()} {limit.unit}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all duration-700 ${
            isDanger ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-primary'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-end">
        <span className={`text-[10px] font-medium ${
          isDanger ? 'text-rose-500' : isWarning ? 'text-amber-500' : 'text-subtle'
        }`}>
          {pct.toFixed(0)}% used
        </span>
      </div>
    </div>
  )
}

// ── Custom tooltip ────────────────────────────────────────────────────────────

function CustomTooltip({ active, payload, label }: {
  active?: boolean
  payload?: { name: string; value: number; color: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-2 shadow-modal">
      <p className="mb-1.5 text-[11px] font-semibold text-heading">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 text-[11px] text-subtle">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
          {p.name}: <span className="font-medium text-body">{p.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface UsageDashboardProps {
  usageData: UsagePoint[]
  planLimits: PlanLimit[]
}

export function UsageDashboard({ usageData, planLimits }: UsageDashboardProps) {
  const latest     = usageData[usageData.length - 1]
  const prev       = usageData[usageData.length - 2]
  const creditsDelta = latest && prev ? latest.credits - prev.credits : 0

  return (
    <div className="flex flex-col gap-8">
      {/* ── Summary stat cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Credits this month" value={latest?.credits.toLocaleString() ?? '—'} unit="cr" icon={Zap}        color="bg-primary"           />
        <StatCard label="API calls"           value={latest?.apiCalls.toLocaleString() ?? '—'} unit="calls" icon={TrendingUp} color="bg-emerald-500"     />
        <StatCard label="Active contracts"    value="4"   unit="active"  icon={Database}  color="bg-amber-500"         />
        <StatCard label="Team members"        value="2"   unit="seats"   icon={Users}     color="bg-violet-500"        />
      </div>

      {/* ── Area chart ────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-heading">Usage over time</h3>
            <p className="mt-0.5 text-xs text-subtle">Credits and API calls — last 6 months</p>
          </div>
          {creditsDelta !== 0 && (
            <span className={`text-xs font-medium ${creditsDelta > 0 ? 'text-rose-500' : 'text-emerald-600'}`}>
              {creditsDelta > 0 ? '↑' : '↓'} {Math.abs(creditsDelta).toLocaleString()} credits vs prev month
            </span>
          )}
        </div>

        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={usageData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="creditsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#4F46E5" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#4F46E5" stopOpacity={0}    />
              </linearGradient>
              <linearGradient id="apiGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#059669" stopOpacity={0.12} />
                <stop offset="95%" stopColor="#059669" stopOpacity={0}    />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '16px' }} />
            <Area type="monotone" dataKey="credits"  name="Credits"   stroke="#4F46E5" strokeWidth={2} fill="url(#creditsGrad)" dot={false} activeDot={{ r: 4 }} />
            <Area type="monotone" dataKey="apiCalls" name="API calls" stroke="#059669" strokeWidth={2} fill="url(#apiGrad)"     dot={false} activeDot={{ r: 4 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* ── Plan limits ───────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Plan Limits</h3>
        <p className="mb-5 text-xs text-subtle">Growth Plan — renews Feb 28, 2026</p>
        <div className="flex flex-col gap-5">
          {planLimits.map(limit => <LimitBar key={limit.label} limit={limit} />)}
        </div>
      </div>
    </div>
  )
}
