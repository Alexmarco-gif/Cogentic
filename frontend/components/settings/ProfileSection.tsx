'use client'

import { useState } from 'react'
import {
  User, Mail, Phone, Calendar, MapPin, Building2,
  BadgeCheck, Edit3, ShieldCheck, Monitor, Trash2, Globe,
} from 'lucide-react'
import type { UserProfile } from '@/lib/hooks/useSettings'
import type { UserSession } from '@/lib/api/sessions'
import { formatLastSeen } from '@/lib/api/sessions'

// ── Helpers ───────────────────────────────────────────────────────────────────

function FieldRow({
  icon: Icon,
  label,
  value,
  badge,
}: {
  icon: React.ElementType
  label: string
  value: string
  badge?: React.ReactNode
}) {
  return (
    <div className="flex items-start gap-3 py-1">
      <Icon className="mt-0.5 h-4 w-4 flex-shrink-0 text-subtle" strokeWidth={1.5} />
      <div className="min-w-0">
        <p className="text-[10px] text-subtle">{label}</p>
        <div className="flex items-center gap-2">
          <p className="text-sm text-body">{value}</p>
          {badge}
        </div>
      </div>
    </div>
  )
}

function VerifiedBadge({ label = 'Verified' }: { label?: string }) {
  return (
    <span className="flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
      <BadgeCheck className="h-3 w-3" />
      {label}
    </span>
  )
}

// ── Access history row ────────────────────────────────────────────────────────

function SessionRow({ session, onRevoke }: { session: UserSession; onRevoke: (id: string) => void }) {
  return (
    <div className="flex items-center gap-4 py-3 border-b border-border last:border-0">
      <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
        <Monitor className="h-4 w-4 text-subtle" strokeWidth={1.5} />
      </div>
      <div className="flex-1 min-w-0 grid grid-cols-[1fr_140px_140px] gap-2 items-center">
        <div>
          <p className="text-xs font-medium text-heading">{session.device}</p>
          <p className="text-[11px] text-subtle font-mono">{session.ip_address}</p>
        </div>
        <div />
        <p className="text-[11px] text-subtle">
          {session.is_current
            ? <span className="flex items-center gap-1.5 text-emerald-600">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-600" />
                </span>
                Active now
              </span>
            : formatLastSeen(session.last_active_at, false)}
        </p>
      </div>
      {!session.is_current && (
        <button
          onClick={() => onRevoke(session.id)}
          className="flex-shrink-0 rounded-lg border border-rose-100 bg-rose-50 px-2.5 py-1 text-[11px] font-medium text-rose-600 hover:bg-rose-100 transition-colors"
        >
          Revoke
        </button>
      )}
      {session.is_current && (
        <span className="flex-shrink-0 rounded-lg border border-emerald-100 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-600">
          Current
        </span>
      )}
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface ProfileSectionProps {
  profile: UserProfile
  sessions: UserSession[]
  onRevokeSession: (id: string) => Promise<void> | void
  onEditProfile: () => void
}

export function ProfileSection({
  profile,
  sessions,
  onRevokeSession,
  onEditProfile,
}: ProfileSectionProps) {
  const [loginAlerts, setLoginAlerts] = useState(true)

  return (
    <div className="flex flex-col gap-6">
      {/* ── Cover + avatar hero ──────────────────────────────────────────── */}
      <div className="overflow-hidden rounded-2xl border border-border shadow-card">
        {/* Cover gradient */}
        <div className={`h-32 w-full bg-gradient-to-r ${profile.coverGradient}`} />

        {/* Avatar row */}
        <div className="relative px-6 pb-5">
          <div className="absolute -top-10 left-6">
            <div className="h-20 w-20 overflow-hidden rounded-2xl border-4 border-surface shadow-card bg-muted">
              {profile.avatarUrl ? (
                <img src={profile.avatarUrl} alt={profile.fullName} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-primary/10 text-2xl font-medium text-primary">
                  {profile.fullName.charAt(0)}
                </div>
              )}
            </div>
          </div>

          <div className="pt-12 flex items-end justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-medium text-heading">{profile.fullName}</h2>
                <span className="flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                  <BadgeCheck className="h-3 w-3" />
                  Verified Profile
                </span>
              </div>
              <p className="mt-0.5 flex items-center gap-1.5 text-xs text-subtle">
                <Calendar className="h-3 w-3" strokeWidth={1.5} />
                Member since 27 Jan 2025
              </p>
            </div>
            <button
              onClick={onEditProfile}
              className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-1.5 text-xs font-medium text-body shadow-sm hover:bg-muted transition-colors"
            >
              <Edit3 className="h-3.5 w-3.5" strokeWidth={1.5} />
              Edit Profile
            </button>
          </div>
        </div>
      </div>

      {/* ── Profile details grid ─────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-5 shadow-card">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-medium text-heading">Profile details</h3>
          <button className="flex items-center gap-1 text-xs text-subtle hover:text-body transition-colors">
            <Edit3 className="h-3 w-3" strokeWidth={1.5} />
            Edit
          </button>
        </div>

        <div className="grid grid-cols-3 gap-x-8 gap-y-4">
          <FieldRow icon={User}       label="Full Name"     value={profile.fullName} />
          <FieldRow icon={Mail}       label="Email"         value={profile.email}
            badge={profile.emailVerified ? <VerifiedBadge label="Email Verified" /> : undefined}
          />
          <FieldRow icon={Calendar}   label="Date of birth" value={profile.dateOfBirth} />
          <FieldRow icon={User}       label="Username"      value={profile.username} />
          <FieldRow icon={Phone}      label="Number"        value={profile.phone}
            badge={profile.phoneVerified ? <VerifiedBadge label="Number Verified" /> : undefined}
          />
          <FieldRow icon={ShieldCheck} label="Plan"         value={profile.plan} />
          <FieldRow icon={MapPin}     label="Address"       value={profile.address} />
          <FieldRow icon={Building2}  label="City"          value={profile.city} />
          <FieldRow icon={Globe}      label="Postal Code"   value={profile.postalCode} />
        </div>
      </div>

      {/* ── Access history ───────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-5 shadow-card">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-medium text-heading">Access History</h3>
          </div>
          <div className="flex items-center gap-4">
            {/* Login alerts toggle */}
            <label className="flex cursor-pointer items-center gap-2 text-xs text-subtle">
              <span className="font-medium text-body">New Login Alerts</span>
              <button
                onClick={() => setLoginAlerts(v => !v)}
                className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none ${
                  loginAlerts ? 'bg-primary' : 'bg-muted'
                }`}
                role="switch"
                aria-checked={loginAlerts}
              >
                <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  loginAlerts ? 'translate-x-4' : 'translate-x-0'
                }`} />
              </button>
            </label>
            <button
              onClick={() => sessions.filter(s => !s.is_current).forEach(s => onRevokeSession(s.id))}
              className="flex items-center gap-1.5 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-medium text-rose-600 hover:bg-rose-100 transition-colors"
            >
              <Trash2 className="h-3 w-3" />
              Logout of all others
            </button>
          </div>
        </div>

        {/* Column headers */}
        <div className="grid grid-cols-[1fr_140px_140px_80px] gap-2 border-b border-border py-2 text-[10px] font-semibold uppercase tracking-wider text-subtle">
          <span>Location</span>
          <span>Device</span>
          <span>ID Address</span>
          <span>Action</span>
        </div>

        {sessions.map(session => (
          <SessionRow key={session.id} session={session} onRevoke={onRevokeSession} />
        ))}
      </div>
    </div>
  )
}
