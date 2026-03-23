'use client'

import { useUser } from '@auth0/nextjs-auth0/client'
import { AlertTriangle, ArrowRight, Sparkles, TrendingUp } from 'lucide-react'
import { LiveIndicator } from '@/components/ui'

interface MorningBriefProps {
  unreadCount: number
  criticalCount: number
  riskCount: number
  opportunityCount: number
  lastUpdated?: Date | null
  liveConnected?: boolean
}

export function MorningBrief({
  unreadCount,
  criticalCount,
  riskCount,
  opportunityCount,
  lastUpdated,
  liveConnected = false,
}: MorningBriefProps) {
  const { user } = useUser()
  const firstName = user?.name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'there'
  const now = new Date()
  const hour = now.getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const refreshedAt = lastUpdated ?? now

  const summary = criticalCount > 0
    ? `${criticalCount} critical issue${criticalCount === 1 ? '' : 's'} need a response.`
    : unreadCount > 0
    ? `${unreadCount} new intelligence update${unreadCount === 1 ? '' : 's'} are ready to review.`
    : 'Your workspace is calm. Use the next action cards below to keep momentum.'

  return (
    <section className="surface-accent overflow-hidden p-6 sm:p-8">
      <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/12 bg-white/60 px-3 py-1.5 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-primary backdrop-blur">
            <Sparkles size={13} />
            Daily intelligence brief
          </div>

          <h1 className="text-display text-heading">
            {greeting}, {firstName}.
          </h1>
          <p className="mt-4 max-w-2xl text-body text-body">{summary}</p>
        </div>

        <div className="rounded-[26px] border border-border bg-surface/90 p-4 shadow-card">
          <div className="flex items-center gap-3">
            <LiveIndicator label={liveConnected ? 'Live sync active' : 'Auto refresh active'} />
            <span className="text-[0.76rem] text-subtle">
              Refreshed {refreshedAt.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <div className="interactive-chip">
              <AlertTriangle size={13} className="text-critical" />
              {riskCount} risks
            </div>
            <div className="interactive-chip">
              <TrendingUp size={13} className="text-success" />
              {opportunityCount} opportunities
            </div>
            <div className="interactive-chip">
              <ArrowRight size={13} className="text-primary" />
              {unreadCount} new updates
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
