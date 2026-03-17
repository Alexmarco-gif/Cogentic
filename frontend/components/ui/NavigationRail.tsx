'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useUser } from '@auth0/nextjs-auth0/client'
import {
  Home, Search, Activity, Globe, BookOpen, FileCode2,
  Settings, Sun, Moon, LogOut, Radar, BarChart3,
  User, CreditCard, KeyRound, ChevronRight, ShoppingBag,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Tooltip } from './Tooltip'
import { Avatar } from './Avatar'
import { Separator } from './Separator'
import { StemIcon } from './StemIcon'
import { useThemeStore } from '@/lib/stores/themeStore'

// ─── Nav item definitions ─────────────────────────────────────────────────────

const NAV_ITEMS = [
  { id: 'home',        label: 'Home',        href: '/dashboard/home',        icon: Home        },
  { id: 'investigate', label: 'Investigate', href: '/dashboard/investigate', icon: Search      },
  { id: 'signals',     label: 'Signals',     href: '/dashboard/signals',     icon: Activity    },
  { id: 'marketplace', label: 'Marketplace', href: '/dashboard/marketplace', icon: ShoppingBag },
  { id: 'discovery',   label: 'Discovery',   href: '/dashboard/discovery',   icon: Radar       },
  { id: 'market-data', label: 'Market Data', href: '/dashboard/market-data', icon: BarChart3   },
  { id: 'domains',     label: 'Domains',     href: '/dashboard/domains',     icon: Globe       },
  { id: 'library',     label: 'Library',     href: '/dashboard/library',     icon: BookOpen    },
  { id: 'studio',      label: 'Studio',      href: '/dashboard/studio',      icon: FileCode2   },
] as const

// ─── Types ────────────────────────────────────────────────────────────────────

interface NavigationRailProps {
  /** Notification count — 0 hides the badge */
  notificationCount?: number
  className?: string
}

// ─── Main component ───────────────────────────────────────────────────────────

export function NavigationRail({ notificationCount = 0, className }: NavigationRailProps) {
  const pathname = usePathname()
  const [expanded, setExpanded]   = React.useState(false)
  const [profileOpen, setProfileOpen] = React.useState(false)

  const { theme, toggleTheme } = useThemeStore()
  const { user }               = useUser()
  const railRef                = React.useRef<HTMLDivElement>(null)

  // Collapse when clicking outside
  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (railRef.current && !railRef.current.contains(e.target as Node)) {
        setExpanded(false)
        setProfileOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Expand on hover, collapse on leave
  const handleMouseEnter = React.useCallback(() => {
    setExpanded(true)
  }, [])

  const handleMouseLeave = React.useCallback(() => {
    setExpanded(false)
    setProfileOpen(false)
  }, [])

  return (
    <nav
      ref={railRef}
      style={{ width: expanded ? '240px' : '64px' }}
      className={cn(
        'fixed left-0 top-0 bottom-0 z-40',
        'flex flex-col',
        'bg-surface border-r border-border',
        'transition-[width] duration-200 ease-spring overflow-hidden',
        className,
      )}
      aria-label="Main navigation"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* ── Logo ──────────────────────────────────────────────── */}
      <div className="flex items-center h-16 px-[14px] shrink-0">
        <button
          onClick={() => setExpanded(p => !p)}
          className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
          aria-label="Toggle navigation"
        >
          <StemIcon size={20} className="text-white" />
        </button>
        {expanded && (
          <span className="ml-3 text-sm font-medium text-heading whitespace-nowrap animate-fade-up">
            Cogent
          </span>
        )}
      </div>

      <Separator />

      {/* ── Primary nav items ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col gap-0.5 py-3 px-2 overflow-y-auto">
        {NAV_ITEMS.map(item => {
          const isActive = pathname?.startsWith(item.href) ?? false
          const Icon     = item.icon

          return (
            <NavItem
              key={item.id}
              href={item.href}
              label={item.label}
              icon={<Icon size={18} strokeWidth={1.5} />}
              isActive={isActive}
              expanded={expanded}
            />
          )
        })}
      </div>

      <Separator />

      {/* ── Footer items ──────────────────────────────────────── */}
      <div className="flex flex-col gap-0.5 py-3 px-2">
        {/* Settings */}
        <NavItem
          href="/dashboard/settings"
          label="Settings"
          icon={<Settings size={18} strokeWidth={1.5} />}
          isActive={pathname?.startsWith('/dashboard/settings') ?? false}
          expanded={expanded}
        />

        {/* Theme toggle */}
        <NavItemButton
          label={theme === 'light' ? 'Dark Mode' : 'Light Mode'}
          expanded={expanded}
          icon={theme === 'light'
            ? <Moon size={18} strokeWidth={1.5} />
            : <Sun  size={18} strokeWidth={1.5} />}
          onClick={toggleTheme}
        />

        {/* Logout */}
        <NavItemButton
          label="Sign Out"
          expanded={expanded}
          icon={<LogOut size={18} strokeWidth={1.5} />}
          onClick={() => { window.location.href = '/api/auth/logout' }}
          destructive
        />
      </div>

      <Separator />

      {/* ── User profile card ─────────────────────────────────── */}
      <div className="relative px-2 py-3">
        <Link
          href="/dashboard/settings?tab=profile"
          className={cn(
            'w-full flex items-center gap-3 rounded-lg px-2 py-2',
            'hover:bg-muted transition-colors text-left',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
          )}
          onClick={() => setProfileOpen(false)}
        >
          <Avatar
            src={user?.picture}
            alt={user?.name ?? 'User'}
            size="sm"
            className="shrink-0"
          />
          {expanded && (
            <div className="flex-1 min-w-0 animate-fade-up">
              <p className="text-xs font-medium text-heading truncate leading-tight">
                {user?.name ?? 'Loading...'}
              </p>
              <p className="text-[11px] text-subtle truncate leading-tight mt-0.5">
                {user?.email ?? ''}
              </p>
            </div>
          )}
          {expanded && (
            <ChevronRight size={14} className="text-subtle shrink-0 animate-fade-up" />
          )}
        </Link>

        {/* Profile popover — still accessible via click on ChevronRight */}
        <button
          onClick={() => setProfileOpen(p => !p)}
          className="absolute right-2 bottom-5 p-1 text-subtle hover:text-body transition-colors"
          aria-label="Open profile menu"
        >
        </button>

        {/* Profile popover */}
        {profileOpen && (
          <ProfilePopover
            user={user}
            expanded={expanded}
            onClose={() => setProfileOpen(false)}
          />
        )}
      </div>
    </nav>
  )
}

