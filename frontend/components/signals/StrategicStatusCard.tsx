'use client'

import { cn } from '@/lib/utils'
import {
  AlertTriangle,
  ArrowRight,
  Lightbulb,
  Minus,
  Radio,
  Search,
  ShieldAlert,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import type { StrategicStatus, StatusLevel } from '@/lib/hooks/useSignals'

const LEVEL_CONFIG: Record<StatusLevel, {
  tone: string
  surface: string
  label: string
}> = {
  critical: {
    tone: 'text-critical',
    surface: 'bg-critical/10',
    label: 'Critical',
  },
  elevated: {
    tone: 'text-warning',
    surface: 'bg-warning/10',
    label: 'Elevated',
  },
  moderate: {
    tone: 'text-primary',
    surface: 'bg-primary/10',
    label: 'Moderate',
  },
  stable: {
    tone: 'text-success',
    surface: 'bg-success/10',
    label: 'Stable',
  },
}

const STATUS_ICONS: Record<string, React.ReactNode> = {
  risks: <ShieldAlert size={16} />,
  opportunities: <Lightbulb size={16} />,
  'critical-alerts': <AlertTriangle size={16} />,
  investigations: <Search size={16} />,
  'signals-today': <Radio size={16} />,
}

const TREND_ICONS: Record<string, React.ReactNode> = {
  up: <TrendingUp size={12} />,
  down: <TrendingDown size={12} />,
  flat: <Minus size={12} />,
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
      <div className="surface-panel space-y-4 p-5">
        <div className="skeleton h-10 w-10" />
        <div className="skeleton h-4 w-24" />
        <div className="skeleton h-10 w-16" />
        <div className="skeleton h-3 w-full" />
        <div className="skeleton h-3 w-2/3" />
      </div>
    )
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') onClick?.()
      }}
      className="group surface-panel flex cursor-pointer flex-col gap-4 p-5 transition-all duration-200 ease-spring hover:-translate-y-1 hover:border-border-hover"
    >
      <div className="flex items-start justify-between gap-3">
        <div className={cn(
          'flex h-11 w-11 items-center justify-center rounded-2xl',
          config.surface,
          config.tone,
        )}>
          {STATUS_ICONS[status.id]}
        </div>
        <span className={cn(
          'rounded-full px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.18em]',
          config.surface,
          config.tone,
        )}>
          {config.label}
        </span>
      </div>

      <div>
        <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">{status.label}</p>
        <p className="mt-2 text-[2rem] font-semibold leading-none tracking-[-0.04em] text-heading tabular-nums">
          {status.count}
        </p>
      </div>

      <p className="text-[0.84rem] text-body">{status.contextLine}</p>

      <div className="flex items-center gap-2 text-[0.76rem] text-subtle">
        <span className={cn(
          'inline-flex items-center gap-1 rounded-full border border-border bg-surface-2 px-2 py-1',
          status.trend === 'up'
            ? 'text-warning'
            : status.trend === 'down'
            ? 'text-success'
            : 'text-subtle',
        )}>
          {TREND_ICONS[status.trend]}
          {status.changeDetector}
        </span>
      </div>

      <div className="mt-auto flex items-center gap-2 text-[0.8rem] font-semibold text-primary transition-colors group-hover:text-primary-hover">
        {status.suggestedAction.replace(' ->', '').replace(' →', '')}
        <ArrowRight size={13} />
      </div>
    </div>
  )
}
