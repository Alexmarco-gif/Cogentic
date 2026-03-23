'use client'

import * as React from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  Bell,
  CheckCheck,
  FileSignature,
  Plus,
  Search,
  X,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { LiveIndicator } from './LiveIndicator'
import { SpotlightSearch } from './SpotlightSearch'
import { listNotifications } from '@/lib/api/notifications'
import type { NotificationItem as APINotifItem } from '@/lib/api/notifications'
import { useAlerts } from '@/lib/hooks/useAlerts'

interface NotifItem {
  id: string
  icon: React.ElementType
  color: string
  title: string
  body: string
  time: string
  unread: boolean
}

function mapTypeToStyle(type: APINotifItem['type']): { icon: React.ElementType; color: string } {
  switch (type) {
    case 'signal':
      return { icon: Zap, color: 'bg-primary/10 text-primary' }
    case 'contract':
      return { icon: FileSignature, color: 'bg-success/10 text-success' }
    case 'system':
      return { icon: AlertCircle, color: 'bg-warning/10 text-warning' }
    default:
      return { icon: Bell, color: 'bg-surface-2 text-subtle' }
  }
}

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return days === 1 ? 'Yesterday' : `${days}d ago`
}

function toNotifItem(item: APINotifItem): NotifItem {
  const { icon, color } = mapTypeToStyle(item.type)
  return {
    id: item.id,
    icon,
    color,
    title: item.title,
    body: item.body,
    time: relativeTime(item.created_at),
    unread: item.unread,
  }
}

interface OmniBarProps {
  notificationCount?: number
  className?: string
}

