'use client'

import { useMemo } from 'react'
import {
  AreaChart,
  Area,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Activity, AlertTriangle, Clock3, ShieldCheck, Wallet } from 'lucide-react'

import type {
  CreditBalanceResponse,
  CreditTransactionResponse,
} from '@/lib/api/types'

function StatCard({
  label,
  value,
  sublabel,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  sublabel: string
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
        <p className="mt-0.5 text-2xl font-semibold tabular-nums text-heading">{value}</p>
        <p className="text-xs text-subtle">{sublabel}</p>
      </div>
    </div>
  )
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null

  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-2 shadow-modal">
      <p className="mb-1.5 text-[11px] font-semibold text-heading">{label}</p>
      {payload.map((item) => (
        <div key={item.name} className="flex items-center gap-2 text-[11px] text-subtle">
          <span className="h-2 w-2 rounded-full" style={{ background: item.color }} />
          {item.name}: <span className="font-medium text-body">{item.value.toLocaleString()}</span>
        </div>
      ))}
    </div>
  )
}

function actionLabel(actionType: string) {
  return actionType
    .split('_')
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function formatTimestamp(value: string) {
  const date = new Date(value)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function buildUsageSeries(transactions: CreditTransactionResponse[]) {
  const grouped = new Map<string, { label: string; credits: number; actions: number }>()

  const sorted = [...transactions].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  )

  for (const txn of sorted) {
    const date = new Date(txn.created_at)
    const key = date.toISOString().slice(0, 10)
    const label = new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
    }).format(date)

    const existing = grouped.get(key) ?? { label, credits: 0, actions: 0 }
    existing.credits += txn.credits_consumed
    existing.actions += 1
    grouped.set(key, existing)
  }

  const series = Array.from(grouped.values()).slice(-7)
  if (series.length > 0) return series

  return [{ label: 'Today', credits: 0, actions: 0 }]
}

interface UsageDashboardProps {
  creditBalance: CreditBalanceResponse | null
  creditTransactions: CreditTransactionResponse[]
  loading?: boolean
}

export function UsageDashboard({
  creditBalance,
  creditTransactions,
  loading = false,
}: UsageDashboardProps) {
  const balance = creditBalance ?? {
    allocated: 0,
    consumed: 0,
    remaining: 0,
    overage: 0,
    overage_rate: 0,
    strict_prepaid_enabled: true,
  }

  const usageSeries = useMemo(
    () => buildUsageSeries(creditTransactions),
    [creditTransactions],
  )

  const recentTransactions = useMemo(
    () =>
      [...creditTransactions]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 8),
    [creditTransactions],
  )

  const usedPercent = balance.allocated > 0
    ? Math.min((balance.consumed / balance.allocated) * 100, 100)
    : 0
  const creditsExhausted = balance.remaining <= 0
  const creditsRunningLow = !creditsExhausted && balance.remaining <= 100

  return (
    <div className="flex flex-col gap-8">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4 md:grid-cols-2">
        <StatCard
          label="Monthly Credits"
          value={balance.allocated.toLocaleString()}
          sublabel="Allocated this billing cycle"
          icon={Wallet}
          color="bg-primary"
        />
        <StatCard
          label="Credits Used"
          value={balance.consumed.toLocaleString()}
          sublabel={`${usedPercent.toFixed(0)}% of allocation consumed`}
          icon={Activity}
          color="bg-amber-500"
        />
        <StatCard
          label="Credits Remaining"
          value={balance.remaining.toLocaleString()}
          sublabel="Hard blocking starts at zero"
          icon={ShieldCheck}
          color="bg-emerald-500"
        />
        <StatCard
          label="Recent Actions"
          value={recentTransactions.length.toLocaleString()}
          sublabel="Latest billable events shown below"
          icon={Clock3}
          color="bg-sky-500"
        />
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <div>
            <h3 className="text-sm font-medium text-heading">Credit Usage</h3>
            <p className="mt-0.5 text-xs text-subtle">
              Recent credit spend and billable activity from your organization.
            </p>
          </div>
          <div className="rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-medium text-emerald-700">
            Strict prepaid active
          </div>
        </div>

        {creditsExhausted && (
          <div className="mb-5 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <div>
                <p className="font-semibold">You are out of credits.</p>
                <p className="mt-1 text-amber-800">
                  New paid actions are blocked until your monthly credits renew or your plan is upgraded.
                </p>
              </div>
            </div>
          </div>
        )}

        {creditsRunningLow && (
          <div className="mb-5 rounded-xl border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm text-amber-900">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <div>
                <p className="font-semibold">Credits are running low.</p>
                <p className="mt-1 text-amber-800">
                  You have {balance.remaining.toLocaleString()} credits left before paid actions are blocked.
                </p>
              </div>
            </div>
          </div>
        )}

        <div className="mb-6">
          <div className="mb-2 flex items-center justify-between text-xs text-subtle">
            <span>Credits used</span>
            <span>
              {balance.consumed.toLocaleString()} / {balance.allocated.toLocaleString()}
            </span>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={`h-full rounded-full transition-all duration-700 ${
                usedPercent >= 95 ? 'bg-rose-500' : usedPercent >= 80 ? 'bg-amber-500' : 'bg-primary'
              }`}
              style={{ width: `${usedPercent}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-subtle">
            Overage is disabled. New paid actions are blocked once no credits remain.
          </p>
        </div>

        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={usageSeries} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="creditsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563EB" stopOpacity={0.18} />
                <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="actionsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#059669" stopOpacity={0.12} />
                <stop offset="95%" stopColor="#059669" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="credits"
              name="Credits spent"
              stroke="#2563EB"
              strokeWidth={2}
              fill="url(#creditsGrad)"
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Area
              type="monotone"
              dataKey="actions"
              name="Billable actions"
              stroke="#059669"
              strokeWidth={2}
              fill="url(#actionsGrad)"
              dot={false}
              activeDot={{ r: 4 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-4">
          <h3 className="text-sm font-medium text-heading">Recent Credit Activity</h3>
          <p className="mt-0.5 text-xs text-subtle">
            Each entry shows what spent credits and how many remained immediately after.
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-subtle">Loading credit activity…</p>
        ) : recentTransactions.length === 0 ? (
          <p className="text-sm text-subtle">No credit transactions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-border text-xs uppercase tracking-wide text-subtle">
                <tr>
                  <th className="pb-3 pr-4 font-medium">Action</th>
                  <th className="pb-3 pr-4 font-medium">Spent</th>
                  <th className="pb-3 pr-4 font-medium">Remaining</th>
                  <th className="pb-3 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {recentTransactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-border/70 last:border-0">
                    <td className="py-3 pr-4">
                      <div className="font-medium text-body">{actionLabel(txn.action_type)}</div>
                    </td>
                    <td className="py-3 pr-4 tabular-nums text-rose-600">
                      -{txn.credits_consumed.toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 tabular-nums text-body">
                      {txn.credits_remaining.toLocaleString()}
                    </td>
                    <td className="py-3 text-subtle">{formatTimestamp(txn.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
