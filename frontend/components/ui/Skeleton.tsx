import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Generic Skeleton ─────────────────────────────────────────────────────────

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden="true"
      className={cn('skeleton', className)}
      {...props}
    />
  )
}

// ─── Pre-built skeleton shapes ────────────────────────────────────────────────

/** Matches a single SignalCard */
export function SignalCardSkeleton() {
  return (
    <div className="bg-surface border border-border shadow-card rounded-lg p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="w-8 h-8 rounded-full" />
          <Skeleton className="w-28 h-3 rounded" />
        </div>
        <Skeleton className="w-14 h-5 rounded-full" />
      </div>
      {/* Headline */}
      <Skeleton className="w-3/4 h-4 rounded" />
      {/* Summary lines */}
      <Skeleton className="w-full h-3 rounded" />
      <Skeleton className="w-2/3 h-3 rounded" />
      {/* Sparkline */}
      <Skeleton className="w-24 h-6 rounded" />
    </div>
  )
}

/** Matches a single table row in the Signals grid */
export function TableRowSkeleton() {
  return (
    <div className="flex items-center gap-4 px-4 h-12 border-b border-border">
      <Skeleton className="w-8 h-8 rounded-full shrink-0" />
      <Skeleton className="w-32 h-3 rounded" />
      <Skeleton className="flex-1 h-3 rounded" />
      <Skeleton className="w-20 h-5 rounded" />
      <Skeleton className="w-10 h-10 rounded-full" />
      <Skeleton className="w-12 h-7 rounded-lg" />
    </div>
  )
}

/** Brief card skeleton for the Library grid */
export function BriefCardSkeleton() {
  return (
    <div className="bg-surface border border-border shadow-card rounded-lg overflow-hidden">
      <Skeleton className="w-full h-32" />
      <div className="p-4 space-y-2">
        <Skeleton className="w-4/5 h-4 rounded" />
        <Skeleton className="w-3/5 h-4 rounded" />
        <Skeleton className="w-24 h-3 rounded mt-1" />
        <div className="flex gap-1.5 mt-2">
          <Skeleton className="w-16 h-5 rounded-full" />
          <Skeleton className="w-14 h-5 rounded-full" />
        </div>
      </div>
    </div>
  )
}

/** Message bubble skeleton for Investigate chat */
export function MessageSkeleton({ align = 'left' }: { align?: 'left' | 'right' }) {
  return (
    <div className={cn('flex gap-2 max-w-[75%]', align === 'right' && 'ml-auto flex-row-reverse')}>
      <Skeleton className="w-8 h-8 rounded-full shrink-0" />
      <div className="space-y-2 flex-1">
        <Skeleton className="w-full h-3 rounded" />
        <Skeleton className="w-4/5 h-3 rounded" />
        <Skeleton className="w-3/5 h-3 rounded" />
      </div>
    </div>
  )
}
