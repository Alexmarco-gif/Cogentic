'use client'

import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowRight,
  BarChart3,
  Server,
  Users,
  Cpu,
  Download,
} from 'lucide-react'
import type { HeatmapQuadrant, StatusLevel } from '@/lib/hooks/useSignals'

// ── Level colors ─────────────────────────────────────────────────────────────
const LEVEL_STYLE: Record<StatusLevel, {
  bg: string
  border: string
  dot: string
  text: string
  label: string
  pulse?: boolean
}> = {
  critical: {
    bg:     'bg-red-500/5',
    border: 'border-red-500/20',
    dot:    'bg-red-500',
    text:   'text-red-600',
    label:  'Critical',
    pulse:  true,
  },
  elevated: {
    bg:     'bg-amber-500/5',
    border: 'border-amber-500/20',
    dot:    'bg-amber-500',
    text:   'text-amber-600',
    label:  'Elevated',
  },
  moderate: {
    bg:     'bg-blue-500/5',
    border: 'border-blue-500/20',
    dot:    'bg-blue-500',
    text:   'text-blue-600',
    label:  'Moderate',
  },
  stable: {
    bg:     'bg-emerald-500/5',
    border: 'border-emerald-500/20',
    dot:    'bg-emerald-500',
    text:   'text-emerald-600',
    label:  'Stable',
  },
}

const QUADRANT_ICONS: Record<string, React.ReactNode> = {
  'market-risk':         <BarChart3 size={14} />,
  'infra-health':        <Server    size={14} />,
  'competitor-activity': <Users     size={14} />,
  'tech-trends':         <Cpu       size={14} />,
}

const TREND_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  improving:     { icon: <TrendingUp   size={11} />, label: 'Improving',     color: 'text-emerald-600' },
  deteriorating: { icon: <TrendingDown size={11} />, label: 'Deteriorating', color: 'text-red-600' },
  stable:        { icon: <Minus        size={11} />, label: 'Stable',        color: 'text-subtle' },
}

interface IntelHeatmapProps {
  quadrants: HeatmapQuadrant[]
  loading?: boolean
}

// Quadrant id → destination route
const ACTION_ROUTES: Record<string, string> = {
  'market-risk':         '/dashboard/investigate?q=Market+Risk+Analysis',
  'infra-health':        '/dashboard/signals',
  'competitor-activity': '/dashboard/investigate?q=Competitor+Activity+Analysis',
  'tech-trends':         '/dashboard/signals',
}

export function IntelHeatmap({ quadrants, loading }: IntelHeatmapProps) {
  const router = useRouter()

  function handleExport() {
    const lines: string[] = [
      '# Intelligence Heatmap Report',
      `*Generated: ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}*`,
      '',
      ...quadrants.flatMap(q => [
        `## ${q.label}`,
        `**Status**: ${q.level.toUpperCase()} · **Trend**: ${q.trend}`,
        '',
        q.explanation,
        '',
        `> **Forecast**: ${q.forecast}`,
        `> **Suggested action**: ${q.suggestedAction}`,
        '',
      ]),
      '---',
      '*Cogent Intelligence — Proprietary Report*',
    ]
    const md = lines.join('\n')
    const blob = new Blob([md], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `cogent-heatmap-${new Date().toISOString().slice(0, 10)}.md`
    a.click()
    URL.revokeObjectURL(a.href)
  }
  if (loading) {
    return (
      <div className="bg-surface border border-border rounded-card shadow-card p-5">
        <div className="h-4 bg-muted rounded w-1/3 mb-4 animate-pulse" />
        <div className="grid grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-40 bg-muted rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-border rounded-card shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-[14px] font-medium text-heading">Intelligence Heatmap</h2>
            <p className="text-[11px] text-subtle mt-0.5">
              Strategic attention allocation across 4 domains
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-3 text-[10px] text-subtle">
              {Object.entries(LEVEL_STYLE).map(([key, style]) => (
                <div key={key} className="flex items-center gap-1">
                  <span className={cn('w-1.5 h-1.5 rounded-full', style.dot)} />
                  <span>{style.label}</span>
                </div>
              ))}
            </div>
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-surface px-2.5 py-1.5 text-[11px] font-medium text-subtle hover:bg-muted hover:text-body transition-colors"
            >
              <Download size={12} />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* 2×2 Grid */}
      <div className="grid grid-cols-2 gap-px bg-border/50">
        {quadrants.map(q => {
          const style = LEVEL_STYLE[q.level]
          const trend = TREND_CONFIG[q.trend]

          return (
            <div
              key={q.id}
              className={cn(
                'group p-5 transition-colors cursor-pointer hover:bg-muted/30',
                style.bg,
              )}
            >
              {/* Quadrant header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={cn('w-7 h-7 rounded-lg flex items-center justify-center bg-surface border', style.border, style.text)}>
                    {QUADRANT_ICONS[q.id]}
                  </div>
                  <div>
                    <p className="text-[12px] font-medium text-heading">{q.label}</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {/* Status dot (pulse for critical) */}
                      <span className="relative flex h-1.5 w-1.5">
                        {style.pulse && (
                          <span className={cn('animate-ping absolute inline-flex h-full w-full rounded-full opacity-75', style.dot)} />
                        )}
                        <span className={cn('relative inline-flex rounded-full h-1.5 w-1.5', style.dot)} />
                      </span>
                      <span className={cn('text-[10px] font-medium', style.text)}>
                        {style.label}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Trend indicator */}
                <div className={cn('flex items-center gap-0.5 text-[10px] font-medium', trend.color)}>
                  {trend.icon}
                  <span>{trend.label}</span>
                </div>
              </div>

              {/* Explanation */}
              <p className="text-[12px] text-body leading-relaxed mb-3">
                {q.explanation}
              </p>

              {/* Predictive forecast label */}
              <div className="flex items-start gap-1.5 mb-3 bg-surface/60 border border-border/50 rounded-lg px-3 py-2">
                <span className="text-[10px] font-medium text-primary bg-primary/8 px-1.5 py-0.5 rounded shrink-0 mt-px">
                  FORECAST
                </span>
                <p className="text-[11px] text-subtle leading-snug">
                  {q.forecast}
                </p>
              </div>

              {/* Action link */}
              <button
                onClick={() => router.push(ACTION_ROUTES[q.id] ?? '/dashboard/signals')}
                className="flex items-center gap-1 text-[11px] font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity"
              >
                {q.suggestedAction.replace(' →', '')}
                <ArrowRight size={11} />
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
