'use client'

import { useMemo, useState, type ElementType, type ReactNode } from 'react'
import {
  BadgeCheck,
  Building2,
  Calendar,
  Globe,
  LockKeyhole,
  Mail,
  Monitor,
  Phone,
  ShieldCheck,
  Trash2,
  User,
  WalletCards,
} from 'lucide-react'

import type { UserProfile } from '@/lib/hooks/useSettings'
import type { UserSession } from '@/lib/api/sessions'
import { formatLastSeen } from '@/lib/api/sessions'

function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string
  value: string
  detail: string
  icon: ElementType
}) {
  return (
    <div className="rounded-[22px] border border-border bg-surface px-4 py-4 shadow-card">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/8 text-primary">
          <Icon className="h-4 w-4" strokeWidth={1.7} />
        </div>
        <div className="min-w-0">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-subtle">{label}</p>
          <p className="mt-1 truncate text-[0.98rem] font-semibold text-heading">{value}</p>
        </div>
      </div>
      <p className="mt-3 text-[0.78rem] leading-relaxed text-subtle">{detail}</p>
    </div>
  )
}

function DetailRow({
  icon: Icon,
  label,
  value,
  badge,
}: {
  icon: ElementType
  label: string
  value: string
  badge?: ReactNode
}) {
  return (
    <div className="flex items-start gap-3 rounded-[20px] border border-border bg-surface px-4 py-3">
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl bg-muted text-subtle">
        <Icon className="h-4 w-4" strokeWidth={1.7} />
      </div>
      <div className="min-w-0">
        <p className="text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-subtle">{label}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <p className="text-[0.92rem] text-body">{value}</p>
          {badge}
        </div>
      </div>
    </div>
  )
}

function VerifiedBadge({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[0.68rem] font-semibold text-emerald-700">
      <BadgeCheck className="h-3 w-3" strokeWidth={1.8} />
      {label}
    </span>
  )
}

