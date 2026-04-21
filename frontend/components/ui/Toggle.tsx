'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  description?: string
  disabled?: boolean
  id?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Toggle({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  id,
}: ToggleProps) {
  const generatedId = React.useId()
  const inputId = id ?? generatedId

  return (
    <label
      htmlFor={inputId}
      className={cn(
        'flex items-center justify-between gap-4 cursor-pointer rounded-lg p-3',
        'hover:bg-muted transition-colors',
        disabled && 'pointer-events-none opacity-50',
      )}
    >
      {/* Label block */}
      {(label || description) && (
        <div className="flex flex-col gap-0.5">
          {label && <span className="text-sm text-body font-medium">{label}</span>}
          {description && <span className="text-xs text-subtle">{description}</span>}
        </div>
      )}

      {/* Track & thumb */}
      <div className="relative shrink-0">
        <input
          id={inputId}
          type="checkbox"
          role="switch"
          aria-checked={checked}
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only"
        />
        <div
          className={cn(
            'w-10 h-6 rounded-full transition-colors duration-200',
            checked ? 'bg-primary' : 'bg-border',
          )}
        />
        <div
          className={cn(
            'absolute top-1 left-1 w-4 h-4 rounded-full bg-white shadow-sm',
            'transition-transform duration-200',
            checked && 'translate-x-4',
          )}
        />
      </div>
    </label>
  )
}
