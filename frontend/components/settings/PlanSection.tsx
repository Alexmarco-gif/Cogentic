'use client'

import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Building2, Check, Loader2, Star, TrendingUp, Zap } from 'lucide-react'

import { upgradeTier, getTierOptions, type TierUpgradeResponse } from '@/lib/api/pricing'
import { friendlyErrorMessage } from '@/lib/api/errors'
import { usePricing } from '@/lib/contexts/PricingContext'

interface TierCard {
  id: string
  name: string
  icon: ReactNode
  description: string
  features: string[]
}

const TIER_COPY: TierCard[] = [
  {
    id: 'explorer',
    name: 'Explorer',
    icon: <TrendingUp className="h-4 w-4 text-slate-400" />,
    description: 'Free workspace for individual research, lightweight monitoring, and trial onboarding.',
    features: [
      'Core dashboard access',
      'Limited signal monitoring',
      'Starter monthly credits',
      'Single-workspace setup',
    ],
  },
  {
    id: 'growth',
    name: 'Growth',
    icon: <Zap className="h-4 w-4 text-primary" />,
    description: 'Best fit for teams that need continuous signals, investigations, and API access.',
    features: [
      'Continuous intelligence feed',
      'On-demand investigations',
      'API key management',
      'Higher monthly credit allocation',
    ],
  },
  {
    id: 'mid_market',
    name: 'Mid-Market',
    icon: <Star className="h-4 w-4 text-amber-500" />,
    description: 'Adds custom contracts, compliance workflows, and broader operational visibility.',
    features: [
      'Custom contracts',
      'Compliance modules',
      'Advanced exports',
      'Higher usage ceilings',
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    icon: <Building2 className="h-4 w-4 text-indigo-400" />,
    description: 'For private deployments, dedicated support, and large-scale intelligence operations.',
    features: [
      'Private signal store',
      'Dedicated support and SLAs',
      'Custom deployment options',
      'Enterprise-grade limits',
    ],
  },
]

function currency(amount: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount)
}

export function PlanSection() {
  const { tier, credits, error: pricingError, refresh } = usePricing()
  const [tiers, setTiers] = useState<Array<{ tier: string; price: number }>>([])
  const [loading, setLoading] = useState(true)
  const [actionTier, setActionTier] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadTiers() {
      setLoading(true)
      try {
        const response = await getTierOptions()
        if (!cancelled) setTiers(response.tiers)
      } catch (err) {
        if (!cancelled) setError(friendlyErrorMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void loadTiers()
    return () => {
      cancelled = true
    }
  }, [])

  const tierCards = useMemo(
    () =>
      TIER_COPY.map((card) => ({
        ...card,
        price: tiers.find((tierItem) => tierItem.tier === card.id)?.price ?? 0,
        isCurrent: tier === card.id,
      })),
    [tier, tiers],
  )

  async function handleUpgrade(targetTier: string) {
    if (targetTier === tier) return

    setActionTier(targetTier)
    setError(null)
    setMessage(null)

    try {
      const response: TierUpgradeResponse = await upgradeTier({ target_tier: targetTier })
      setMessage(response.message)
      await refresh()
    } catch (err) {
      setError(friendlyErrorMessage(err))
    } finally {
      setActionTier(null)
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-xl font-medium text-heading">Plan & Credits</h2>
            <p className="mt-1 text-sm text-subtle">
              Upgrade requests are recorded for billing review until the payment processor is enabled.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">Current tier</p>
              <p className="mt-1 text-sm font-semibold capitalize text-heading">{tier.replace('_', ' ')}</p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">Credits used</p>
              <p className="mt-1 text-sm font-semibold text-heading">{credits.consumed.toLocaleString()}</p>
            </div>
            <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
              <p className="text-[10px] uppercase tracking-wide text-subtle">Credits remaining</p>
              <p className="mt-1 text-sm font-semibold text-heading">{credits.remaining.toLocaleString()}</p>
            </div>
          </div>
        </div>

        {(message || error || pricingError) && (
          <div className={`mt-5 rounded-xl border px-4 py-3 text-sm ${
            error || pricingError
              ? 'border-rose-200 bg-rose-50 text-rose-700'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}>
            {error ?? pricingError ?? message}
          </div>
        )}
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-subtle">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading plan options...
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
          {tierCards.map((card) => (
            <div
              key={card.id}
              className={`relative flex flex-col rounded-2xl border p-5 shadow-card ${
                card.isCurrent
                  ? 'border-primary/40 bg-primary/5 ring-2 ring-primary/10'
                  : 'border-border bg-surface'
              }`}
            >
              {card.id === 'growth' && !card.isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border border-primary/20 bg-primary px-3 py-0.5 text-[11px] font-semibold text-white">
                  Most Popular
                </div>
              )}

              <div className="mb-4">
                <div className="mb-1 flex items-center gap-2">
                  {card.icon}
                  <p className="text-sm font-semibold text-heading">{card.name}</p>
                </div>
                <div className="flex items-end gap-1">
                  <span className="text-2xl font-bold text-heading">{currency(card.price)}</span>
                  <span className="mb-0.5 text-xs text-subtle">/month</span>
                </div>
                <p className="mt-2 text-[11px] leading-relaxed text-subtle">{card.description}</p>
              </div>

              <ul className="mb-6 flex flex-1 flex-col gap-2">
                {card.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-500" strokeWidth={2.5} />
                    <span className="text-[11px] leading-snug text-body">{feature}</span>
                  </li>
                ))}
              </ul>

              {card.id === 'enterprise' ? (
                <a
                  href="mailto:sales@cogent.ai?subject=Enterprise%20Pricing"
                  className="w-full rounded-xl border border-border bg-surface py-2 text-center text-[13px] font-semibold text-body transition-colors hover:bg-muted"
                >
                  Contact sales
                </a>
              ) : (
                <button
                  onClick={() => {
                    void handleUpgrade(card.id)
                  }}
                  disabled={card.isCurrent || actionTier === card.id}
                  className={`w-full rounded-xl py-2 text-[13px] font-semibold transition-all ${
                    card.isCurrent
                      ? 'cursor-not-allowed border border-primary/20 bg-primary/10 text-primary'
                      : 'bg-primary text-white hover:bg-primary-hover disabled:opacity-50'
                  }`}
                >
                  {actionTier === card.id ? 'Submitting...' : card.isCurrent ? 'Current plan' : `Request ${card.name}`}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