export function OmniBar({ notificationCount = 0, className }: OmniBarProps) {
  const [query, setQuery] = React.useState('')
  const [spotlightOpen, setSpotlightOpen] = React.useState(false)
  const [notifOpen, setNotifOpen] = React.useState(false)
  const [notifs, setNotifs] = React.useState<NotifItem[]>([])
  const [activeTab, setActiveTab] = React.useState<'notifications' | 'alerts'>('notifications')
  const inputRef = React.useRef<HTMLInputElement>(null)
  const barRef = React.useRef<HTMLDivElement>(null)
  const notifRef = React.useRef<HTMLDivElement>(null)
  const { data: alertData, acknowledge: acknowledgeAlertItem } = useAlerts({
    acknowledged: false,
    limit: 50,
  })

  const unreadCount = notifs.filter((notif) => notif.unread).length
  const alertUnread = alertData?.unacknowledged ?? 0
  const totalUnread = unreadCount + alertUnread + notificationCount

  React.useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const data = await listNotifications(20)
        if (!cancelled) {
          setNotifs(data.items.map(toNotifItem))
        }
      } catch {
        // Keep the shell usable if the notification feed is unavailable.
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setSpotlightOpen(false)
      }
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false)
      }
    }

    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  React.useEffect(() => {
    function handler(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      const isShortcut = (
        (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') ||
        (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey))
      )

      if (isShortcut) {
        e.preventDefault()
        inputRef.current?.focus()
        setSpotlightOpen(true)
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  function markAllRead() {
    setNotifs((items) => items.map((item) => ({ ...item, unread: false })))
  }

  function dismissNotif(id: string) {
    setNotifs((items) => items.filter((item) => item.id !== id))
  }

  return (
    <header
      className={cn(
        'fixed left-0 right-0 top-0 z-30 md:left-[var(--nav-rail-collapsed)]',
        'px-3 pt-3 sm:px-5 md:px-6',
        className,
      )}
    >
      <div className="mx-auto flex h-[calc(var(--omnibar-height)-12px)] max-w-shell items-center gap-3 rounded-[28px] border border-border bg-[rgba(252,251,247,0.78)] px-4 shadow-card backdrop-blur-xl dark:bg-[rgba(23,32,29,0.82)] sm:px-5">
        <div ref={barRef} className="relative flex-1">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-subtle">
            <Search size={16} strokeWidth={1.8} />
          </span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSpotlightOpen(true)
            }}
            onFocus={() => setSpotlightOpen(true)}
            placeholder="Search intelligence, open pages, or run a command"
            aria-label="Search and command palette"
            aria-autocomplete="list"
            aria-controls={spotlightOpen ? 'spotlight-results' : undefined}
            className="focus-ring h-12 w-full rounded-[20px] border border-transparent bg-surface-2 pl-11 pr-24 text-[0.92rem] text-heading placeholder:text-subtle transition-all duration-200 focus:border-primary/20 focus:bg-surface"
          />
          <div className="pointer-events-none absolute right-3 top-1/2 flex -translate-y-1/2 items-center gap-2">
            <kbd className="hidden rounded-full border border-border bg-surface px-2.5 py-1 text-[0.66rem] font-semibold uppercase tracking-[0.18em] text-subtle sm:inline-flex">
              Ctrl K
            </kbd>
            {!query && (
              <span className="hidden text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle md:inline">
                /
              </span>
            )}
          </div>

          {spotlightOpen && (
            <SpotlightSearch
              query={query}
              onClose={() => {
                setSpotlightOpen(false)
                setQuery('')
              }}
              onNavigate={() => {
                setSpotlightOpen(false)
                setQuery('')
              }}
            />
          )}
        </div>

        <div className="hidden items-center gap-2 lg:flex">
          <div className="rounded-full border border-border bg-surface px-3 py-1.5">
            <LiveIndicator label="Live intelligence" className="border-0 bg-transparent px-0 py-0 shadow-none" />
          </div>
          <Link
            href="/dashboard/studio"
            className="button-press inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-[0.8rem] font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
          >
            <Plus size={14} />
            Create contract
          </Link>
        </div>

        <div ref={notifRef} className="relative shrink-0">
          <button
            onClick={() => setNotifOpen((open) => !open)}
            title="Notifications"
            aria-label={`Notifications${totalUnread ? ` - ${totalUnread} unread` : ''}`}
            className="focus-ring button-press relative flex h-11 w-11 items-center justify-center rounded-2xl border border-border bg-surface text-neutral transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2 hover:text-heading"
          >
            <Bell size={18} strokeWidth={1.8} />
            {totalUnread > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 min-w-[1rem] items-center justify-center rounded-full bg-primary px-1 text-[0.6rem] font-bold text-white">
                {totalUnread > 9 ? '9+' : totalUnread}
              </span>
            )}
          </button>

          {notifOpen && (
            <div className="surface-elevated absolute right-0 top-full z-50 mt-3 w-[min(92vw,30rem)] overflow-hidden p-2">
              <div className="flex items-center justify-between rounded-[20px] bg-surface-2 px-4 py-3">
                <div>
                  <p className="text-title">Inbox</p>
                  <p className="text-[0.78rem] text-subtle">Everything that changed since your last visit.</p>
                </div>
                <button
                  onClick={() => setNotifOpen(false)}
                  className="focus-ring button-press rounded-full p-2 text-subtle transition-colors hover:bg-surface hover:text-heading"
                >
                  <X size={16} strokeWidth={1.8} />
                </button>
              </div>

              <div className="mt-2 flex items-center gap-2 px-1">
                {(['notifications', 'alerts'] as const).map((tab) => {
                  const count = tab === 'notifications' ? unreadCount : alertUnread
                  const active = activeTab === tab
                  return (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={cn(
                        'button-press inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-[0.78rem] font-semibold capitalize transition-all duration-200',
                        active
                          ? 'bg-primary text-white shadow-glow'
                          : 'border border-border bg-surface text-body hover:bg-surface-2',
                      )}
                    >
                      {tab}
                      {count > 0 && (
                        <span className={cn(
                          'rounded-full px-1.5 py-0.5 text-[0.64rem]',
                          active ? 'bg-white/15 text-white' : 'bg-surface-2 text-subtle',
                        )}>
                          {count}
                        </span>
                      )}
                    </button>
                  )
                })}

                {activeTab === 'notifications' && unreadCount > 0 && (
                  <button
                    onClick={markAllRead}
                    className="ml-auto inline-flex items-center gap-1.5 text-[0.76rem] font-semibold text-primary transition-colors hover:text-primary-hover"
                  >
                    <CheckCheck size={14} />
                    Mark all read
                  </button>
                )}
              </div>

              {activeTab === 'notifications' ? (
                <div className="mt-3 max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                  {notifs.length === 0 ? (
                    <EmptyInbox
                      title="You're caught up"
                      body="New contract updates, signal alerts, and system events will land here."
                    />
                  ) : (
                    notifs.map((notif) => (
                      <div
                        key={notif.id}
                        className={cn(
                          'group rounded-[20px] border border-border bg-surface px-4 py-3 transition-all duration-200 hover:border-border-hover hover:bg-surface-2',
                          notif.unread && 'bg-primary/[0.03]',
                        )}
                      >
                        <div className="flex items-start gap-3">
                          <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl', notif.color)}>
                            <notif.icon size={16} strokeWidth={1.8} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="truncate text-[0.86rem] font-semibold text-heading">{notif.title}</p>
                                <p className="mt-1 line-clamp-2 text-[0.78rem] text-subtle">{notif.body}</p>
                              </div>
                              <span className="shrink-0 text-[0.72rem] text-subtle">{notif.time}</span>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            {notif.unread && <span className="h-2.5 w-2.5 rounded-full bg-primary" />}
                            <button
                              onClick={() => dismissNotif(notif.id)}
                              className="text-subtle opacity-0 transition-all group-hover:opacity-100 hover:text-heading"
                            >
                              <X size={14} strokeWidth={1.8} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              ) : (
                <div className="mt-3 max-h-[24rem] space-y-2 overflow-y-auto pr-1">
                  {(alertData?.items ?? []).length === 0 ? (
                    <EmptyInbox
                      title="No active alerts"
                      body="When premium alerts trigger, they'll show here with severity and source context."
                    />
                  ) : (
                    (alertData?.items ?? []).map((alert) => {
                      const tone = alert.severity === 'critical'
                        ? 'bg-critical/10 text-critical'
                        : alert.severity === 'high'
                        ? 'bg-warning/10 text-warning'
                        : 'bg-primary/10 text-primary'

                      return (
                        <button
                          key={alert.id}
                          onClick={() => acknowledgeAlertItem(alert.id)}
                          className="button-press flex w-full items-start gap-3 rounded-[20px] border border-border bg-surface px-4 py-3 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
                        >
                          <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl', tone)}>
                            <AlertCircle size={16} strokeWidth={1.8} />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center justify-between gap-3">
                              <p className="truncate text-[0.86rem] font-semibold text-heading">{alert.title}</p>
                              <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[0.68rem] font-semibold uppercase tracking-[0.16em] text-subtle">
                                {alert.severity}
                              </span>
                            </div>
                            <p className="mt-1 line-clamp-2 text-[0.78rem] text-subtle">{alert.description}</p>
                          </div>
                        </button>
                      )
                    })
                  )}
                </div>
              )}

              <div className="mt-3 flex items-center justify-between border-t border-border px-2 pt-3">
                <p className="text-[0.74rem] text-subtle">Press Ctrl/Cmd + K to move faster.</p>
                <Link
                  href="/dashboard/settings?tab=notifications"
                  className="text-[0.78rem] font-semibold text-primary transition-colors hover:text-primary-hover"
                >
                  Manage settings
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

function EmptyInbox({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[20px] border border-dashed border-border bg-surface px-5 py-10 text-center">
      <p className="text-[0.9rem] font-semibold text-heading">{title}</p>
      <p className="mx-auto mt-2 max-w-sm text-[0.78rem] text-subtle">{body}</p>
    </div>
  )
}
