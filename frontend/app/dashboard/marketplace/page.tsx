'use client'

import { useState, useCallback } from 'react'
import { ShoppingBag, Search, Star, Globe, RefreshCw, CheckCircle2, Plus, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  listTemplates,
  listSubscriptions,
  subscribeToTemplate,
  unsubscribeFromTemplate,
  type SignalTemplateResponse,
} from '@/lib/api'
import { useEffect } from 'react'


const TIER_LABELS: Record<string, { label: string; color: string }> = {
  realtime: { label: 'Real-time', color: 'text-emerald-400' },
  standard: { label: 'Hourly',    color: 'text-blue-400'    },
  slow:     { label: '6-hourly',  color: 'text-amber-400'   },
  daily:    { label: 'Daily',     color: 'text-purple-400'  },
}

const TYPE_COLORS: Record<string, string> = {
  financial:   'bg-blue-500/15 text-blue-300 border-blue-500/30',
  regulatory:  'bg-orange-500/15 text-orange-300 border-orange-500/30',
  market:      'bg-green-500/15 text-green-300 border-green-500/30',
  news:        'bg-slate-500/15 text-slate-300 border-slate-500/30',
  technology:  'bg-violet-500/15 text-violet-300 border-violet-500/30',
}

// ── Template Card ─────────────────────────────────────────────────────────────

