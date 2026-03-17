'use client'

import { Check, Zap, Star, Building2, TrendingUp } from 'lucide-react'

// ── Plan data — mirrors backend PricingTier enum + seed data ──────────────────
// Source: alembic/versions/2026_02_15_0009_seed_pricing_config_data.py
//         alembic/versions/2026_02_15_0010_seed_feature_gates_data.py

interface Plan {
  id:          string
  name:        string
  badge?:      string
  price:       string
  period:      string
  description: string
  credits:     string
  features:    string[]
  highlighted: boolean
  cta:         string
  ctaVariant:  'primary' | 'outline' | 'ghost' | 'disabled'
}

const PLANS: Plan[] = [
  {
    id:          'explorer',
    name:        'Explorer',
    price:       '$0',
    period:      'month',
    description: 'Free forever — explore Cogent with limited access. Includes a 30-day Growth trial on signup.',
    credits:     '1,000 credits/month',
    features: [
      '1,000 credits/month',
      '50 signals/month (limited feed)',
      'Basic intelligence access',
      'Community support',
      '30-day Growth trial on signup',
    ],
    highlighted: false,
    cta:         'Downgrade to Free',
    ctaVariant:  'ghost',
  },
  {
    id:          'growth',
    name:        'Growth',
    badge:       'Most Popular',
    price:       '$499',
    period:      'month',
    description: 'For analysts and growing teams who need full signal coverage and AI synthesis.',
    credits:     '5,000 credits/month',
    features: [
      '5,000 credits/month',
      'Full continuous signals feed',
      'On-demand AI synthesis',
      'API access',
      'Priority support',
      'Weekly intelligence reports',
    ],
    highlighted: true,
    cta:         'Current Plan',
    ctaVariant:  'disabled',
  },
  {
    id:          'mid_market',
    name:        'Mid-Market',
    price:       '$2,499',
    period:      'month',
    description: 'For mid-size organisations requiring compliance intelligence and custom workflows.',
    credits:     '25,000 credits/month',
    features: [
      '25,000 credits/month',
      'Everything in Growth',
      'Compliance modules',
      'Custom contract creation',
      'Dedicated account manager',
      'Advanced analytics & exports',
    ],
    highlighted: false,
    cta:         'Upgrade to Mid-Market',
    ctaVariant:  'primary',
  },
  {
    id:          'enterprise',
    name:        'Enterprise',
    price:       '$9,999',
    period:      'month',
    description: 'For large organisations requiring unlimited scale, private storage, and custom SLAs.',
    credits:     'Unlimited credits',
    features: [
      'Unlimited credits',
      'Everything in Mid-Market',
      'Private signal store',
      'Custom SLA & on-prem option',
      'White-label available',
      'Dedicated 24/7 support',
    ],
    highlighted: false,
    cta:         'Contact sales',
    ctaVariant:  'outline',
  },
]

const PLAN_ICONS: Record<string, React.ReactNode> = {
  explorer:   <TrendingUp className="h-4 w-4 text-slate-400" />,
  growth:     <Zap        className="h-4 w-4 text-primary"   />,
  mid_market: <Star       className="h-4 w-4 text-amber-500" />,
  enterprise: <Building2  className="h-4 w-4 text-indigo-400" />,
}

// ── Component ─────────────────────────────────────────────────────────────────

export function PlanSection() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="text-xl font-medium text-heading">Choose your Plan</h2>
        <p className="mt-1 text-sm text-subtle">
          All plans billed monthly in USD. Credit overages billed at your account's overage rate.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {PLANS.map(plan => (
          <div
            key={plan.id}
            className={`relative flex flex-col rounded-2xl border p-5 shadow-card transition-shadow hover:shadow-md ${
              plan.highlighted
                ? 'border-primary/40 bg-primary/3 ring-2 ring-primary/15'
                : 'border-border bg-surface'
            }`}
          >
            {/* Badge */}
            {plan.badge && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <span className="flex items-center gap-1 rounded-full border border-primary/30 bg-primary px-3 py-0.5 text-[11px] font-semibold text-white shadow-sm">
                  <Zap className="h-3 w-3" />
                  {plan.badge}
                </span>
              </div>
            )}

            {/* Header */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                {PLAN_ICONS[plan.id]}
                <p className="text-sm font-semibold text-heading">{plan.name}</p>
              </div>
              <div className="flex items-end gap-1 mt-1">
                <span className="text-2xl font-bold text-heading leading-none">{plan.price}</span>
                {plan.period && (
                  <span className="mb-0.5 text-xs text-subtle">/{plan.period}</span>
                )}
              </div>
              <p className="mt-2 text-[11px] text-subtle leading-relaxed">{plan.description}</p>
            </div>

            {/* Credits pill */}
            <div className="mb-4 inline-flex items-center gap-1.5 rounded-lg bg-muted px-3 py-1.5 self-start">
              <Zap className="h-3 w-3 text-primary/70" />
              <span className="text-[11px] font-semibold text-body">{plan.credits}</span>
            </div>

            {/* Features */}
            <ul className="mb-6 flex flex-1 flex-col gap-2">
              {plan.features.map(f => (
                <li key={f} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-emerald-500" strokeWidth={2.5} />
                  <span className="text-[11px] text-body leading-snug">{f}</span>
                </li>
              ))}
            </ul>

            {/* CTA */}
            <button
              disabled={plan.ctaVariant === 'disabled'}
              className={`w-full rounded-xl py-2 text-[13px] font-semibold transition-all ${
                plan.ctaVariant === 'disabled'
                  ? 'cursor-not-allowed border border-primary/20 bg-primary/8 text-primary'
                  : plan.ctaVariant === 'primary'
                  ? 'bg-primary text-white hover:bg-primary-hover active:scale-[0.98] shadow-sm'
                  : plan.ctaVariant === 'outline'
                  ? 'border border-border bg-surface text-body hover:bg-muted active:scale-[0.98]'
                  : 'text-subtle hover:text-body hover:bg-muted'
              }`}
            >
              {plan.cta}
            </button>
          </div>
        ))}
      </div>

      {/* Footnotes */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-muted/50 px-5 py-3">
        <p className="text-xs text-subtle">
          Need help choosing?{' '}
          <a href="#" className="font-medium text-primary hover:underline">Talk to sales</a>
          {' '}· Cancel anytime · Prices in USD
        </p>
        <p className="text-xs text-subtle">
          Credit overages are never discounted · Billed at your account's overage rate
        </p>
      </div>
    </div>
  )
}
