'use client'

import * as React from 'react'
import Link from 'next/link'
import { Search, Bell, CheckCheck, Zap, FileSignature, AlertCircle, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { LiveIndicator } from './LiveIndicator'
import { SpotlightSearch } from './SpotlightSearch'
import { listNotifications } from '@/lib/api/notifications'
import type { NotificationItem as APINotifItem } from '@/lib/api/notifications'
import { useAlerts } from '@/lib/hooks/useAlerts'

// ─── Types ────────────────────────────────────────────────────────────────────

interface NotifItem {
  id:      string
  icon:    React.ElementType
  color:   string
  title:   string
  body:    string
  time:    string
  unread:  boolean
}

function mapTypeToStyle(type: APINotifItem['type']): { icon: React.ElementType; color: string } {
  switch (type) {
    case 'signal':   return { icon: Zap,           color: 'text-primary bg-primary/8'     }
    case 'contract': return { icon: FileSignature,  color: 'text-emerald-600 bg-emerald-50' }
    case 'system':   return { icon: AlertCircle,    color: 'text-amber-600 bg-amber-50'    }
    default:         return { icon: Bell,            color: 'text-subtle bg-muted'          }
  }
}

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60_000)
  if (mins < 1)   return 'Just now'
  if (mins < 60)  return `${mins} min ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24)   return `${hrs} hr ago`
  const days = Math.floor(hrs / 24)
  return days === 1 ? 'Yesterday' : `${days} days ago`
}

function toNotifItem(n: APINotifItem): NotifItem {
  const { icon, color } = mapTypeToStyle(n.type)
  return { id: n.id, icon, color, title: n.title, body: n.body, time: relativeTime(n.created_at), unread: n.unread }
}

interface OmniBarProps {
  notificationCount?: number
  className?: string
}

// ─── Component ────────────────────────────────────────────────────────────────

export function OmniBar({ notificationCount = 0, className }: OmniBarProps) {
  const [query, setQuery]                 = React.useState('')
  const [spotlightOpen, setSpotlightOpen] = React.useState(false)
  const [notifOpen, setNotifOpen]         = React.useState(false)
  const [notifs, setNotifs]               = React.useState<NotifItem[]>([])
  const inputRef  = React.useRef<HTMLInputElement>(null)
  const barRef    = React.useRef<HTMLDivElement>(null)
  const notifRef  = React.useRef<HTMLDivElement>(null)

  const [activeTab, setActiveTab] = React.useState<'notifications' | 'alerts'>('notifications')
  const { data: alertData, acknowledge: acknowledgeAlertItem } = useAlerts({ acknowledged: false, limit: 50 })

  const unreadCount = notifs.filter(n => n.unread).length
  const alertUnread = alertData?.unacknowledged ?? 0
  const totalUnread = unreadCount + alertUnread

  // Fetch notifications from backend on mount
  React.useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await listNotifications(20)
        if (!cancelled) setNotifs(data.items.map(toNotifItem))
      } catch {
        // Backend unavailable — show empty state gracefully
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  // Close spotlight on outside click
  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setSpotlightOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Close notif dropdown on outside click
  React.useEffect(() => {
    function handler(e: MouseEvent) {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setNotifOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Open spotlight on any keystroke when input focused
  function handleInput(e: React.ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value)
    setSpotlightOpen(true)
  }

  function handleFocus() {
    setSpotlightOpen(true)
  }

  function markAllRead() {
    setNotifs(ns => ns.map(n => ({ ...n, unread: false })))
  }

  function dismissNotif(id: string) {
    setNotifs(ns => ns.filter(n => n.id !== id))
  }

  // Global shortcuts: '/' or ⌘K / Ctrl+K focuses input
  React.useEffect(() => {
    function handler(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement).tagName
      const isShortcutKey = (
        (e.key === '/' && tag !== 'INPUT' && tag !== 'TEXTAREA') ||
        (e.key === 'k' && (e.metaKey || e.ctrlKey))
      )
      if (isShortcutKey) {
        e.preventDefault()
        inputRef.current?.focus()
        setSpotlightOpen(true)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-30 h-16',
        // Mobile: full width. Desktop: offset from nav rail.
        'left-0 md:left-[var(--nav-rail-collapsed)]',
        'flex items-center gap-4 px-4 sm:px-6',
        'bg-surface/80 backdrop-blur-sm border-b border-border',
        'transition-all duration-200',
        className,
      )}
    >
      {/* ── Command input (centered) ──────────────────────────── */}
      <div
        ref={barRef}
        className="flex-1 flex justify-center"
      >
        <div
          className="relative w-full max-w-[600px]"
        >
          {/* Search icon */}
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-subtle pointer-events-none">
            <Search size={15} strokeWidth={1.5} />
          </span>

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInput}
            onFocus={handleFocus}
            placeholder="Ask about market trends, entities, or press '/' for commands..."
            aria-label="Intelligence search"
            aria-autocomplete="list"
            aria-controls={spotlightOpen ? 'spotlight-results' : undefined}
            className={cn(
              'w-full h-9 pl-9 pr-4 rounded-lg',
              'bg-muted text-sm text-body',
              'placeholder:text-subtle',
              'border border-transparent',
              'focus:outline-none focus:border-primary/40 focus:bg-surface',
              'transition-colors duration-150',
            )}
          />

          {/* Shortcut hint — visible when unfocused and empty */}
          {!query && !spotlightOpen && (
            <span
              aria-hidden="true"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[11px] text-subtle font-mono"
            >
              /
            </span>
          )}

          {/* Spotlight dropdown */}
          {spotlightOpen && (
            <SpotlightSearch
              query={query}
              onClose={() => {
                setSpotlightOpen(false)
                setQuery('')
              }}
              onNavigate={() => {
                setQuery('')
                setSpotlightOpen(false)
              }}
            />
          )}
        </div>
      </div>

      {/* ── Right section ─────────────────────────────────────── */}
      <div className="flex items-center gap-4 shrink-0">
        <LiveIndicator label="Data Freshness: Live" />

        {/* Notification bell */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => setNotifOpen(o => !o)}
            title="Notifications"
            aria-label={`Notifications${totalUnread ? ` — ${totalUnread} unread` : ''}`}
            className="relative p-1.5 rounded-lg hover:bg-muted transition-colors text-neutral hover:text-heading focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
          >
            <Bell size={18} strokeWidth={1.5} />
            {totalUnread > 0 && (
              <span className="absolute top-0.5 right-0.5 w-3.5 h-3.5 rounded-full bg-primary text-white text-[9px] font-medium flex items-center justify-center leading-none">
                {totalUnread > 9 ? '9+' : totalUnread}
              </span>
            )}
          </button>

          {/* Notifications + Alerts dropdown panel */}
          {notifOpen && (
            <div className="absolute right-0 top-full mt-2 w-96 rounded-2xl border border-border bg-surface shadow-modal z-50 overflow-hidden">

              {/* Tab header */}
              <div className="flex items-center justify-between border-b border-border px-4 py-3">
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setActiveTab('notifications')}
                    className={cn(
                      'text-sm font-medium transition-colors',
                      activeTab === 'notifications' ? 'text-heading' : 'text-subtle hover:text-body',
                    )}
                  >
                    Notifications
                    {unreadCount > 0 && (
                      <span className="ml-1.5 rounded-full bg-primary/15 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                        {unreadCount}
                      </span>
                    )}
                  </button>
                  <button
                    onClick={() => setActiveTab('alerts')}
                    className={cn(
                      'text-sm font-medium transition-colors',
                      activeTab === 'alerts' ? 'text-heading' : 'text-subtle hover:text-body',
                    )}
                  >
                    Alerts
                    {alertUnread > 0 && (
                      <span className="ml-1.5 rounded-full bg-red-100 px-1.5 py-0.5 text-[10px] font-medium text-red-700">
                        {alertUnread}
                      </span>
                    )}
                  </button>
                </div>
                <div className="flex items-center gap-3">
                  {activeTab === 'notifications' && unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
                    >
                      <CheckCheck className="h-3 w-3" />
                      Mark all read
                    </button>
                  )}
                  <button
                    onClick={() => setNotifOpen(false)}
                    className="text-subtle hover:text-body transition-colors"
                  >
                    <X className="h-4 w-4" strokeWidth={1.5} />
                  </button>
                </div>
              </div>

              {/* Notifications tab */}
              {activeTab === 'notifications' && (
                <div className="max-h-80 overflow-y-auto divide-y divide-border">
                  {notifs.length === 0 ? (
                    <div className="py-10 text-center text-sm text-subtle">All caught up ✓</div>
                  ) : notifs.map(n => (
                    <div
                      key={n.id}
                      className={`flex items-start gap-3 px-4 py-3 transition-colors hover:bg-muted/50 ${
                        n.unread ? 'bg-primary/[0.02]' : ''
                      }`}
                    >
                      <div className={`mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg ${n.color}`}>
                        <n.icon className="h-4 w-4" strokeWidth={1.5} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-medium text-heading truncate">{n.title}</p>
                          <span className="flex-shrink-0 text-[10px] text-subtle">{n.time}</span>
                        </div>
                        <p className="mt-0.5 text-[11px] leading-relaxed text-subtle line-clamp-2">{n.body}</p>
                      </div>
                      <button
                        onClick={() => dismissNotif(n.id)}
                        className="mt-0.5 flex-shrink-0 text-subtle opacity-0 group-hover:opacity-100 hover:text-body transition-all"
                      >
                        <X className="h-3.5 w-3.5" strokeWidth={1.5} />
                      </button>
                      {n.unread && (
                        <span className="mt-1.5 flex-shrink-0 h-2 w-2 rounded-full bg-primary" />
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Alerts tab */}
              {activeTab === 'alerts' && (
                <div className="max-h-80 overflow-y-auto divide-y divide-border">
                  {(alertData?.items ?? []).length === 0 ? (
                    <div className="py-10 text-center text-sm text-subtle">No active alerts ✓</div>
                  ) : (alertData?.items ?? []).map(alert => {
                    const sevDot: Record<string, string> = {
                      critical: 'bg-red-500',
                      high:     'bg-orange-400',
                      medium:   'bg-yellow-400',
                      low:      'bg-blue-400',
                    }
                    const sevBadge: Record<string, string> = {
                      critical: 'text-red-700 bg-red-50 border-red-200',
                      high:     'text-orange-700 bg-orange-50 border-orange-200',
                      medium:   'text-yellow-700 bg-yellow-50 border-yellow-200',
                      low:      'text-blue-700 bg-blue-50 border-blue-200',
                    }
                    return (
                      <div key={alert.id} className="flex items-start gap-3 px-4 py-3 hover:bg-muted/50 transition-colors">
                        <span className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${sevDot[alert.severity] ?? 'bg-gray-400'}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-heading truncate">{alert.title}</p>
                          <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                            <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${sevBadge[alert.severity] ?? 'text-gray-600 bg-gray-50 border-gray-200'}`}>
                              {alert.severity}
                            </span>
                            {alert.metric && <span className="text-[10px] font-mono text-subtle">{alert.metric}</span>}
                            {alert.country_code && <span className="text-[10px] text-subtle">{alert.country_code}</span>}
                          </div>
                          <p className="mt-0.5 text-[10px] text-subtle">{relativeTime(alert.created_at)}</p>
                        </div>
                        <button
                          onClick={() => acknowledgeAlertItem(alert.id)}
                          title="Acknowledge alert"
                          className="mt-0.5 flex-shrink-0 p-1 rounded hover:bg-green-50 text-subtle hover:text-green-600 transition-colors"
                        >
                          <CheckCheck className="h-3.5 w-3.5" strokeWidth={1.5} />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Footer */}
              <div className="border-t border-border px-4 py-2.5">
                {activeTab === 'notifications' ? (
                  <Link
                    href="/dashboard/settings?tab=notifications"
                    onClick={() => setNotifOpen(false)}
                    className="block text-center text-xs font-medium text-primary hover:underline"
                  >
                    Manage notification settings
                  </Link>
                ) : (
                  <Link
                    href="/dashboard/alerts"
                    onClick={() => setNotifOpen(false)}
                    className="block text-center text-xs font-medium text-primary hover:underline"
                  >
                    View all alerts
                  </Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
