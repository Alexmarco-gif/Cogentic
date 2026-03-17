'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

type BadgeVariant =
  | 'default'
  | 'success'
  | 'warning'
  | 'critical'
  | 'neutral'
  | 'ai'         // Indigo — reserved for AI-generated content
  | 'outline'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant
}

// ─── Variant Map ──────────────────────────────────────────────────────────────

const variantClasses: Record<BadgeVariant, string> = {
  default:  'bg-muted text-body',
  success:  'bg-[#ECFDF5] text-[#059669]',
  warning:  'bg-[#FFFBEB] text-[#D97706]',
  critical: 'bg-[#FFF1F2] text-[#E11D48]',
  neutral:  'bg-muted text-neutral',
  ai:       'bg-[#EEF2FF] text-primary',  // Indigo — AI content only
  outline:  'bg-transparent border border-border text-body',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Badge({
  variant = 'default',
  className,
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium leading-none',
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