function SessionItem({
  session,
  onRevoke,
}: {
  session: UserSession
  onRevoke: (id: string) => void
}) {
  return (
    <div className="rounded-[22px] border border-border bg-surface px-4 py-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-muted text-subtle">
            <Monitor className="h-4 w-4" strokeWidth={1.7} />
          </div>
          <div>
            <p className="text-[0.9rem] font-semibold text-heading">{session.device}</p>
            <p className="mt-1 text-[0.78rem] font-mono text-subtle">{session.ip_address}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span
            className={
              session.is_current
                ? 'inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[0.72rem] font-semibold text-emerald-700'
                : 'inline-flex items-center rounded-full border border-border bg-muted/50 px-2.5 py-1 text-[0.72rem] font-semibold text-subtle'
            }
          >
            {session.is_current ? 'Current session' : formatLastSeen(session.last_active_at, false)}
          </span>

          {!session.is_current ? (
            <button
              onClick={() => onRevoke(session.id)}
              className="button-press inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-50 px-3 py-1.5 text-[0.76rem] font-semibold text-rose-700 transition-colors hover:bg-rose-100"
            >
              Revoke
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

interface ProfileSectionProps {
  profile: UserProfile
  sessions: UserSession[]
  onRevokeSession: (id: string) => Promise<void> | void
  workspaceRole: string
  workspaceId: string
  currentPlan: string
}

export function ProfileSection({
  profile,
  sessions,
  onRevokeSession,
  workspaceRole,
  workspaceId,
  currentPlan,
}: ProfileSectionProps) {
  const [loginAlerts, setLoginAlerts] = useState(true)

  const locationLabel = useMemo(() => {
    const parts = [profile.city, profile.country].filter(Boolean)
    return parts.length > 0 ? parts.join(', ') : 'Not added yet'
  }, [profile.city, profile.country])

  return (
    <div className="flex flex-col gap-6">
      <div className="overflow-hidden rounded-[28px] border border-border bg-[linear-gradient(135deg,rgba(255,255,255,0.98),rgba(248,250,252,0.98))] shadow-card">
        <div className={`h-28 w-full bg-gradient-to-r ${profile.coverGradient}`} />

        <div className="relative px-5 pb-5 pt-0 sm:px-6 sm:pb-6">
          <div className="-mt-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-[24px] border-4 border-surface bg-primary/10 text-[1.65rem] font-semibold text-primary shadow-card">
                {profile.avatarUrl ? (
                  <img src={profile.avatarUrl} alt={profile.fullName} className="h-full w-full object-cover" />
                ) : (
                  profile.fullName.charAt(0) || 'C'
                )}
              </div>

              <div className="pt-10 sm:pt-8">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-title text-heading">{profile.fullName || 'Your profile'}</h2>
                  <VerifiedBadge label="Verified account" />
                </div>
                <p className="mt-2 max-w-[60ch] text-sm text-body">
                  Manage your identity, workspace access, and secure sessions without digging through unnecessary
                  personal profile fields.
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[0.76rem] text-subtle">
                  <span className="inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1">
                    <Calendar className="h-3 w-3" strokeWidth={1.7} />
                    Workspace member
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full border border-border bg-surface px-2.5 py-1">
                    <ShieldCheck className="h-3 w-3" strokeWidth={1.7} />
                    Secure access enabled
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="Workspace role"
          value={workspaceRole.replace('_', ' ')}
          detail="Your current access level inside the active Cogent workspace."
          icon={ShieldCheck}
        />
        <MetricCard
          label="Current plan"
          value={currentPlan.replace('_', ' ')}
          detail="Billing tier currently attached to this workspace."
          icon={WalletCards}
        />
        <MetricCard
          label="Workspace ID"
          value={workspaceId}
          detail="The workspace context this account is operating inside."
          icon={Building2}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
        <div className="rounded-[28px] border border-border bg-surface p-5 shadow-card sm:p-6">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <p className="eyebrow">Identity</p>
              <h3 className="mt-2 text-title text-heading">Account details</h3>
              <p className="mt-2 text-sm text-subtle">
                The essentials your workspace needs for identity, collaboration, and secure communication.
              </p>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <DetailRow
              icon={User}
              label="Full name"
              value={profile.fullName || 'Not added yet'}
            />
            <DetailRow
              icon={Mail}
              label="Work email"
              value={profile.email || 'Not added yet'}
              badge={profile.emailVerified ? <VerifiedBadge label="Email verified" /> : undefined}
            />
            <DetailRow
              icon={User}
              label="Username"
              value={profile.username || 'Not added yet'}
            />
            <DetailRow
              icon={Phone}
              label="Phone"
              value={profile.phone || 'Not added yet'}
              badge={profile.phoneVerified ? <VerifiedBadge label="Phone verified" /> : undefined}
            />
            <DetailRow
              icon={Globe}
              label="Region"
              value={locationLabel}
            />
            <DetailRow
              icon={LockKeyhole}
              label="Access posture"
              value={loginAlerts ? 'New login alerts enabled' : 'New login alerts muted'}
            />
          </div>
        </div>

        <div className="rounded-[28px] border border-border bg-surface p-5 shadow-card sm:p-6">
          <p className="eyebrow">Workspace context</p>
          <h3 className="mt-2 text-title text-heading">How this account is set up</h3>
          <p className="mt-2 text-sm text-subtle">
            A clearer summary of what this account can access inside Cogent right now.
          </p>

          <div className="mt-5 space-y-3">
            <DetailRow icon={Building2} label="Workspace" value={workspaceId} />
            <DetailRow icon={ShieldCheck} label="Role" value={workspaceRole.replace('_', ' ')} />
            <DetailRow icon={WalletCards} label="Plan" value={currentPlan.replace('_', ' ')} />
          </div>

          <div className="mt-5 rounded-[24px] border border-border bg-muted/35 px-4 py-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[0.86rem] font-semibold text-heading">New login alerts</p>
                <p className="mt-1 text-[0.78rem] leading-relaxed text-subtle">
                  Receive a heads-up when this account signs in from a new device or location.
                </p>
              </div>
              <button
                onClick={() => setLoginAlerts((value) => !value)}
                className={`relative inline-flex h-6 w-11 shrink-0 rounded-full transition-colors ${
                  loginAlerts ? 'bg-primary' : 'bg-muted'
                }`}
                role="switch"
                aria-checked={loginAlerts}
              >
                <span
                  className={`inline-block h-5 w-5 translate-y-0.5 rounded-full bg-white shadow transition-transform ${
                    loginAlerts ? 'translate-x-5' : 'translate-x-0.5'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-[28px] border border-border bg-surface p-5 shadow-card sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="eyebrow">Security</p>
            <h3 className="mt-2 text-title text-heading">Active sessions</h3>
            <p className="mt-2 text-sm text-subtle">
              Review where this account is signed in and revoke sessions you no longer trust.
            </p>
          </div>

          <button
            onClick={() => sessions.filter((session) => !session.is_current).forEach((session) => onRevokeSession(session.id))}
            className="button-press inline-flex h-11 items-center justify-center gap-2 self-start rounded-[18px] border border-rose-200 bg-rose-50 px-4 text-[0.82rem] font-semibold text-rose-700 transition-colors hover:bg-rose-100"
          >
            <Trash2 className="h-4 w-4" strokeWidth={1.7} />
            Log out other sessions
          </button>
        </div>

        <div className="mt-5 space-y-3">
          {sessions.map((session) => (
            <SessionItem key={session.id} session={session} onRevoke={(id) => void onRevokeSession(id)} />
          ))}
        </div>
      </div>
    </div>
  )
}
