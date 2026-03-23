'use client'

import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  ArrowRight,
  BarChart3,
  Cpu,
  Download,
  Minus,
  Server,
  TrendingDown,
  TrendingUp,
  Users,
} from 'lucide-react'
import type { HeatmapQuadrant, StatusLevel } from '@/lib/hooks/useSignals'

const LEVEL_STYLE: Record<StatusLevel, {
  surface: string
  tone: string
  dot: string
  label: string
  pulse?: boolean
}> = {
  critical: {
    surface: 'bg-critical/10',
    tone: 'text-critical',
    dot: 'bg-critical',
    label: 'Critical',
    pulse: true,
  },
  elevated: {
    surface: 'bg-warning/10',
    tone: 'text-warning',
    dot: 'bg-warning',
    label: 'Elevated',
  },
  moderate: {
    surface: 'bg-primary/10',
    tone: 'text-primary',
    dot: 'bg-primary',
    label: 'Moderate',
  },
  stable: {
    surface: 'bg-success/10',
    tone: 'text-success',
    dot: 'bg-success',
    label: 'Stable',
  },
}

const QUADRANT_ICONS: Record<string, React.ReactNode> = {
  'market-risk': <BarChart3 size={15} />,
  'infra-health': <Server size={15} />,
  'competitor-activity': <Users size={15} />,
  'tech-trends': <Cpu size={15} />,
}

const TREND_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  improving: { icon: <TrendingUp size={12} />, label: 'Improving', color: 'text-success' },
  deteriorating: { icon: <TrendingDown size={12} />, label: 'Deteriorating', color: 'text-critical' },
  stable: { icon: <Minus size={12} />, label: 'Stable', color: 'text-subtle' },
}

interface IntelHeatmapProps {
  quadrants: HeatmapQuadrant[]
  loading?: boolean
}

const ACTION_ROUTES: Record<string, string> = {
  'market-risk': '/dashboard/investigate?q=Market+Risk+Analysis',
  'infra-health': '/dashboard/signals',
  'competitor-activity': '/dashboard/investigate?q=Competitor+Activity+Analysis',
  'tech-trends': '/dashboard/signals',
}

export function IntelHeatmap({ quadrants, loading }: IntelHeatmapProps) {
  const router = useRouter()

  function handleExport() {
    const lines: string[] = [
      '# Intelligence Heatmap Report',
      `*Generated: ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}*`,
      '',
      ...quadrants.flatMap((quadrant) => [
        `## ${quadrant.label}`,
        `**Status**: ${quadrant.level.toUpperCase()} - **Trend**: ${quadrant.trend}`,
        '',
        quadrant.explanation,
        '',
        `> **Forecast**: ${quadrant.forecast}`,
        `> **Suggested action**: ${quadrant.suggestedAction}`,
        '',
      ]),
      '---',
      '*Cogent Intelligence - Proprietary Report*',
    ]

    const md = lines.join('\n')
    const blob = new Blob([md], { type: 'text/markdown' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `cogent-heatmap-${new Date().toISOString().slice(0, 10)}.md`
    link.click()
    URL.revokeObjectURL(link.href)
  }

  if (loading) {
    return (
      <div className="surface-panel p-5">
        <div className="skeleton mb-4 h-5 w-40" />
        <div className="grid gap-3 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="skeleton h-48 w-full" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="surface-panel overflow-hidden">
      <div className="border-b border-border px-5 py-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="eyebrow">Situation room</p>
            <h2 className="mt-2 text-title">Where leadership attention should go next</h2>
            <p className="mt-2 max-w-2xl text-[0.82rem] text-subtle">
              Use this heatmap to understand what is accelerating, where pressure is building, and which areas deserve immediate investigation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="hidden flex-wrap items-center gap-2 md:flex">
              {Object.values(LEVEL_STYLE).map((style) => (
                <div key={style.label} className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-[0.72rem] font-semibold text-subtle">
                  <span className={cn('h-2 w-2 rounded-full', style.dot)} />
                  {style.label}
                </div>
              ))}
            </div>

            <button
              onClick={handleExport}
              className="button-press inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-[0.8rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
            >
              <Download size={14} />
              Export
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-px bg-border/70 md:grid-cols-2">
        {quadrants.map((quadrant) => {
          const style = LEVEL_STYLE[quadrant.level]
          const trend = TREND_CONFIG[quadrant.trend]

          return (
            <button
              key={quadrant.id}
              onClick={() => router.push(ACTION_ROUTES[quadrant.id] ?? '/dashboard/signals')}
              className="group bg-surface px-5 py-5 text-left transition-all duration-200 hover:bg-surface-2/75"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    'flex h-11 w-11 items-center justify-center rounded-2xl',
                    style.surface,
                    style.tone,
                  )}>
                    {QUADRANT_ICONS[quadrant.id]}
                  </div>
                  <div>
                    <p className="text-[0.9rem] font-semibold text-heading">{quadrant.label}</p>
                    <div className="mt-1 flex items-center gap-2">
                      <span className="relative flex h-2.5 w-2.5">
                        {style.pulse && (
                          <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', style.dot)} />
                        )}
                        <span className={cn('relative inline-flex h-2.5 w-2.5 rounded-full', style.dot)} />
                      </span>
                      <span className={cn('text-[0.72rem] font-semibold uppercase tracking-[0.16em]', style.tone)}>
                        {style.label}
                      </span>
                    </div>
                  </div>
                </div>

                <span className={cn('inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1 text-[0.72rem] font-semibold', trend.color)}>
                  {trend.icon}
                  {trend.label}
                </span>
              </div>

              <p className="mt-4 text-[0.84rem] text-body">{quadrant.explanation}</p>

              <div className="mt-4 rounded-[20px] border border-border bg-surface-2/70 px-4 py-3">
                <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-primary">Forecast</p>
                <p className="mt-1 text-[0.78rem] text-subtle">{quadrant.forecast}</p>
              </div>

              <div className="mt-4 inline-flex items-center gap-2 text-[0.82rem] font-semibold text-primary transition-colors group-hover:text-primary-hover">
                {quadrant.suggestedAction.replace(' ->', '').replace(' →', '')}
                <ArrowRight size={13} />
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
