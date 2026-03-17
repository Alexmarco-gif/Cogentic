import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface LiveIndicatorProps {
  label?: string
  className?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function LiveIndicator({ label = 'Live', className }: LiveIndicatorProps) {
  return (
    <span
      className={cn('inline-flex items-center gap-1.5 text-xs text-[#059669] font-medium', className)}
      aria-label={`Status: ${label}`}
    >
      <span className="live-dot" aria-hidden="true" />
      {label}
    </span>
  )
}
