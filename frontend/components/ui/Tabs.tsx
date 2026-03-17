'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Tab {
  id: string
  label: string
  icon?: React.ReactNode
  badge?: string | number
}

type TabsVariant = 'line' | 'pill'

interface TabsProps {
  tabs: Tab[]
  activeTab: string
  onChange: (id: string) => void
  variant?: TabsVariant
  className?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Tabs({
  tabs,
  activeTab,
  onChange,
  variant = 'line',
  className,
}: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn(
        variant === 'line'
          ? 'flex gap-0 border-b border-border'
          : 'flex gap-1 p-1 bg-muted rounded-lg',
        className,
      )}
    >
      {tabs.map(tab => {
        const isActive = tab.id === activeTab

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={cn(
              'inline-flex items-center gap-2 text-sm font-medium transition-all duration-150',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 rounded',
              variant === 'line'
                ? [
                    'px-4 py-2.5 -mb-px border-b-2',
                    isActive
                      ? 'border-primary text-primary'
                      : 'border-transparent text-subtle hover:text-body hover:border-border',
                  ]
                : [
                    'px-3 py-1.5 rounded-md',
                    isActive
                      ? 'bg-surface text-heading shadow-card'
                      : 'text-subtle hover:text-body',
                  ],
            )}
          >
            {tab.icon && <span className="w-4 h-4">{tab.icon}</span>}
            {tab.label}
            {tab.badge !== undefined && (
              <span
                className={cn(
                  'rounded-full text-[10px] px-1.5 py-0.5 leading-none',
                  isActive
                    ? 'bg-primary text-white'
                    : 'bg-border text-subtle',
                )}
              >
                {tab.badge}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
