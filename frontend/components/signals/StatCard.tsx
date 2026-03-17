'use client'

import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'
import type { ReactNode } from 'react'

interface StatCardProps {
  icon: ReactNode
  label: string
  value: string
  sub?: string
  change?: string
  positive?: boolean
  /** sparkline or mini-chart below value */
  chart?: ReactNode
  accent?: string // tailwind bg class for icon bg
}

export function StatCard({
  icon,
  label,
  value,
  sub,
  change,
  positive,
  chart,
  accent = 'bg-primary/10',
}: StatCardProps) {
  return (
    <div className="bg-surface border border-border rounded-card shadow-card p-5 flex flex-col gap-3 min-w-0">
      {/* Top row */}
      <div className="flex items-start justify-between">
        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center shrink-0', accent)}>
          {icon}
        </div>
        {change && (
          <span
            className={cn(
              'flex items-center gap-0.5 text-[12px] font-medium',
              positive ? 'text-emerald-600' : 'text-red-500',
            )}
          >
            {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {change}
          </span>
        )}
      </div>

      {/* Value */}
      <div>
        <p className="text-[11px] text-subtle mb-0.5">{label}</p>
        <p className="text-[22px] font-medium text-heading leading-none tabular-nums">{value}</p>
        {sub && <p className="text-[11px] text-subtle mt-1">{sub}</p>}
      </div>

      {/* Optional chart slot */}
      {chart && <div className="mt-auto">{chart}</div>}
    </div>
  )
}
