'use client'

import { memo } from 'react'
import { AlertTriangle, Radio, Bookmark, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ─────────────────────────────────────────────────────────────────────

interface StatItem {
  label: string
  value: number | string
  sub: string
  icon: React.ElementType
  accent: string      // tailwind text color class
  bgAccent: string    // tailwind bg tint class
  pillColor: string   // dot indicator color
}

interface SignalsStatsBarProps {
  total: number
  critical: number
  unread: number
  saved: number
  className?: string
}

// ── Component ─────────────────────────────────────────────────────────────────

export const SignalsStatsBar = memo(function SignalsStatsBar({
  total,
  critical,
  unread,
  saved,
  className,
}: SignalsStatsBarProps) {
  const stats: StatItem[] = [
    {
      label: 'Total Signals',
      value: total,
      sub: 'across all domains',
      icon: TrendingUp,
      accent: 'text-indigo-400',
      bgAccent: 'bg-indigo-500/8',
      pillColor: 'bg-indigo-400',
    },
    {
      label: 'Critical',
      value: critical,
      sub: 'require immediate attention',
      icon: AlertTriangle,
      accent: 'text-red-400',
      bgAccent: 'bg-red-500/8',
      pillColor: 'bg-red-400',
    },
    {
      label: 'New Today',
      value: unread,
      sub: 'unread since last session',
      icon: Radio,
      accent: 'text-amber-400',
      bgAccent: 'bg-amber-500/8',
      pillColor: 'bg-amber-400',
    },
    {
      label: 'Saved',
      value: saved,
      sub: 'in your watchlist',
      icon: Bookmark,
      accent: 'text-emerald-400',
      bgAccent: 'bg-emerald-500/8',
      pillColor: 'bg-emerald-400',
    },
  ]

  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-3 sm:grid-cols-4',
        className,
      )}
    >
      {stats.map((stat) => {
        const Icon = stat.icon
        return (
          <div
            key={stat.label}
            className={cn(
              'relative flex items-start gap-3 rounded-card border border-border p-4',
              'bg-surface transition-colors duration-200',
              'hover:border-white/10',
            )}
          >
            {/* icon pill */}
            <div
              className={cn(
                'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                stat.bgAccent,
              )}
            >
              <Icon className={cn('h-4 w-4', stat.accent)} strokeWidth={1.8} />
            </div>

            {/* text */}
            <div className="min-w-0 flex-1">
              <div
                className={cn(
                  'font-display text-2xl font-bold leading-none tracking-tight',
                  stat.accent,
                )}
              >
                {stat.value}
              </div>
              <div className="mt-0.5 text-xs font-medium text-heading">
                {stat.label}
              </div>
              <div className="mt-0.5 truncate text-[11px] text-subtle">
                {stat.sub}
              </div>
            </div>

            {/* pulse dot for critical and unread */}
            {(stat.label === 'Critical' && critical > 0) ||
            (stat.label === 'New Today' && unread > 0) ? (
              <span className="absolute right-3 top-3">
                <span className="relative flex h-2 w-2">
                  <span
                    className={cn(
                      'absolute inline-flex h-full w-full animate-ping rounded-full opacity-60',
                      stat.pillColor,
                    )}
                  />
                  <span
                    className={cn(
                      'relative inline-flex h-2 w-2 rounded-full',
                      stat.pillColor,
                    )}
                  />
                </span>
              </span>
            ) : null}
          </div>
        )
      })}
    </div>
  )
})
