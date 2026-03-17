import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Card Root ────────────────────────────────────────────────────────────────

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Remove default padding */
  noPadding?: boolean
}

export function Card({ noPadding = false, className, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'bg-surface border border-border shadow-card rounded-lg',
        !noPadding && 'p-4',
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}

// ─── Card Sub-parts ───────────────────────────────────────────────────────────

export function CardHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex items-center justify-between gap-3', className)} {...props}>
      {children}
    </div>
  )
}

export function CardBody({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('mt-3', className)} {...props}>
      {children}
    </div>
  )
}

export function CardFooter({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('mt-4 pt-3 border-t border-border flex items-center gap-2', className)}
      {...props}
    >
      {children}
    </div>
  )
}
