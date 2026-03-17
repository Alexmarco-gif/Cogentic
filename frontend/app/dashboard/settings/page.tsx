'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { useSettings, type SettingsTab } from '@/lib/hooks/useSettings'
import { SettingsTabs }          from '@/components/settings/SettingsTabs'
import { ProfileSection }        from '@/components/settings/ProfileSection'
import { BillingSection }        from '@/components/settings/BillingSection'
import { SecuritySection }       from '@/components/settings/SecuritySection'
import { NotificationsSection }  from '@/components/settings/NotificationsSection'
import { PreferencesSection }    from '@/components/settings/PreferencesSection'
import { IntegrationsSection }   from '@/components/settings/IntegrationsSection'
import { UsageDashboard }        from '@/components/settings/UsageDashboard'
import { PlanSection }           from '@/components/settings/PlanSection'
import { DataPrivacySection }    from '@/components/settings/DataPrivacySection'
import { LegalSection }          from '@/components/settings/LegalSection'

// ── Coming-soon wrapper for unconnected sections ─────────────────────────────

function ComingSoon({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="relative">
      <div className="pointer-events-none select-none opacity-40 blur-[1px]">
        {children}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="rounded-full border border-primary/20 bg-primary/8 px-4 py-1.5 text-xs font-semibold text-primary">
          Coming Soon
        </span>
        <p className="mt-2 max-w-xs text-center text-xs text-subtle">
          {label} will be available in an upcoming release.
        </p>
      </div>
    </div>
  )
}

// ── Inner component (reads searchParams) ─────────────────────────────────────

function SettingsContent() {
  const searchParams = useSearchParams()
  const queryTab     = searchParams.get('tab') as SettingsTab | null

  const s = useSettings(queryTab ?? 'profile')

  function renderContent() {
    switch (s.activeTab) {
      case 'profile':
        return (
          <ProfileSection
            profile={s.profile}
            sessions={s.sessions}
            onRevokeSession={s.revokeSession}
            onEditProfile={() => s.setEditingProfile(true)}
          />
        )
      case 'billing':
        return (
          <ComingSoon label="Billing & invoices">
            <BillingSection
              card={s.card}
              billingContact={s.billingContact}
              invoices={s.invoices}
              selectedInvoices={s.selectedInvoices}
              onCardChange={patch => s.setCard(c => ({ ...c, ...patch }))}
              onContactChange={s.setBillingContact}
              onToggleInvoice={s.toggleInvoiceSelect}
            />
          </ComingSoon>
        )
      case 'security':
        return (
          <SecuritySection
            twoFAEnabled={s.twoFAEnabled}
            onSetTwoFA={s.setTwoFA}
            sessions={s.sessions}
            sessionsLoading={s.sessionsLoading}
            onRevokeSession={s.revokeSession}
            apiKeys={s.apiKeys}
            onRevokeKey={s.handleRevokeApiKey}
            onGenerateKey={s.handleCreateApiKey}
          />
        )
      case 'notifications':
        return (
          <ComingSoon label="Notification preferences">
            <NotificationsSection
              prefs={s.notifications}
              onToggle={s.toggleNotification}
            />
          </ComingSoon>
        )
      case 'preferences':
        return <PreferencesSection />
      case 'integrations':
        return (
          <ComingSoon label="Third-party integrations">
            <IntegrationsSection
              integrations={s.integrations}
              onToggle={s.toggleIntegration}
            />
          </ComingSoon>
        )
      case 'usage':
        return (
          <UsageDashboard
            usageData={s.usageData}
            planLimits={s.planLimits}
          />
        )
      case 'plan':
        return (
          <ComingSoon label="Plan management">
            <PlanSection />
          </ComingSoon>
        )
      case 'data':
        return <DataPrivacySection />
      case 'legal':
        return <LegalSection />
    }
  }

  return (
    <div
      className="flex flex-col overflow-hidden"
      style={{ height: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 border-b border-border bg-surface px-8 pt-8 pb-0">
        <h1 className="text-2xl font-medium text-heading">Settings</h1>
        <p className="mt-0.5 mb-5 text-sm text-subtle">Manage your account settings and preferences.</p>
        <SettingsTabs activeTab={s.activeTab} onTabChange={s.setActiveTab} />
      </div>

      {/* ── Scrollable content ───────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        {renderContent()}
      </div>
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-subtle">Loading settings…</div>}>
      <SettingsContent />
    </Suspense>
  )
}
