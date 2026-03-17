'use client'

import type { NotificationPrefs } from '@/lib/hooks/useSettings'

// ── Toggle row ────────────────────────────────────────────────────────────────

function ToggleRow({
  label,
  description,
  checked,
  onToggle,
}: {
  label: string
  description?: string
  checked: boolean
  onToggle: () => void
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5 border-b border-border last:border-0">
      <div>
        <p className="text-sm font-medium text-body">{label}</p>
        {description && <p className="mt-0.5 text-xs text-subtle">{description}</p>}
      </div>
      <button
        onClick={onToggle}
        role="switch"
        aria-checked={checked}
        className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
          checked ? 'bg-primary' : 'bg-muted'
        }`}
      >
        <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          checked ? 'translate-x-4' : 'translate-x-0'
        }`} />
      </button>
    </div>
  )
}

// ── Channel pill ──────────────────────────────────────────────────────────────

function ChannelToggle({
  label,
  checked,
  onToggle,
}: {
  label: string
  checked: boolean
  onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className={`rounded-xl border px-4 py-2 text-xs font-medium transition-all ${
        checked
          ? 'border-primary/30 bg-primary/8 text-primary'
          : 'border-border bg-surface text-subtle hover:border-primary/20 hover:text-body'
      }`}
    >
      {label}
    </button>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface NotificationsSectionProps {
  prefs: NotificationPrefs
  onToggle: (key: keyof NotificationPrefs) => void
}

export function NotificationsSection({ prefs, onToggle }: NotificationsSectionProps) {
  return (
    <div className="flex flex-col gap-8">
      {/* ── Delivery channels ─────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Delivery Channels</h3>
        <p className="mb-5 text-xs text-subtle">Choose how you receive notifications</p>
        <div className="flex gap-3">
          <ChannelToggle label="Email"  checked={prefs.emailEnabled} onToggle={() => onToggle('emailEnabled')} />
          <ChannelToggle label="Push"   checked={prefs.pushEnabled}  onToggle={() => onToggle('pushEnabled')} />
          <ChannelToggle label="SMS"    checked={prefs.smsEnabled}   onToggle={() => onToggle('smsEnabled')} />
        </div>
      </div>

      {/* ── Notification types ────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Notification Types</h3>
        <p className="mb-4 text-xs text-subtle">Select what you want to be notified about</p>
        <div>
          <ToggleRow
            label="Signal Alerts"
            description="Get notified when new high-confidence signals are detected"
            checked={prefs.signalAlerts}
            onToggle={() => onToggle('signalAlerts')}
          />
          <ToggleRow
            label="Weekly Digest"
            description="Receive a curated weekly intelligence summary every Monday"
            checked={prefs.weeklyDigest}
            onToggle={() => onToggle('weeklyDigest')}
          />
          <ToggleRow
            label="Contract Updates"
            description="Alerts when data contracts change status or have delivery issues"
            checked={prefs.contractUpdates}
            onToggle={() => onToggle('contractUpdates')}
          />
          <ToggleRow
            label="System Announcements"
            description="Platform updates, maintenance windows and new features"
            checked={prefs.systemAnnouncements}
            onToggle={() => onToggle('systemAnnouncements')}
          />
        </div>
      </div>
    </div>
  )
}
