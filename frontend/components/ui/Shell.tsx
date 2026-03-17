import * as React from 'react'
import { cn } from '@/lib/utils'
import { NavigationRail } from './NavigationRail'
import { OmniBar } from './OmniBar'
import { MobileNav } from './MobileNav'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ShellProps {
  children: React.ReactNode
  notificationCount?: number
  className?: string
}

// ─── Shell ────────────────────────────────────────────────────────────────────
//
//  ┌──────────┬──────────────────────────────────┐
//  │  NavRail │  OmniBar (sticky top)            │
//  │  (fixed) ├──────────────────────────────────┤
//  │          │  <children> (scrollable content) │
//  └──────────┴──────────────────────────────────┘
//
//  Nav rail is `position: fixed` at 64px wide.
//  OmniBar is `position: fixed` at top, offset by nav rail width.
//  Main content has padding-left matching rail and padding-top matching bar.

export function Shell({ children, notificationCount = 0, className }: ShellProps) {
  return (
    <div className="min-h-screen bg-canvas">
      {/* Fixed left nav — hidden on mobile, visible md+ */}
      <NavigationRail
        notificationCount={notificationCount}
        className="hidden md:flex"
      />

      {/* Fixed top bar — full width on mobile, offset on md+ */}
      <OmniBar notificationCount={notificationCount} />

      {/* Scrollable page content */}
      <main
        className={cn(
          // Desktop: offset by nav rail. Mobile: no left padding.
          'pl-0 md:pl-[var(--nav-rail-collapsed)]',
          // Top offset for OmniBar
          'pt-[var(--omnibar-height)]',
          // Mobile: clear the bottom tab bar
          'pb-16 md:pb-0',
          'min-h-screen',
          className,
        )}
      >
        {children}
      </main>

      {/* Mobile bottom tab bar — hidden on md+ */}
      <MobileNav />
    </div>
  )
}
