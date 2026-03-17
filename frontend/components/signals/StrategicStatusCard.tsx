'use client'

import { cn } from '@/lib/utils'
import {
  ShieldAlert,
  Lightbulb,
  AlertTriangle,
  Search,
  Radio,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
} from 'lucide-react'
import type { StrategicStatus, StatusLevel } from '@/lib/hooks/useSignals'

// ── Level styling ────────────────────────────────────────────────────────────
const LEVEL_CONFIG: Record<StatusLevel, {
  barColor: string
  bgColor: string
  textColor: string
  label: string
}> = {
  critical: {
    barColor: 'bg-red-500',
    bgColor:  'bg-red-500/8',
    textColor: 'text-red-600',
    label: 'Critical',
  },
  elevated: {
    barColor: 'bg-amber-500',
    bgColor:  'bg-amber-500/8',
    textColor: 'text-amber-600',
    label: 'Elevated',
  },
  moderate: {
    barColor: 'bg-blue-500',
    bgColor:  'bg-blue-500/8',
    textColor: 'text-blue-600',
    label: 'Moderate',
  },
  stable: {
    barColor: 'bg-emerald-500',
    bgColor:  'bg-emerald-500/8',
    textColor: 'text-emerald-600',
    label: 'Stable',
  },
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  'risks':           <ShieldAlert  size={15} />,
  'opportunities':   <Lightbulb    size={15} />,
  'critical-alerts': <AlertTriangle size={15} />,
  'investigations':  <Search       size={15} />,
  'signals-today':   <Radio        size={15} />,
}

const TREND_ICONS: Record<string, React.ReactNode> = {
  up:   <TrendingUp   size={11} />,
  down: <TrendingDown size={11} />,
  flat: <Minus        size={11} />,
}

interface StrategicStatusCardProps {
  status: StrategicStatus
  loading?: boolean
  onClick?: () => void
}

export function StrategicStatusCard({ status, loading, onClick }: StrategicStatusCardProps) {
  const config = LEVEL_CONFIG[status.level]

  if (loading) {
    return (
      <div className="bg-surface border border-border rounded-card shadow-card p-5 space-y-3 animate-pulse">
        <div className="h-4 bg-muted rounded w-1/2" />
        <div className="h-8 bg-muted rounded w-1/3" />
        <div className="h-3 bg-muted rounded w-full" />
        <div className="h-3 bg-muted rounded w-2/3" />
      </div>
    )
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') onClick?.() }}
      className="group bg-surface border border-border rounded-card shadow-card p-5 flex flex-col gap-3 transition-all hover:shadow-md hover:border-border/80 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
    >
      {/* ── Top: Icon + Level badge ──────────────── */}
      <div className="flex items-start justify-between">
        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center', config.bgColor, config.textColor)}>
          {STATUS_ICONS[status.id]}
        </div>
        <div className="flex items-center gap-1.5">
          {/* Severity bar */}
          <div className="flex gap-0.5">
            {['critical', 'elevated', 'moderate', 'stable'].map((lvl, i) => {
              const levelOrder = { critical: 3, elevated: 2, moderate: 1, stable: 0 }
              const currentOrder = levelOrder[status.level as keyof typeof levelOrder]
              const isActive = i <= currentOrder
              return (
                <div
                  key={lvl}
                  className={cn(
                    'w-[14px] h-[3px] rounded-full transition-colors',
                    isActive ? config.barColor : 'bg-muted',
                  )}
                />
              )
            })}
          </div>
          <span className={cn('text-[10px] font-medium', config.textColor)}>
            {config.label}
          </span>
        </div>
      </div>

      {/* ── Label + Count ────────────────────────── */}
      <div>
        <p className="text-[11px] text-subtle font-medium tracking-wide uppercase mb-1">
          {status.label}
        </p>
        <p className="text-[28px] font-medium text-heading leading-none tabular-nums">
          {status.count}
        </p>
      </div>

      {/* ── Context line (intelligence, not just a number) ── */}
      <p className="text-[12px] text-body leading-relaxed line-clamp-2">
        {status.contextLine}
      </p>

      {/* ── Change detector ──────────────────────── */}
      <div className="flex items-center gap-1.5 text-[11px] text-subtle">
        <span className={cn(
          'flex items-center gap-0.5',
          status.trend === 'up' ? 'text-amber-600' : status.trend === 'down' ? 'text-emerald-600' : 'text-subtle',
        )}>
          {TREND_ICONS[status.trend]}
        </span>
        <span>{status.changeDetector}</span>
      </div>

      {/* ── Suggested action ─────────────────────── */}
      <button className="mt-auto flex items-center gap-1 text-[11px] font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity">
        {status.suggestedAction.replace(' →', '')}
        <ArrowRight size={11} />
      </button>
    </div>
  )
}
