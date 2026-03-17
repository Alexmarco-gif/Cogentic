'use client'

import * as React from 'react'
import { LineChart, Line, ResponsiveContainer } from 'recharts'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

export type TrendColor = 'emerald' | 'rose' | 'amber' | 'indigo'

interface TrendLineProps {
  /** Array of numeric values (order: oldest → newest) */
  data: number[]
  color?: TrendColor
  width?: number
  height?: number
  className?: string
}

// ─── Color map ────────────────────────────────────────────────────────────────

const colorMap: Record<TrendColor, string> = {
  emerald: '#059669',
  rose:    '#E11D48',
  amber:   '#D97706',
  indigo:  '#4F46E5',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function TrendLine({
  data,
  color = 'emerald',
  width = 80,
  height = 24,
  className,
}: TrendLineProps) {
  // Auto-detect direction for default color assignment
  const resolvedColor = color === 'emerald' && data.length >= 2
    ? data[data.length - 1] >= data[0] ? 'emerald' : 'rose'
    : color

  const chartData = data.map((v, i) => ({ i, v }))
  const stroke = colorMap[resolvedColor]

  if (!data.length) return null

  return (
    <span
      className={cn('inline-block', className)}
      style={{ width, height }}
      aria-hidden="true"
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={stroke}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </span>
  )
}
