'use client'

import { useCallback, useEffect, useState } from 'react'
import { Bell, CheckCheck, Loader2, RefreshCw } from 'lucide-react'

import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from '@/lib/api/notifications'
import { friendlyErrorMessage } from '@/lib/api/errors'
import { timeAgo } from '@/lib/utils'

const TYPE_STYLES: Record<NotificationItem['type'], string> = {
  signal: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  contract: 'bg-amber-50 text-amber-700 border-amber-200',
  system: 'bg-slate-100 text-slate-700 border-slate-200',
}

export function NotificationsSection() {
  const [items, setItems] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [markingId, setMarkingId] = useState<string | null>(null)
  const [markingAll, setMarkingAll] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async (background = false) => {
    if (background) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)

    try {
      const response = await listNotifications(30)
      setItems(response.items)
      setUnreadCount(response.unread_count)
    } catch (err) {
      setError(friendlyErrorMessage(err))
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  async function handleMarkRead(id: string) {
    setMarkingId(id)
    try {
      await markNotificationRead(id)
      setItems((previous) =>
        previous.map((item) => (item.id === id ? { ...item, unread: false } : item)),
      )
      setUnreadCount((previous) => Math.max(previous - 1, 0))
    } catch (err) {
      setError(friendlyErrorMessage(err))
    } finally {
      setMarkingId(null)
    }
  }

  async function handleMarkAllRead() {
    setMarkingAll(true)
    try {
      await markAllNotificationsRead()
      setItems((previous) => previous.map((item) => ({ ...item, unread: false })))
      setUnreadCount(0)
    } catch (err) {
      setError(friendlyErrorMessage(err))
    } finally {
      setMarkingAll(false)
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2">
              <Bell className="h-4 w-4 text-primary" strokeWidth={1.5} />
              <h3 className="text-sm font-medium text-heading">Notification Inbox</h3>
            </div>
            <p className="text-xs text-subtle">
              Review live signal, contract, and system notifications for your workspace.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-full border border-border bg-muted px-3 py-1 text-[11px] font-medium text-body">
              {unreadCount} unread
            </span>
            <button
              onClick={() => {
                void refresh(true)
              }}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-medium text-body transition-colors hover:bg-muted disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => {
                void handleMarkAllRead()
              }}
              disabled={markingAll || unreadCount === 0}
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
            >
              {markingAll ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCheck className="h-3.5 w-3.5" />}
              Mark all read
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs text-rose-600">
            {error}
          </div>
        )}

        {loading ? (
          <div className="mt-6 flex items-center gap-2 text-xs text-subtle">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading notifications...
          </div>
        ) : items.length === 0 ? (
          <div className="mt-6 rounded-xl border border-dashed border-border bg-muted/30 px-4 py-6 text-sm text-subtle">
            No notifications yet. New high-confidence signals and contract warnings will appear here.
          </div>
        ) : (
          <div className="mt-6 flex flex-col gap-3">
            {items.map((item) => (
              <div
                key={item.id}
                className={`rounded-xl border px-4 py-3 transition-colors ${
                  item.unread ? 'border-primary/20 bg-primary/5' : 'border-border bg-muted/20'
                }`}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${TYPE_STYLES[item.type]}`}>
                        {item.type}
                      </span>
                      {item.unread && (
                        <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">
                          New
                        </span>
                      )}
                    </div>
                    <p className="mt-2 text-sm font-medium text-heading">{item.title}</p>
                    <p className="mt-1 text-sm text-subtle">{item.body}</p>
                  </div>

                  <div className="flex flex-col items-start gap-2 sm:items-end">
                    <span className="text-[11px] text-subtle">{timeAgo(item.created_at)}</span>
                    <button
                      onClick={() => {
                        void handleMarkRead(item.id)
                      }}
                      disabled={!item.unread || markingId === item.id}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-primary transition-colors hover:underline disabled:opacity-40"
                    >
                      {markingId === item.id && <Loader2 className="h-3 w-3 animate-spin" />}
                      Mark read
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
