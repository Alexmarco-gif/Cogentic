'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Called when user presses Enter (without Shift). Shift+Enter inserts newline. */
  onEnter?: (value: string) => void
  error?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ onEnter, error, className, onKeyDown, ...props }, ref) => {
    function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
      if (e.key === 'Enter' && !e.shiftKey && onEnter) {
        e.preventDefault()
        const val = (e.target as HTMLTextAreaElement).value
        if (val.trim()) onEnter(val.trim())
      }
      onKeyDown?.(e)
    }

    return (
      <div className="flex flex-col gap-1 w-full">
        <textarea
          ref={ref}
          onKeyDown={handleKeyDown}
          className={cn(
            'w-full rounded-lg bg-muted text-sm text-body',
            'px-3 py-2.5 min-h-[40px]',
            'placeholder:text-subtle resize-none',
            'border border-transparent',
            'transition-colors duration-150',
            'focus:outline-none focus:border-primary/40 focus:bg-surface',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-critical/60',
            className,
          )}
          aria-invalid={!!error}
          {...props}
        />
        {error && (
          <p className="text-xs text-critical" role="alert">{error}</p>
        )}
      </div>
    )
  },
)

Textarea.displayName = 'Textarea'
