import * as React from 'react'
import { cn } from '@/lib/utils'
import { NavigationRail } from './NavigationRail'
import { OmniBar } from './OmniBar'
import { MobileNav } from './MobileNav'

interface ShellProps {
  children: React.ReactNode
  notificationCount?: number
  className?: string
}

export function Shell({ children, notificationCount = 0, className }: ShellProps) {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-canvas">
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          backgroundImage:
            'radial-gradient(circle at 8% 0%, rgba(37,99,235,0.14), transparent 28%), radial-gradient(circle at 88% 0%, rgba(17,24,39,0.08), transparent 26%)',
        }}
      />

      <NavigationRail
        notificationCount={notificationCount}
        className="hidden md:flex"
      />

      <OmniBar notificationCount={notificationCount} />

      <main
        className={cn(
          'relative pl-0 pt-[var(--omnibar-height)] pb-20 md:pl-[var(--nav-rail-collapsed)] md:pb-0',
          className,
        )}
      >
        <div className="mx-auto min-h-screen max-w-shell px-3 pb-8 sm:px-5 md:px-6 lg:px-8">
          {children}
        </div>
      </main>

      <MobileNav />
    </div>
  )
}