// ─── Nav link item (router link) ─────────────────────────────────────────────

interface NavItemProps {
  href: string
  label: string
  icon: React.ReactNode
  isActive: boolean
  expanded: boolean
}

function NavItem({ href, label, icon, isActive, expanded }: NavItemProps) {
  const content = (
    <Link
      href={href}
      className={cn(
        'relative flex items-center gap-3 rounded-lg px-2.5 py-2.5',
        'hover:bg-muted transition-colors group',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
        isActive && 'bg-primary/5',
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      {/* Active indicator bar */}
      {isActive && (
        <span
          aria-hidden="true"
          className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-full bg-primary"
        />
      )}

      {/* Icon */}
      <span className={cn(
        'shrink-0 transition-colors',
        isActive ? 'text-primary' : 'text-neutral group-hover:text-primary',
      )}>
        {icon}
      </span>

      {/* Label — only in expanded state */}
      {expanded && (
        <span className={cn(
          'text-sm whitespace-nowrap font-medium animate-fade-up',
          isActive ? 'text-primary' : 'text-body',
        )}>
          {label}
        </span>
      )}
    </Link>
  )

  // In collapsed mode, wrap in tooltip
  if (!expanded) {
    return (
      <Tooltip content={label} side="right">
        {content}
      </Tooltip>
    )
  }

  return content
}

// ─── Nav button item (action, no link) ───────────────────────────────────────

interface NavItemButtonProps {
  label: string
  icon: React.ReactNode
  expanded: boolean
  onClick: () => void
  badge?: number
  destructive?: boolean
}

function NavItemButton({ label, icon, expanded, onClick, badge, destructive }: NavItemButtonProps) {
  const content = (
    <button
      onClick={onClick}
      className={cn(
        'relative w-full flex items-center gap-3 rounded-lg px-2.5 py-2.5',
        'hover:bg-muted transition-colors group text-left',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50',
      )}
    >
      <span className={cn(
        'relative shrink-0 transition-colors',
        destructive
          ? 'text-neutral group-hover:text-critical'
          : 'text-neutral group-hover:text-primary',
      )}>
        {icon}
        {/* Notification badge */}
        {!!badge && badge > 0 && (
          <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-primary text-white text-[9px] font-medium flex items-center justify-center leading-none">
            {badge > 9 ? '9+' : badge}
          </span>
        )}
      </span>

      {expanded && (
        <span className={cn(
          'text-sm whitespace-nowrap font-medium animate-fade-up',
          destructive ? 'text-body group-hover:text-critical' : 'text-body',
        )}>
          {label}
        </span>
      )}
    </button>
  )

  if (!expanded) {
    return (
      <Tooltip content={label} side="right">
        {content}
      </Tooltip>
    )
  }

  return content
}

// ─── Profile popover ─────────────────────────────────────────────────────────

interface ProfilePopoverProps {
  user: ReturnType<typeof useUser>['user']
  expanded: boolean
  onClose: () => void
}

function ProfilePopover({ user, expanded, onClose }: ProfilePopoverProps) {

  const items = [
    { icon: User,       label: 'View Profile',    href: '/dashboard/settings?tab=profile' },
    { icon: CreditCard, label: 'Billing & Plans',  href: '/dashboard/settings?tab=billing' },
    { icon: KeyRound,   label: 'Security',         href: '/dashboard/settings?tab=security' },
    { icon: Settings,   label: 'All Settings',     href: '/dashboard/settings' },
  ] as const

  return (
    <div
      className={cn(
        'absolute z-50 bottom-full mb-2',
        'bg-surface border border-border shadow-modal rounded-lg py-2',
        'animate-fade-up',
        expanded ? 'left-2 right-2' : 'left-14 w-56',
      )}
    >
      {/* Profile header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <Avatar
          src={user?.picture}
          alt={user?.name ?? 'User'}
          size="md"
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-heading truncate">{user?.name ?? 'User'}</p>
          <p className="text-xs text-subtle truncate">{user?.email ?? ''}</p>
        </div>
      </div>

      <Separator />

      {/* Profile action items */}
      <div className="py-1">
        {items.map(item => (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClose}
            className="flex items-center gap-3 px-4 py-2 text-sm text-body hover:bg-muted hover:text-heading transition-colors"
          >
            <item.icon size={15} strokeWidth={1.5} className="text-neutral shrink-0" />
            {item.label}
          </Link>
        ))}
      </div>

      <Separator />

      {/* Sign out */}
      <div className="py-1">
        <a
          href="/api/auth/logout"
          className="flex items-center gap-3 px-4 py-2 text-sm text-body hover:bg-muted hover:text-critical transition-colors"
        >
          <LogOut size={15} strokeWidth={1.5} className="text-neutral shrink-0" />
          Sign out
        </a>
      </div>
    </div>
  )
}

// Cogent logo mark replaced by StemIcon component (see components/ui/StemIcon.tsx)