function TemplateCard({
  template,
  onSubscribe,
  onUnsubscribe,
  loading,
}: {
  template: SignalTemplateResponse
  onSubscribe: (id: string) => void
  onUnsubscribe: (id: string) => void
  loading: boolean
}) {
  const flag    = template.primary_country ? (COUNTRY_FLAGS[template.primary_country] ?? '🌍') : '🌍'
  const country = template.primary_country ? (COUNTRY_NAMES[template.primary_country] ?? template.primary_country) : 'Pan-Africa'
  const tier    = TIER_LABELS[template.schedule_tier] ?? { label: template.schedule_tier, color: 'text-gray-400' }
  const typeStyle = TYPE_COLORS[template.signal_type] ?? 'bg-gray-500/15 text-gray-300 border-gray-500/30'

  return (
    <div
      className={cn(
        'group relative flex flex-col rounded-xl border bg-surface-2 p-5 transition-all',
        template.is_subscribed
          ? 'border-emerald-500/40 bg-emerald-500/5'
          : 'border-border hover:border-border-hover',
      )}
    >
      {/* Featured badge */}
      {template.is_featured && (
        <span className="absolute right-4 top-4 flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-300">
          <Star size={10} className="fill-amber-300" />
          Featured
        </span>
      )}

      {/* Header */}
      <div className="mb-3 flex items-start gap-3">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-surface-3 text-xl">
          {flag}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold text-heading">
            {template.name}
          </h3>
          <p className="text-xs text-subtle">{country}</p>
        </div>
      </div>

      {/* Description */}
      {template.short_description && (
        <p className="mb-4 line-clamp-2 text-xs text-subtle">
          {template.short_description}
        </p>
      )}

      {/* Meta row */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className={cn('rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide', typeStyle)}>
          {template.signal_type}
        </span>
        <span className={cn('text-xs font-medium', tier.color)}>
          {tier.label}
        </span>
        {template.subscription_count > 0 && (
          <span className="text-xs text-subtle">
            {template.subscription_count.toLocaleString()} subscribers
          </span>
        )}
      </div>

      {/* Tags */}
      {template.tags.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-1">
          {template.tags.slice(0, 4).map(tag => (
            <span key={tag} className="rounded-full bg-surface-3 px-2 py-0.5 text-[10px] text-subtle">
              {tag}
            </span>
          ))}
          {template.tags.length > 4 && (
            <span className="rounded-full bg-surface-3 px-2 py-0.5 text-[10px] text-subtle">
              +{template.tags.length - 4}
            </span>
          )}
        </div>
      )}

      {/* CTA */}
      <div className="mt-auto">
        {template.is_subscribed ? (
          <button
            onClick={() => onUnsubscribe(template.id)}
            disabled={loading}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-500/30',
              'bg-emerald-500/10 px-4 py-2 text-xs font-medium text-emerald-300',
              'hover:bg-red-500/10 hover:border-red-500/30 hover:text-red-300',
              'transition-colors disabled:opacity-50',
            )}
          >
            {loading ? (
              <RefreshCw size={12} className="animate-spin" />
            ) : (
              <>
                <CheckCircle2 size={12} />
                Subscribed — click to remove
              </>
            )}
          </button>
        ) : (
          <button
            onClick={() => onSubscribe(template.id)}
            disabled={loading}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-lg border border-border',
              'bg-surface-3 px-4 py-2 text-xs font-medium text-heading',
              'hover:border-accent hover:bg-accent/10 hover:text-accent',
              'transition-colors disabled:opacity-50',
            )}
          >
            {loading ? (
              <RefreshCw size={12} className="animate-spin" />
            ) : (
              <>
                <Plus size={12} />
                Subscribe
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

// ── Filter bar ────────────────────────────────────────────────────────────────

const SIGNAL_TYPES = ['financial', 'regulatory', 'market', 'news', 'technology']

function FilterBar({
  search, setSearch,
  signalType, setSignalType,
  featuredOnly, setFeaturedOnly,
}: {
  search: string
  setSearch: (v: string) => void
  signalType: string
  setSignalType: (v: string) => void
  featuredOnly: boolean
  setFeaturedOnly: (v: boolean) => void
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Search */}
      <div className="relative flex-1 min-w-[200px]">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          type="text"
          placeholder="Search templates…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface-2 py-2 pl-8 pr-4 text-sm text-heading placeholder:text-muted focus:border-accent focus:outline-none"
        />
        {search && (
          <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-heading">
            <X size={12} />
          </button>
        )}
      </div>

      {/* Type filter */}
      <select
        value={signalType}
        onChange={e => setSignalType(e.target.value)}
        className="rounded-lg border border-border bg-surface-2 py-2 pl-3 pr-8 text-sm text-heading focus:border-accent focus:outline-none"
      >
        <option value="">All types</option>
        {SIGNAL_TYPES.map(t => (
          <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
        ))}
      </select>

      {/* Featured toggle */}
      <label className="flex cursor-pointer items-center gap-2 text-sm text-heading">
        <input
          type="checkbox"
          checked={featuredOnly}
          onChange={e => setFeaturedOnly(e.target.checked)}
          className="rounded border-border accent-accent"
        />
        Featured only
      </label>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function MarketplacePage() {
  const [templates, setTemplates]       = useState<SignalTemplateResponse[]>([])
  const [total, setTotal]               = useState(0)
  const [loading, setLoading]           = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError]               = useState<string | null>(null)

  // Filters
  const [search, setSearch]           = useState('')
  const [signalType, setSignalType]   = useState('')
  const [featuredOnly, setFeaturedOnly] = useState(false)
  const [activeTab, setActiveTab]     = useState<'browse' | 'subscriptions'>('browse')

  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      if (activeTab === 'subscriptions') {
        const subs = await listSubscriptions()
        setTemplates(subs)
        setTotal(subs.length)
      } else {
        const result = await listTemplates({
          search: search || undefined,
          signal_type: signalType || undefined,
          featured_only: featuredOnly || undefined,
          limit: 100,
        })
        setTemplates(result.items)
        setTotal(result.total)
      }
    } catch {
      setError('Failed to load marketplace templates')
    } finally {
      setLoading(false)
    }
  }, [search, signalType, featuredOnly, activeTab])

  useEffect(() => {
    const timer = setTimeout(fetchTemplates, 300)
    return () => clearTimeout(timer)
  }, [fetchTemplates])

  const handleSubscribe = useCallback(async (templateId: string) => {
    setActionLoading(templateId)
    try {
      await subscribeToTemplate(templateId)
      setTemplates(prev =>
        prev.map(t => t.id === templateId ? { ...t, is_subscribed: true, subscription_count: t.subscription_count + 1 } : t)
      )
    } catch {
      setError('Failed to subscribe to template')
    } finally {
      setActionLoading(null)
    }
  }, [])

  const handleUnsubscribe = useCallback(async (templateId: string) => {
    setActionLoading(templateId)
    try {
      await unsubscribeFromTemplate(templateId)
      if (activeTab === 'subscriptions') {
        setTemplates(prev => prev.filter(t => t.id !== templateId))
        setTotal(prev => prev - 1)
      } else {
        setTemplates(prev =>
          prev.map(t => t.id === templateId ? { ...t, is_subscribed: false, subscription_count: Math.max(0, t.subscription_count - 1) } : t)
        )
      }
    } catch {
      setError('Failed to unsubscribe from template')
    } finally {
      setActionLoading(null)
    }
  }, [activeTab])

  const subscribedCount = templates.filter(t => t.is_subscribed).length

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Page header */}
      <div className="flex-shrink-0 border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10">
              <ShoppingBag size={18} className="text-accent" />
            </div>
            <div>
              <h1 className="font-display text-xl font-semibold text-heading">
                Signal Marketplace
              </h1>
              <p className="text-sm text-subtle">
                Subscribe to curated signal feeds — Nigeria/Africa first
              </p>
            </div>
          </div>

          {subscribedCount > 0 && (
            <div className="flex items-center gap-2 rounded-full bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
              <CheckCircle2 size={12} />
              {subscribedCount} active subscription{subscribedCount !== 1 ? 's' : ''}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="mt-4 flex gap-1">
          {(['browse', 'subscriptions'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'rounded-lg px-4 py-1.5 text-sm font-medium transition-colors',
                activeTab === tab
                  ? 'bg-accent/15 text-accent'
                  : 'text-muted hover:text-heading',
              )}
            >
              {tab === 'browse' ? 'Browse' : 'My Subscriptions'}
              {tab === 'subscriptions' && subscribedCount > 0 && (
                <span className="ml-2 rounded-full bg-emerald-500/20 px-1.5 py-0.5 text-xs text-emerald-400">
                  {subscribedCount}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Filters (browse tab only) */}
      {activeTab === 'browse' && (
        <div className="flex-shrink-0 border-b border-border px-6 py-3">
          <FilterBar
            search={search}
            setSearch={setSearch}
            signalType={signalType}
            setSignalType={setSignalType}
            featuredOnly={featuredOnly}
            setFeaturedOnly={setFeaturedOnly}
          />
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <X size={14} />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">
              <X size={12} />
            </button>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-72 animate-pulse rounded-xl border border-border bg-surface-2" />
            ))}
          </div>
        ) : templates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Globe size={40} className="mb-4 text-muted opacity-40" />
            <p className="text-base font-medium text-heading">
              {activeTab === 'subscriptions' ? 'No active subscriptions' : 'No templates found'}
            </p>
            <p className="mt-1 text-sm text-subtle">
              {activeTab === 'subscriptions'
                ? 'Browse the marketplace and subscribe to signal feeds'
                : 'Try adjusting your filters'}
            </p>
            {activeTab === 'subscriptions' && (
              <button
                onClick={() => setActiveTab('browse')}
                className="mt-4 flex items-center gap-2 rounded-lg bg-accent/10 px-4 py-2 text-sm font-medium text-accent hover:bg-accent/15"
              >
                <ShoppingBag size={14} />
                Browse marketplace
              </button>
            )}
          </div>
        ) : (
          <>
            {activeTab === 'browse' && (
              <p className="mb-4 text-xs text-subtle">
                {total.toLocaleString()} template{total !== 1 ? 's' : ''} available
              </p>
            )}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {templates.map(template => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onSubscribe={handleSubscribe}
                  onUnsubscribe={handleUnsubscribe}
                  loading={actionLoading === template.id}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
