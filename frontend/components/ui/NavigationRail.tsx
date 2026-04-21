'use client'

import * as React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useUser } from '@auth0/nextjs-auth0/client'
import {
  Activity,
  BarChart3,
  BookOpen,
  ChevronRight,
  CreditCard,
  FileCode2,
  Globe,
  Home,
  KeyRound,
  LogOut,
  Moon,
  Radar,
  Search,
  Settings,
  ShoppingBag,
  Sun,
  User,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Tooltip } from './Tooltip'
import { Avatar } from './Avatar'
import { StemIcon } from './StemIcon'
import { useThemeStore } from '@/lib/stores/themeStore'

const NAV_ITEMS = [
  { id: 'home', label: 'Home', href: '/dashboard/home', icon: Home, section: 'Workspace' },
  { id: 'investigate', label: 'Investigate', href: '/dashboard/investigate', icon: Search, section: 'Workspace' },
  { id: 'signals', label: 'Signals', href: '/dashboard/signals', icon: Activity, section: 'Workspace' },
  { id: 'studio', label: 'Studio', href: '/dashboard/studio', icon: FileCode2, section: 'Workspace' },
  { id: 'marketplace', label: 'Marketplace', href: '/dashboard/marketplace', icon: ShoppingBag, section: 'Explore' },
  { id: 'discovery', label: 'Discovery', href: '/dashboard/discovery', icon: Radar, section: 'Explore' },
  { id: 'market-data', label: 'Market Data', href: '/dashboard/market-data', icon: BarChart3, section: 'Explore' },
  { id: 'domains', label: 'Domains', href: '/dashboard/domains', icon: Globe, section: 'Explore' },
  { id: 'library', label: 'Library', href: '/dashboard/library', icon: BookOpen, section: 'Explore' },
] as const

interface NavigationRailProps {
  notificationCount?: number
  className?: string
}

