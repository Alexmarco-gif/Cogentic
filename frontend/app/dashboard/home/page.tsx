'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Zap, ShoppingBag, BookOpen } from 'lucide-react'
import { useSignals } from '@/lib/hooks/useSignals'
import { useSituationRoom } from '@/lib/hooks/useSituationRoom'
import { MorningBrief } from '@/components/signals/MorningBrief'
import { StrategicStatusCard } from '@/components/signals/StrategicStatusCard'
import { IntelHeatmap } from '@/components/signals/IntelHeatmap'
import { LiveIntelFeed } from '@/components/signals/LiveIntelFeed'
import { SignalDrawer } from '@/components/signals/SignalDrawer'

const INDUSTRY_OPTIONS = [
  { value: 'fintech',            label: 'Fintech' },
  { value: 'e-commerce-retail',  label: 'E-Commerce & Retail' },
  { value: 'financial-services', label: 'Financial Services' },
  { value: 'media-brand',        label: 'Entertainment & Brand' },
  { value: 'telecom-digital',    label: 'Telecom & Digital' },
  { value: 'agriculture-agritech', label: 'Agriculture & Agritech' },
]

// ── Quick-action shortcuts ───────────────────────────────────────────────────
const QUICK_ACTIONS = [
  { label: 'New Contract', icon: <Plus size={12} />,       href: '/dashboard/studio'      },
  { label: 'Signals',      icon: <Zap size={12} />,        href: '/dashboard/signals'     },
  { label: 'Marketplace',  icon: <ShoppingBag size={12} />, href: '/dashboard/marketplace' },
  { label: 'Library',      icon: <BookOpen size={12} />,   href: '/dashboard/library'     },
]

export default function HomePage() {
  const router = useRouter()
  const [industrySlug, setIndustrySlug] = useState('fintech')
  const [feedUpdatedAt, setFeedUpdatedAt] = useState<Date | null>(null)

  const {
    signals,
    loading: signalsLoading,
    activeDrawerSignal,
    openDrawer,
    closeDrawer,
    toggleSave,
  } = useSignals()

  const {
    strategicStatuses,
    heatmapQuadrants,
    feedEvents,
    unreadCount,
    riskCount,
    opportunityCount,
    loading: roomLoading,
  } = useSituationRoom(industrySlug)

  const loading = signalsLoading || roomLoading
  const criticalCount = strategicStatuses.find(s => s.id === 'critical-alerts')?.count ?? 0

  // Track when the feed data last refreshed
  useEffect(() => {
    if (!roomLoading) setFeedUpdatedAt(new Date())
  }, [roomLoading])

  /* ── Empty-state onboarding ────────────────────────────────────────── */
  const isEmpty = !loading && signals.length === 0 && feedEvents.length === 0

  if (isEmpty) {
    return (
      <div className="px-6 py-6 max-w-[1400px] mx-auto">
        <MorningBrief
          unreadCount={0}
          criticalCount={0}
          riskCount={0}
          opportunityCount={0}
        />
        <div className="mt-10 flex flex-col items-center justify-center text-center py-20">
          <div className="rounded-2xl border border-dashed border-primary/30 bg-primary/5 p-10 max-w-lg">
            <h2 className="text-lg font-semibold text-heading mb-2">Welcome to Cogent</h2>
            <p className="text-sm text-subtle mb-6">
              Your intelligence dashboard is empty because no signals have been ingested yet.
              Create your first brief or import documents to get started.
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => router.push('/dashboard/briefs/new')}
                className="rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
              >
                Create a Brief
              </button>
              <button
                onClick={() => router.push('/dashboard/marketplace')}
                className="rounded-xl border border-border bg-surface px-5 py-2.5 text-sm font-medium text-body hover:bg-muted transition-colors"
              >
                Browse Signal Marketplace
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-6">

        {/* ── Mission Control Header ───────────────── */}
        <MorningBrief
          unreadCount={unreadCount}
          criticalCount={criticalCount}
          riskCount={riskCount}
          opportunityCount={opportunityCount}
        />

        {/* ── Quick Actions + ⌘K hint ─────────────── */}
        <div className="flex items-center gap-2 flex-wrap">
          {QUICK_ACTIONS.map(({ label, icon, href }) => (
            <button
              key={href}
              onClick={() => router.push(href)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-surface text-[11px] font-medium text-body hover:bg-muted hover:border-border-hover transition-colors"
            >
              {icon}
              {label}
            </button>
          ))}
          <div className="ml-auto inline-flex items-center gap-1 text-[11px] text-subtle select-none">
            <kbd className="font-mono text-[10px] bg-muted border border-border px-1.5 py-0.5 rounded">⌘K</kbd>
            <span>to search</span>
          </div>
        </div>

        {/* ── SECTION 1: Strategic Status ──────────── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-[13px] font-medium text-heading tracking-wide uppercase">
                Strategic Status
              </h2>
              <p className="text-[11px] text-subtle mt-0.5">
                What changed · Why it matters · What to do next
              </p>
            </div>
            <select
              value={industrySlug}
              onChange={(e) => setIndustrySlug(e.target.value)}
              className="rounded-lg border border-white/10 bg-surface px-2.5 py-1 text-[11px] text-body focus:outline-none focus:ring-1 focus:ring-primary/50"
              aria-label="Select industry"
            >
              {INDUSTRY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {loading
              ? Array.from({ length: 5 }).map((_, i) => (
                  <StrategicStatusCard
                    key={i}
                    status={{ id: `skeleton-${i}`, label: '', count: 0, level: 'stable', contextLine: '', changeDetector: '', suggestedAction: '', trend: 'flat' }}
                    loading
                  />
                ))
              : strategicStatuses.map(status => (
                  <StrategicStatusCard
                    key={status.id}
                    status={status}
                    loading={false}
                    onClick={() => router.push(`/dashboard/signals?filter=${status.id}`)}
                  />
                ))
            }
          </div>
        </section>

        {/* ── SECTION 2: Intelligence Heatmap ──────── */}
        <section>
          <IntelHeatmap quadrants={heatmapQuadrants} loading={roomLoading} />
        </section>

        {/* ── SECTION 3: Real-Time Intelligence Feed ── */}
        <section>
          {/* Recent signals chips */}
          {signals.length > 0 && !loading && (
            <div className="mb-3 flex items-center gap-2 flex-wrap">
              <span className="text-[11px] text-subtle whitespace-nowrap">Latest on radar:</span>
              {signals.slice(0, 4).map(signal => (
                <button
                  key={signal.id}
                  onClick={() => openDrawer(signal)}
                  className="inline-flex items-center max-w-[200px] gap-1.5 px-2.5 py-1 rounded-full border border-border bg-surface text-[11px] text-body hover:bg-muted transition-colors"
                >
                  <span className="truncate">{signal.title ?? signal.domain ?? 'Signal'}</span>
                </button>
              ))}
            </div>
          )}
          <LiveIntelFeed
            events={feedEvents}
            signals={signals}
            loading={roomLoading}
            onEventClick={openDrawer}
            lastUpdated={feedUpdatedAt ?? undefined}
          />
        </section>

      </div>

      {/* Signal Dossier Drawer */}
      <SignalDrawer
        signal={activeDrawerSignal}
        onClose={closeDrawer}
        onSave={toggleSave}
      />
    </>
  )
}
