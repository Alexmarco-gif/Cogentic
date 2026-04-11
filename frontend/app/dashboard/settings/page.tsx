'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import {
  Bell,
  CreditCard,
  FileCheck2,
  LockKeyhole,
  Palette,
  ShieldCheck,
  UserCircle2,
} from 'lucide-react'

import { SETTINGS_TABS, useSettings, type SettingsTab } from '@/lib/hooks/useSettings'
import { SettingsTabs } from '@/components/settings/SettingsTabs'
import { ProfileSection } from '@/components/settings/ProfileSection'
import { SecuritySection } from '@/components/settings/SecuritySection'
import { PreferencesSection } from '@/components/settings/PreferencesSection'
import { NotificationsSection } from '@/components/settings/NotificationsSection'
import { DataPrivacySection } from '@/components/settings/DataPrivacySection'
import { LegalSection } from '@/components/settings/LegalSection'
import { BillingControlSection } from '@/components/settings/BillingControlSection'
import { cn } from '@/lib/utils'

const SETTINGS_META: Record<
  Exclude<SettingsTab, 'usage' | 'billing' | 'integrations'>,
  {
    label: string
    description: string
    group: 'Account' | 'Workspace'
    icon: React.ElementType
  }
> = {
  profile: {
    label: 'Profile',
    description: 'Identity, workspace access, and session overview.',
    group: 'Account',
    icon: UserCircle2,
  },
  preferences: {
    label: 'Preferences',
    description: 'Display, density, language, and regional settings.',
    group: 'Account',
    icon: Palette,
  },
  notifications: {
    label: 'Notifications',
    description: 'Review alerts, updates, and communication flow.',
    group: 'Account',
    icon: Bell,
  },
  security: {
    label: 'Security',
    description: 'Sessions, authentication, and API access.',
    group: 'Account',
    icon: LockKeyhole,
  },
  plan: {
    label: 'Billing & Usage',
    description: 'Plans, credits, invoices, and workspace billing.',
    group: 'Workspace',
    icon: CreditCard,
  },
  data: {
    label: 'Data & Privacy',
    description: 'Consent, exports, deletion, and archive controls.',
    group: 'Workspace',
    icon: ShieldCheck,
  },
  legal: {
    label: 'Legal & Help',
    description: 'Terms, privacy notice, support, and legal resources.',
    group: 'Workspace',
    icon: FileCheck2,
  },
}

function SummaryCard({
  label,
  value,
  detail,
}: {
  label: string
  value: string
  detail: string
}) {
  return (
    <div className="rounded-[22px] border border-border bg-surface px-4 py-4 shadow-card">
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-subtle">{label}</p>
      <p className="mt-2 text-[1.35rem] font-semibold text-heading">{value}</p>
      <p className="mt-1 text-[0.8rem] text-subtle">{detail}</p>
    </div>
  )
}

