'use client'

import { WalletCards } from 'lucide-react'

import type {
  CreditBalanceResponse,
  CreditTransactionResponse,
} from '@/lib/hooks/useSettings'
import { PlanSection } from '@/components/settings/PlanSection'
import { UsageDashboard } from '@/components/settings/UsageDashboard'

interface BillingControlSectionProps {
  creditBalance: CreditBalanceResponse | null
  creditTransactions: CreditTransactionResponse[]
  loading?: boolean
}

export function BillingControlSection({
  creditBalance,
  creditTransactions,
  loading = false,
}: BillingControlSectionProps) {
  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-[28px] border border-border bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] p-6 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/12 bg-primary/5 px-3 py-1.5 text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-primary">
              <WalletCards className="h-3.5 w-3.5" strokeWidth={1.7} />
              Workspace billing
            </div>
            <h2 className="mt-4 text-title text-heading">Plan, credits, and billing in one place</h2>
            <p className="mt-2 max-w-[62ch] text-sm leading-relaxed text-subtle">
              Track your current plan, watch credit usage, and manage subscription state without jumping between
              separate tabs.
            </p>
          </div>
        </div>
      </div>

      <UsageDashboard
        creditBalance={creditBalance}
        creditTransactions={creditTransactions}
        loading={loading}
      />

      <PlanSection />
    </div>
  )
}
