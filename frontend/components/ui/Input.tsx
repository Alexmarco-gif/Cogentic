'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Icon rendered on the left (e.g. Lucide <Search />) */
  icon?: React.ReactNode
  /** Error message shown below — also sets error border */
  error?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ icon, error, className, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1 w-full">
        <div className="relative flex items-center">
          {icon && (
            <span className="absolute left-3 text-neutral pointer-events-none">
              {icon}
            </span>
          )}
          <input
            ref={ref}
            className={cn(
              'w-full rounded-lg bg-muted text-sm text-body',
              'h-9 px-3',
              'placeholder:text-subtle',
              'border border-transparent',
              'transition-colors duration-150',
              'focus:outline-none focus:border-primary/40 focus:bg-surface',
              'disabled:cursor-not-allowed disabled:opacity-50',
              icon && 'pl-9',
              error && 'border-critical/60 focus:border-critical/60',
              className,
            )}
            aria-invalid={!!error}
            {...props}
          />
        </div>
        {error && (
          <p className="text-xs text-critical" role="alert">{error}</p>
        )}
      </div>
    )
  },
)

Input.displayName = 'Input'
