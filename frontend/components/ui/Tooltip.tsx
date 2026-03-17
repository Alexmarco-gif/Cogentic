'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

type TooltipSide = 'top' | 'bottom' | 'left' | 'right'

interface TooltipProps {
  content: React.ReactNode
  side?: TooltipSide
  children: React.ReactNode
  className?: string
}

// ─── Position maps ────────────────────────────────────────────────────────────

const positionClasses: Record<TooltipSide, string> = {
  top:    'bottom-full left-1/2 -translate-x-1/2 mb-2',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
  left:   'right-full top-1/2 -translate-y-1/2 mr-2',
  right:  'left-full top-1/2 -translate-y-1/2 ml-2',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Tooltip({ content, side = 'top', children, className }: TooltipProps) {
  const [visible, setVisible] = React.useState(false)

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}

      {visible && (
        <span
          role="tooltip"
          className={cn(
            'pointer-events-none absolute z-50 whitespace-nowrap',
            'rounded-lg bg-heading text-white text-xs px-2.5 py-1.5 shadow-modal',
            'animate-fade-up',
            positionClasses[side],
            className,
          )}
        >
          {content}
        </span>
      )}
    </span>
  )
}
