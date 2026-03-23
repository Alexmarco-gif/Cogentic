import * as React from 'react'
import { cn } from '@/lib/utils'

interface LiveIndicatorProps {
  label?: string
  className?: string
}

export function LiveIndicator({ label = 'Live', className }: LiveIndicatorProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-2 rounded-full border border-success/20 bg-success/10 px-3 py-1 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-success',
        className,
      )}
      aria-label={`Status: ${label}`}
    >
      <span className="live-dot" aria-hidden="true" />
      {label}
    </span>
  )
}