function SettingsSidebar({
  activeTab,
  onTabChange,
}: {
  activeTab: SettingsTab
  onTabChange: (tab: SettingsTab) => void
}) {
  const groups = ['Account', 'Workspace'] as const

  return (
    <aside className="hidden lg:block">
      <div className="sticky top-6 rounded-[28px] border border-border bg-surface p-4 shadow-card">
        <div className="mb-4 px-2">
          <p className="text-[0.72rem] font-semibold uppercase tracking-[0.18em] text-subtle">Control center</p>
          <p className="mt-2 text-sm leading-relaxed text-body">
            Manage your identity, workspace controls, credits, billing, and privacy settings.
          </p>
        </div>

        <div className="space-y-5">
          {groups.map((group) => (
            <div key={group}>
              <p className="px-2 pb-2 text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-subtle">{group}</p>
              <div className="space-y-1">
                {Object.entries(SETTINGS_META)
                  .filter(([, meta]) => meta.group === group)
                  .map(([tab, meta]) => {
                    const Icon = meta.icon
                    const isActive = activeTab === tab

                    return (
                      <button
                        key={tab}
                        onClick={() => onTabChange(tab as SettingsTab)}
                        className={cn(
                          'flex w-full items-start gap-3 rounded-[20px] px-3 py-3 text-left transition-all duration-200',
                          isActive
                            ? 'bg-primary/6 text-primary shadow-[inset_0_0_0_1px_rgba(37,99,235,0.15)]'
                            : 'text-body hover:bg-muted/60 hover:text-heading',
                        )}
                      >
                        <div
                          className={cn(
                            'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl',
                            isActive ? 'bg-primary/12 text-primary' : 'bg-muted text-subtle',
                          )}
                        >
                          <Icon className="h-4 w-4" strokeWidth={1.7} />
                        </div>
                        <div className="min-w-0">
                          <p className={cn('text-[0.86rem] font-semibold', isActive ? 'text-primary' : 'text-heading')}>
                            {meta.label}
                          </p>
                          <p className="mt-1 text-[0.76rem] leading-relaxed text-subtle">{meta.description}</p>
                        </div>
                      </button>
                    )
                  })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  )
}

function SettingsContent() {
  const searchParams = useSearchParams()
  const requestedTab = searchParams.get('tab') as SettingsTab | null
  const queryTab = SETTINGS_TABS.some((tab) => tab.id === requestedTab)
    ? requestedTab
    : 'profile'

  const s = useSettings(queryTab ?? 'profile')
  const activeKey = s.activeTab === 'usage' ? 'plan' : s.activeTab
  const meta = SETTINGS_META[activeKey as keyof typeof SETTINGS_META] ?? SETTINGS_META.profile
  const remainingCredits = s.creditBalance.remaining.toLocaleString()
  const currentPlan = s.currentUser?.subscription.plan ?? s.profile.plan ?? 'Explorer'
  const currentRole = s.currentUser?.organization.role ?? 'member'

  function renderContent() {
    switch (s.activeTab) {
      case 'profile':
        return (
          <ProfileSection
            profile={s.profile}
            sessions={s.sessions}
            onRevokeSession={s.revokeSession}
            workspaceRole={currentRole}
            workspaceId={s.currentUser?.organization.id ?? 'Awaiting workspace'}
            currentPlan={currentPlan}
          />
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
            onRotateKey={s.handleRotateApiKey}
          />
        )
      case 'preferences':
        return <PreferencesSection />
      case 'notifications':
        return <NotificationsSection />
      case 'plan':
      case 'usage':
        return (
          <BillingControlSection
            creditBalance={s.creditBalance}
            creditTransactions={s.creditTransactions}
            loading={s.usageLoading}
          />
        )
      case 'data':
        return <DataPrivacySection />
      case 'legal':
        return <LegalSection />
      default:
        return (
          <ProfileSection
            profile={s.profile}
            sessions={s.sessions}
            onRevokeSession={s.revokeSession}
            workspaceRole={currentRole}
            workspaceId={s.currentUser?.organization.id ?? 'Awaiting workspace'}
            currentPlan={currentPlan}
          />
        )
    }
  }

  const ActiveIcon = meta.icon

  return (
    <div data-onboarding="settings-page" className="min-h-full bg-canvas">
      <div className="mx-auto flex max-w-[1480px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <div
          data-onboarding="settings-header"
          className="rounded-[32px] border border-border bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] p-6 shadow-card sm:p-7"
        >
          <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-3xl">
              <p className="eyebrow">Settings</p>
              <h1 className="mt-3 text-display text-heading">Control your account, workspace, and billing with clarity.</h1>
              <p className="mt-4 max-w-[65ch] text-body">
                Everything here should help you manage identity, credits, privacy, and operational preferences without
                hunting through scattered forms.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-3 xl:min-w-[620px]">
              <SummaryCard
                label="Workspace role"
                value={currentRole.replace('_', ' ')}
                detail="Your current level of access inside this workspace."
              />
              <SummaryCard
                label="Current plan"
                value={currentPlan.replace('_', ' ')}
                detail="Plan and billing status for the active workspace."
              />
              <SummaryCard
                label="Credits remaining"
                value={remainingCredits}
                detail="Available credits before paid actions are blocked."
              />
            </div>
          </div>

          <div className="mt-6 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <div className="inline-flex items-start gap-3 rounded-[22px] border border-primary/12 bg-primary/5 px-4 py-3 text-sm text-body">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <ActiveIcon className="h-4 w-4" strokeWidth={1.7} />
              </div>
              <div>
                <p className="font-semibold text-heading">{meta.label}</p>
                <p className="mt-1 text-[0.82rem] leading-relaxed text-subtle">{meta.description}</p>
              </div>
            </div>

            <div data-onboarding="settings-tabs" className="lg:hidden">
              <SettingsTabs activeTab={s.activeTab} onTabChange={s.setActiveTab} />
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)]">
          <div data-onboarding="settings-tabs">
            <SettingsSidebar activeTab={activeKey as SettingsTab} onTabChange={s.setActiveTab} />
          </div>

          <section
            data-onboarding="settings-content"
            className="rounded-[32px] border border-border bg-surface p-4 shadow-card sm:p-5 lg:p-6"
          >
            {renderContent()}
          </section>
        </div>
      </div>
    </div>
  )
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-subtle">Loading settings…</div>}>
      <SettingsContent />
    </Suspense>
  )
}
