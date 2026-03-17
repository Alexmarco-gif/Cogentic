import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── ScrollArea ───────────────────────────────────────────────────────────────
// Thin custom scrollbar via globals.css ::-webkit-scrollbar rules.
// This component adds a constrained, overflow-auto wrapper.

interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Maximum height before scrolling kicks in */
  maxHeight?: string
  /** Horizontal scrolling as well */
  horizontal?: boolean
}

export function ScrollArea({
  maxHeight,
  horizontal = false,
  style,
  className,
  children,
  ...props
}: ScrollAreaProps) {
  return (
    <div
      className={cn(
        'overflow-y-auto',
        horizontal && 'overflow-x-auto',
        className,
      )}
      style={{
        maxHeight,
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  )
}
