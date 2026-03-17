'use client'

import * as React from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './Button'

// ─── Types ────────────────────────────────────────────────────────────────────

interface DialogProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  description?: string
  /** max-w class – defaults to 'max-w-lg' */
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'reader'
  children: React.ReactNode
  /** Hide default padding (e.g. for full-bleed content) */
  noPadding?: boolean
}

const sizeClasses = {
  sm:     'max-w-sm',
  md:     'max-w-lg',
  lg:     'max-w-2xl',
  xl:     'max-w-4xl',
  reader: 'max-w-[65ch]',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Dialog({
  open,
  onClose,
  title,
  description,
  size = 'md',
  noPadding = false,
  children,
}: DialogProps) {

  // Close on Escape
  React.useEffect(() => {
    if (!open) return
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Lock body scroll
  React.useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'dialog-title' : undefined}
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-heading/20 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={cn(
          'relative z-10 w-full mx-4 bg-surface rounded-lg shadow-modal',
          'animate-fade-up',
          sizeClasses[size],
          !noPadding && 'p-6',
        )}
      >
        {/* Header */}
        {(title || description) && (
          <div className={cn('flex items-start justify-between gap-4', !noPadding && 'mb-4')}>
            <div>
              {title && (
                <h2 id="dialog-title" className="text-heading text-base font-medium">
                  {title}
                </h2>
              )}
              {description && (
                <p className="mt-1 text-sm text-subtle">{description}</p>
              )}
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label="Close dialog"
              className="shrink-0 -mt-1 -mr-1"
            >
              <X size={16} />
            </Button>
          </div>
        )}

        {/* If no header — floating close button */}
        {!title && !description && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close dialog"
            className={cn('absolute top-3 right-3', noPadding && 'z-10')}
          >
            <X size={16} />
          </Button>
        )}

        {children}
      </div>
    </div>
  )
}
