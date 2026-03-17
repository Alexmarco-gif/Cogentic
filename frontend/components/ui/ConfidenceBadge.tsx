'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Tooltip } from './Tooltip'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ConfidenceBreakdown {
  source: 'high' | 'medium' | 'low'
  freshness: 'high' | 'medium' | 'low'
  corroboration: 'high' | 'medium' | 'low'
}

interface ConfidenceBadgeProps {
  /** 0–100 */
  score: number
  breakdown?: ConfidenceBreakdown
  /** 'ring' shows SVG ring, 'pill' shows plain badge */
  mode?: 'ring' | 'pill'
  className?: string
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 75) return { stroke: '#059669', text: 'text-[#059669]', bg: 'bg-[#ECFDF5]' }
  if (score >= 50) return { stroke: '#D97706', text: 'text-[#D97706]', bg: 'bg-[#FFFBEB]' }
  return          { stroke: '#E11D48', text: 'text-[#E11D48]', bg: 'bg-[#FFF1F2]' }
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1)
}

// ─── Ring mode ────────────────────────────────────────────────────────────────

function ConfidenceRing({ score, breakdown, className }: ConfidenceBadgeProps) {
  const size   = 40
  const radius = 16
  const circ   = 2 * Math.PI * radius
  const offset = circ - (score / 100) * circ
  const colors = scoreColor(score)

  const tooltipContent = breakdown ? (
    <div className="space-y-1 text-xs">
      <p>Source: <strong>{capitalize(breakdown.source)}</strong></p>
      <p>Freshness: <strong>{capitalize(breakdown.freshness)}</strong></p>
      <p>Corroboration: <strong>{capitalize(breakdown.corroboration)}</strong></p>
    </div>
  ) : `${score}% confidence`

  return (
    <Tooltip content={tooltipContent} side="left">
      <span
        className={cn('relative inline-flex items-center justify-center', className)}
        style={{ width: size, height: size }}
        aria-label={`Confidence: ${score}%`}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="-rotate-90"
          aria-hidden="true"
        >
          {/* Track */}
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none" stroke="#E2E8F0" strokeWidth="3"
          />
          {/* Progress */}
          <circle
            cx={size / 2} cy={size / 2} r={radius}
            fill="none"
            stroke={colors.stroke}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.6s ease' }}
          />
        </svg>
        <span className={cn('absolute text-[10px] font-medium', colors.text)}>
          {score}
        </span>
      </span>
    </Tooltip>
  )
}

// ─── Pill mode ────────────────────────────────────────────────────────────────

function ConfidencePill({ score, className }: ConfidenceBadgeProps) {
  const colors = scoreColor(score)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        colors.bg, colors.text, className,
      )}
      aria-label={`Confidence: ${score}%`}
    >
      <span className={cn('w-1.5 h-1.5 rounded-full', `bg-current`)} aria-hidden="true" />
      {score}%
    </span>
  )
}

// ─── Public export ───────────────────────────────────────────────────────────

export function ConfidenceBadge(props: ConfidenceBadgeProps) {
  const { mode = 'ring' } = props
  return mode === 'ring' ? <ConfidenceRing {...props} /> : <ConfidencePill {...props} />
}
