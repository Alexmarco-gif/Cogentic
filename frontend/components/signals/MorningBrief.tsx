'use client'

import { useUser } from '@auth0/nextjs-auth0/client'
import { LiveIndicator } from '@/components/ui'

interface MorningBriefProps {
  unreadCount: number
  criticalCount: number
  riskCount: number
  opportunityCount: number
}

export function MorningBrief({
  unreadCount,
  criticalCount,
  riskCount,
  opportunityCount,
}: MorningBriefProps) {
  const { user } = useUser()

  const firstName = user?.name?.split(' ')[0] ?? user?.email?.split('@')[0] ?? 'there'

  const now = new Date()
  const hour = now.getHours()
  const greeting =
    hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  const today = now.toLocaleDateString('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  return (
    <section className="mb-2">
      {/* Greeting */}
      <h1 className="text-[28px] leading-tight font-semibold text-heading mb-1">
        {greeting},{' '}
        <span className="text-primary font-bold">{firstName}</span>.
      </h1>

      {/* Intelligence-first sub-copy */}
      <p className="text-sm text-body max-w-2xl mb-4">
        {criticalCount > 0 ? (
          <>
            <span className="text-red-600 font-medium">{riskCount} risk{riskCount !== 1 ? 's' : ''} require attention</span>
            {' '}·{' '}
            <span className="text-emerald-600 font-medium">{opportunityCount} opportunit{opportunityCount !== 1 ? 'ies' : 'y'} detected</span>
            {' '}·{' '}
            <span className="text-heading font-medium">{unreadCount} new signal{unreadCount !== 1 ? 's' : ''}</span>
            {' '}across monitored domains since your last session.
          </>
        ) : unreadCount > 0 ? (
          <>
            <span className="font-medium text-heading">{unreadCount} new intelligence update{unreadCount !== 1 ? 's' : ''}</span>
            {' '}detected. No critical risks. {opportunityCount > 0 && (
              <><span className="text-emerald-600 font-medium">{opportunityCount} emerging opportunit{opportunityCount !== 1 ? 'ies' : 'y'}</span> flagged for review.</>
            )}
          </>
        ) : null}
      </p>

      {/* Live badge */}
      <div className="flex items-center gap-3">
        <LiveIndicator label="Live" />
        <span className="text-xs text-subtle">
          Last refreshed{' '}
          {now.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </section>
  )
}
