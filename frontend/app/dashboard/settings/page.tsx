'use client'

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'
import { SETTINGS_TABS, useSettings, type SettingsTab } from '@/lib/hooks/useSettings'
import { SettingsTabs }          from '@/components/settings/SettingsTabs'
import { ProfileSection }        from '@/components/settings/ProfileSection'
import { SecuritySection }       from '@/components/settings/SecuritySection'
import { PreferencesSection }    from '@/components/settings/PreferencesSection'
import { UsageDashboard }        from '@/components/settings/UsageDashboard'
import { DataPrivacySection }    from '@/components/settings/DataPrivacySection'
import { LegalSection }          from '@/components/settings/LegalSection'

// ── Coming-soon wrapper for unconnected sections ─────────────────────────────

// ── Inner component (reads searchParams) ─────────────────────────────────────

function SettingsContent() {
  const searchParams = useSearchParams()
  const requestedTab = searchParams.get('tab') as SettingsTab | null
  const queryTab = SETTINGS_TABS.some((tab) => tab.id === requestedTab)
    ? requestedTab
    : 'profile'

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
      case 'preferences':
        return <PreferencesSection />
      case 'usage':
        return (
          <UsageDashboard
            usageData={s.usageData}
            planLimits={s.planLimits}
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
            onEditProfile={() => s.setEditingProfile(true)}
          />
        )
    }
  }

  return (
    <div
      data-onboarding="settings-page"
      className="flex flex-col overflow-hidden"
      style={{ height: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* ── Page header ──────────────────────────────────────────────────── */}
      <div data-onboarding="settings-header" className="flex-shrink-0 border-b border-border bg-surface px-8 pt-8 pb-0">
        <h1 className="text-2xl font-medium text-heading">Settings</h1>
        <p className="mt-0.5 mb-5 text-sm text-subtle">Manage your account settings and preferences.</p>
        <div data-onboarding="settings-tabs">
          <SettingsTabs activeTab={s.activeTab} onTabChange={s.setActiveTab} />
        </div>
      </div>

      {/* ── Scrollable content ───────────────────────────────────────────── */}
      <div data-onboarding="settings-content" className="flex-1 overflow-y-auto px-8 py-8">
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