export function NavigationRail({ notificationCount = 0, className }: NavigationRailProps) {
  const pathname = usePathname()
  const [expanded, setExpanded] = React.useState(false)
  const [profileOpen, setProfileOpen] = React.useState(false)
  const { theme, toggleTheme } = useThemeStore()
  const { user } = useUser()
  const railRef = React.useRef<HTMLDivElement>(null)

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

  const groups = {
    Workspace: NAV_ITEMS.filter((item) => item.section === 'Workspace'),
    Explore: NAV_ITEMS.filter((item) => item.section === 'Explore'),
  }
  const collapsed = !expanded

  return (
    <nav
      ref={railRef}
      style={{ width: expanded ? 'var(--nav-rail-expanded)' : 'var(--nav-rail-collapsed)' }}
      className={cn(
        'fixed inset-y-0 left-0 z-40 flex flex-col overflow-hidden border-r border-border bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(248,250,252,0.98))] shadow-rail backdrop-blur-xl dark:bg-[linear-gradient(180deg,rgba(17,24,39,0.96),rgba(11,18,32,0.98))]',
        'transition-[width] duration-300 ease-spring',
        className,
      )}
      aria-label="Main navigation"
      onFocusCapture={() => setExpanded(true)}
      onMouseEnter={() => setExpanded(true)}
      onPointerEnter={() => setExpanded(true)}
      onMouseLeave={() => {
        setExpanded(false)
        setProfileOpen(false)
      }}
    >
      <div className={cn('pb-3 pt-4', expanded ? 'px-2.5' : 'px-3')}>
        <div className={cn('glass rounded-[26px] py-2.5', expanded ? 'px-2' : 'px-1.5')}>
          <div className={cn('flex items-center py-1.5', expanded ? 'gap-3 px-2' : 'justify-center')}>
            <button
              onClick={() => setExpanded((value) => !value)}
              className={cn(
                'focus-ring button-press flex shrink-0 items-center justify-center overflow-hidden border border-border/80 bg-white shadow-[0_18px_42px_-28px_rgba(37,99,235,0.45)] transition-all duration-200 dark:bg-surface-2',
                expanded ? 'h-12 w-12 rounded-[18px]' : 'h-11 w-11 rounded-[18px]',
              )}
              aria-label="Toggle navigation"
            >
              <StemIcon size={expanded ? 28 : 26} variant="brand" aria-label="Cogent" />
            </button>
            {expanded && (
              <div className="animate-fade-up min-w-0">
                <p className="text-title text-heading">Cogent</p>
                <p className="text-[0.78rem] text-subtle">Strategic operating system</p>
              </div>
            )}
          </div>

          {expanded && (
            <Link
              href="/dashboard/studio"
              className="button-press mt-2 flex items-center justify-between rounded-2xl bg-primary px-4 py-3 text-[0.84rem] font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
            >
              <span>Create contract</span>
              <ChevronRight size={16} />
            </Link>
          )}
        </div>
      </div>

      <div className={cn('flex-1 overflow-y-auto pb-4', expanded ? 'px-2.5' : 'px-3')}>
        {Object.entries(groups).map(([label, items]) => (
          <div
            key={label}
            className={cn(
              'mb-4',
              collapsed && 'mb-5',
            )}
          >
            {expanded && (
              <p className="eyebrow px-3 pb-2 pt-1.5">{label}</p>
            )}
            {!expanded && label === 'Explore' && (
              <div className="mx-auto mb-3 h-px w-8 rounded-full bg-border/80" aria-hidden="true" />
            )}
            <div className={cn('space-y-1', collapsed && 'space-y-2')}>
              {items.map((item) => {
                const Icon = item.icon
                const isActive = pathname?.startsWith(item.href) ?? false
                const badge = item.id === 'signals' ? notificationCount : undefined

                return (
                  <NavItem
                    key={item.id}
                    href={item.href}
                    label={item.label}
                    icon={<Icon size={18} strokeWidth={1.7} />}
                    isActive={isActive}
                    expanded={expanded}
                    badge={badge}
                  />
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div className={cn('border-t border-border', expanded ? 'px-2.5 py-2.5' : 'px-3 py-3')}>
        <div className={cn('space-y-1', collapsed && 'space-y-2')}>
          <NavButton
            label={theme === 'light' ? 'Dark mode' : 'Light mode'}
            expanded={expanded}
            icon={theme === 'light'
              ? <Moon size={18} strokeWidth={1.7} />
              : <Sun size={18} strokeWidth={1.7} />}
            onClick={toggleTheme}
          />
          <NavItem
            href="/dashboard/settings"
            label="Settings"
            icon={<Settings size={18} strokeWidth={1.7} />}
            isActive={pathname?.startsWith('/dashboard/settings') ?? false}
            expanded={expanded}
          />
          <NavButton
            label="Sign out"
            expanded={expanded}
            icon={<LogOut size={18} strokeWidth={1.7} />}
            onClick={() => {
              window.location.href = '/api/auth/logout'
            }}
            destructive
          />
        </div>

        <div className={cn('relative', expanded ? 'mt-2.5' : 'mt-3')}>
          <button
            onClick={() => setProfileOpen((open) => !open)}
            className={cn(
              'focus-ring button-press flex w-full items-center gap-3 rounded-[20px] border border-border bg-surface px-2.5 py-2.5 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2',
              !expanded && 'mx-auto h-12 w-12 justify-center rounded-[22px] px-0 py-0',
            )}
          >
            <Avatar
              src={user?.picture}
              alt={user?.name ?? 'User'}
              size="sm"
              className="shrink-0"
            />
            {expanded && (
              <>
                <div className="min-w-0 flex-1 animate-fade-up">
                  <p className="truncate text-[0.86rem] font-semibold text-heading">
                    {user?.name ?? 'Your workspace'}
                  </p>
                  <p className="truncate text-[0.74rem] text-subtle">
                    {user?.email ?? 'Manage profile and plan'}
                  </p>
                </div>
                <ChevronRight size={15} className="shrink-0 text-subtle" />
              </>
            )}
          </button>

          {profileOpen && (
            <ProfilePopover
              user={user}
              expanded={expanded}
              onClose={() => setProfileOpen(false)}
            />
          )}
        </div>
      </div>
    </nav>
  )
}

interface NavItemProps {
  href: string
  label: string
  icon: React.ReactNode
  isActive: boolean
  expanded: boolean
  badge?: number
}

function NavItem({ href, label, icon, isActive, expanded, badge }: NavItemProps) {
  const content = (
    <Link
      href={href}
      className={cn(
        'group relative flex min-h-[48px] w-full items-center gap-3 rounded-[18px] px-3 py-3 transition-all duration-200 ease-spring',
        'focus-ring hover:-translate-y-0.5 hover:bg-surface-2',
        isActive
          ? 'bg-[linear-gradient(135deg,rgba(37,99,235,0.14),rgba(37,99,235,0.05))] text-primary shadow-[inset_0_0_0_1px_rgba(37,99,235,0.2)]'
          : 'text-body',
        !expanded && 'mx-auto h-11 min-h-[44px] w-11 justify-center rounded-[16px] px-0 py-0',
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      <span className={cn(
        'relative shrink-0',
        isActive ? 'text-primary' : 'text-neutral group-hover:text-heading',
      )}>
        {icon}
        {!!badge && badge > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-primary px-1 text-[0.6rem] font-bold text-white">
            {badge > 9 ? '9+' : badge}
          </span>
        )}
      </span>

      {expanded && (
        <>
          <span className={cn(
            'min-w-0 flex-1 truncate text-[0.86rem] font-semibold',
            isActive ? 'text-primary' : 'text-body',
          )}>
            {label}
          </span>
          {isActive && <span className="h-2 w-2 rounded-full bg-primary" aria-hidden="true" />}
        </>
      )}
    </Link>
  )

  if (!expanded) {
    return (
      <div className="w-full">
        <Tooltip content={label} side="right">
          {content}
        </Tooltip>
      </div>
    )
  }

  return content
}

interface NavButtonProps {
  label: string
  icon: React.ReactNode
  expanded: boolean
  onClick: () => void
  destructive?: boolean
}

function NavButton({ label, icon, expanded, onClick, destructive = false }: NavButtonProps) {
  const content = (
    <button
      onClick={onClick}
      className={cn(
        'focus-ring button-press group flex min-h-[48px] w-full items-center gap-3 rounded-[18px] px-3 py-3 text-left transition-all duration-200 ease-spring',
        destructive
          ? 'text-body hover:bg-critical/10 hover:text-critical'
          : 'text-body hover:bg-surface-2 hover:text-heading',
        !expanded && 'mx-auto h-11 min-h-[44px] w-11 justify-center rounded-[16px] px-0 py-0',
      )}
    >
      <span className={cn(
        destructive ? 'text-neutral group-hover:text-critical' : 'text-neutral group-hover:text-heading',
      )}>
        {icon}
      </span>
      {expanded && <span className="text-[0.84rem] font-semibold">{label}</span>}
    </button>
  )

  if (!expanded) {
    return (
      <div className="w-full">
        <Tooltip content={label} side="right">
          {content}
        </Tooltip>
      </div>
    )
  }

  return content
}

interface ProfilePopoverProps {
  user: ReturnType<typeof useUser>['user']
  expanded: boolean
  onClose: () => void
}

function ProfilePopover({ user, expanded, onClose }: ProfilePopoverProps) {
  const items = [
    { icon: User, label: 'Profile', href: '/dashboard/settings?tab=profile' },
    { icon: CreditCard, label: 'Billing', href: '/dashboard/settings?tab=billing' },
    { icon: KeyRound, label: 'Security', href: '/dashboard/settings?tab=security' },
    { icon: Settings, label: 'All settings', href: '/dashboard/settings' },
  ] as const

  return (
    <div
      className={cn(
        'surface-elevated absolute bottom-full z-50 mb-3 overflow-hidden p-2 animate-fade-up',
        expanded ? 'left-0 right-0' : 'left-[72px] w-60',
      )}
    >
      <div className="rounded-[20px] bg-surface-2 px-3 py-3">
        <p className="truncate text-[0.88rem] font-semibold text-heading">{user?.name ?? 'Cogent user'}</p>
        <p className="truncate text-[0.74rem] text-subtle">{user?.email ?? 'Manage your workspace'}</p>
      </div>

      <div className="mt-2 space-y-1">
        {items.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={onClose}
            className="focus-ring button-press flex items-center gap-3 rounded-[18px] px-3 py-3 text-[0.84rem] font-semibold text-body transition-all duration-200 hover:bg-surface-2 hover:text-heading"
          >
            <item.icon size={16} strokeWidth={1.7} className="shrink-0 text-neutral" />
            <span>{item.label}</span>
          </Link>
        ))}
      </div>

      <button
        onClick={() => {
          onClose()
          window.location.href = '/api/auth/logout'
        }}
        className="focus-ring button-press mt-2 flex w-full items-center gap-3 rounded-[18px] px-3 py-3 text-[0.84rem] font-semibold text-body transition-all duration-200 hover:bg-critical/10 hover:text-critical"
      >
        <LogOut size={16} strokeWidth={1.7} className="shrink-0 text-neutral" />
        Sign out
      </button>
    </div>
  )
}
