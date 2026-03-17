'use client'

import * as React from 'react'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './Button'

// ─── Types ────────────────────────────────────────────────────────────────────

type DrawerSide = 'right' | 'left' | 'bottom'

interface DrawerProps {
  open: boolean
  onClose: () => void
  side?: DrawerSide
  /** Width for left/right drawers — default '480px' */
  width?: string
  /** Height for bottom drawer — default '60vh' */
  height?: string
  title?: React.ReactNode
  children: React.ReactNode
  className?: string
}

// ─── Slide animation per side ────────────────────────────────────────────────

const slideIn: Record<DrawerSide, string> = {
  right:  'animate-slide-in-right',
  left:   'animate-[slide-in-left_0.25s_cubic-bezier(0.16,1,0.3,1)_both]',
  bottom: 'animate-[slide-in-bottom_0.25s_cubic-bezier(0.16,1,0.3,1)_both]',
}

const positionStyles: Record<DrawerSide, string> = {
  right:  'right-0 top-0 bottom-0',
  left:   'left-0 top-0 bottom-0',
  bottom: 'bottom-0 left-0 right-0',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Drawer({
  open,
  onClose,
  side = 'right',
  width = '480px',
  height = '60vh',
  title,
  children,
  className,
}: DrawerProps) {

  // Escape key
  React.useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  // Body scroll lock
  React.useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [open])

  if (!open) return null

  const isHorizontal = side === 'right' || side === 'left'

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? 'drawer-title' : undefined}
      className="fixed inset-0 z-50 flex"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-heading/15 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        style={isHorizontal ? { width } : { height }}
        className={cn(
          'absolute flex flex-col bg-surface shadow-modal overflow-hidden',
          positionStyles[side],
          slideIn[side],
          className,
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
          {title ? (
            <h2 id="drawer-title" className="text-base font-medium text-heading">
              {title}
            </h2>
          ) : (
            <span />
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label="Close panel"
          >
            <X size={16} />
          </Button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  )
}
