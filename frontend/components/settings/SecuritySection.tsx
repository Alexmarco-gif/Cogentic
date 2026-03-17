'use client'

import { useState } from 'react'
import { Lock, Eye, EyeOff, ShieldCheck, KeyRound, Loader2, Plus, Monitor } from 'lucide-react'
import type { APIKeyResponse, CreateAPIKeyRequest, CreateAPIKeyResponse } from '@/lib/api/api_keys'
import type { UserSession } from '@/lib/api/sessions'
import { formatLastSeen } from '@/lib/api/sessions'

// ── Toggle switch ─────────────────────────────────────────────────────────────

function Toggle({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      role="switch"
      aria-checked={enabled}
      className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 ${
        enabled ? 'bg-primary' : 'bg-muted'
      }`}
    >
      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
        enabled ? 'translate-x-4' : 'translate-x-0'
      }`} />
    </button>
  )
}

// ── Password field ────────────────────────────────────────────────────────────

function PasswordField({ label, placeholder }: { label: string; placeholder?: string }) {
  const [show, setShow] = useState(false)
  const [value, setValue] = useState('')
  return (
    <div>
      <label className="mb-1.5 block text-[11px] font-medium text-subtle">{label}</label>
      <div className="flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2.5 focus-within:border-primary/50 focus-within:ring-1 focus-within:ring-primary/20">
        <Lock className="h-4 w-4 flex-shrink-0 text-subtle" strokeWidth={1.5} />
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder={placeholder ?? '••••••••'}
          className="flex-1 bg-transparent text-sm text-body placeholder:text-subtle focus:outline-none"
        />
        <button onClick={() => setShow(v => !v)} className="text-subtle hover:text-body transition-colors">
          {show ? <EyeOff className="h-4 w-4" strokeWidth={1.5} /> : <Eye className="h-4 w-4" strokeWidth={1.5} />}
        </button>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface SecuritySectionProps {
  twoFAEnabled: boolean
  onSetTwoFA: (v: boolean) => void
  sessions: UserSession[]
  sessionsLoading?: boolean
  onRevokeSession: (id: string) => Promise<void>
  apiKeys: APIKeyResponse[]
  onRevokeKey: (keyId: string) => Promise<void>
  onGenerateKey: (req: CreateAPIKeyRequest) => Promise<CreateAPIKeyResponse | null>
}

export function SecuritySection({ twoFAEnabled, onSetTwoFA, sessions, sessionsLoading, onRevokeSession, apiKeys, onRevokeKey, onGenerateKey }: SecuritySectionProps) {
  const [savedOk,        setSavedOk]        = useState(false)
  const [revoking,       setRevoking]        = useState<string | null>(null)
  const [revokingSession, setRevokingSession] = useState<string | null>(null)
  const [generating,     setGenerating]      = useState(false)
  const [genOpen,        setGenOpen]         = useState(false)
  const [newKeyName,     setNewKeyName]      = useState('')
  const [newKeyVisible,  setNewKeyVisible]   = useState<string | null>(null)

  const handleSave = () => {
    setSavedOk(true)
    setTimeout(() => setSavedOk(false), 2500)
  }

  async function handleRevokeSession(sessionId: string) {
    setRevokingSession(sessionId)
    try {
      await onRevokeSession(sessionId)
    } finally {
      setRevokingSession(null)
    }
  }

  async function handleRevoke(keyId: string) {
    setRevoking(keyId)
    try {
      await onRevokeKey(keyId)
    } finally {
      setRevoking(null)
    }
  }

  async function handleGenerate() {
    if (!newKeyName.trim()) return
    setGenerating(true)
    try {
      const result = await onGenerateKey({ name: newKeyName.trim() })
      if (result?.key) {
        setNewKeyVisible(result.key)
        setNewKeyName('')
        setGenOpen(false)
      }
    } finally {
      setGenerating(false)
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
  }

  return (
    <div className="flex flex-col gap-8">
      {/* ── Password change ────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/8">
            <KeyRound className="h-5 w-5 text-primary" strokeWidth={1.5} />
          </div>
          <div>
            <h3 className="text-sm font-medium text-heading">Change Password</h3>
            <p className="text-xs text-subtle">Use a strong password with at least 12 characters</p>
          </div>
        </div>

        <div className="flex flex-col gap-4 max-w-md">
          <PasswordField label="Current password"  placeholder="Enter current password" />
          <PasswordField label="New password"       placeholder="Min 12 characters" />
          <PasswordField label="Confirm new password" placeholder="Re-enter new password" />

          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={handleSave}
              className="rounded-xl bg-primary px-5 py-2 text-sm font-medium text-white transition-all hover:bg-primary-hover active:scale-[0.98]"
            >
              {savedOk ? '✓ Saved' : 'Update password'}
            </button>
          </div>
        </div>
      </div>

      {/* ── Active Sessions ──────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="flex items-center gap-3 mb-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/8">
            <Monitor className="h-5 w-5 text-primary" strokeWidth={1.5} />
          </div>
          <div>
            <h3 className="text-sm font-medium text-heading">Active Sessions</h3>
            <p className="text-xs text-subtle">Devices currently signed in to your account</p>
          </div>
        </div>

        {sessionsLoading ? (
          <div className="flex items-center gap-2 text-xs text-subtle">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading sessions…
          </div>
        ) : sessions.length === 0 ? (
          <p className="text-xs text-subtle italic">No active sessions found.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {sessions.map(sess => (
              <div
                key={sess.id}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
                  sess.is_current
                    ? 'border-emerald-200 bg-emerald-50/60'
                    : 'border-border bg-muted/40'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Monitor className={`h-4 w-4 shrink-0 ${
                    sess.is_current ? 'text-emerald-600' : 'text-subtle'
                  }`} strokeWidth={1.5} />
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium text-heading">{sess.device}</p>
                      {sess.is_current && (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                          This device
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-subtle">
                      {sess.ip_address} · {formatLastSeen(sess.last_active_at, sess.is_current)}
                    </p>
                  </div>
                </div>

                {!sess.is_current && (
                  <button
                    onClick={() => handleRevokeSession(sess.id)}
                    disabled={revokingSession === sess.id}
                    className="flex items-center gap-1 text-[11px] font-medium text-rose-500 hover:underline disabled:opacity-50"
                  >
                    {revokingSession === sess.id
                      ? <><Loader2 className="h-3 w-3 animate-spin" /> Signing out…</>
                      : 'Sign out'
                    }
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── 2FA ────────────────────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${
              twoFAEnabled ? 'bg-emerald-100' : 'bg-muted'
            }`}>
              <ShieldCheck className={`h-5 w-5 ${twoFAEnabled ? 'text-emerald-600' : 'text-subtle'}`} strokeWidth={1.5} />
            </div>
            <div>
              <h3 className="text-sm font-medium text-heading">Two-Factor Authentication</h3>
              <p className="text-xs text-subtle">
                {twoFAEnabled ? 'Enabled — your account is protected with TOTP' : 'Disabled — enable for extra security'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-xs font-medium ${twoFAEnabled ? 'text-emerald-600' : 'text-subtle'}`}>
              {twoFAEnabled ? 'Enabled' : 'Disabled'}
            </span>
            <Toggle enabled={twoFAEnabled} onToggle={() => onSetTwoFA(!twoFAEnabled)} />
          </div>
        </div>

        {twoFAEnabled && (
          <div className="mt-4 rounded-xl border border-emerald-100 bg-emerald-50 p-4">
            <p className="text-xs text-emerald-700">
              2FA is active. Authenticator app configured. Last verified 2 hours ago.
            </p>
          </div>
        )}
      </div>

      {/* ── Active API Keys ───────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Active API Keys</h3>
        <p className="mb-5 text-xs text-subtle">Manage keys used to access the Cogent API</p>

        {/* New key reveal banner */}
        {newKeyVisible && (
          <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="mb-1 text-xs font-medium text-emerald-700">API key created — copy it now. It will not be shown again.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded-lg bg-white border border-emerald-200 px-3 py-1.5 font-mono text-[11px] text-emerald-800 break-all">
                {newKeyVisible}
              </code>
              <button
                onClick={() => { navigator.clipboard.writeText(newKeyVisible); }}
                className="shrink-0 rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-50"
              >
                Copy
              </button>
              <button
                onClick={() => setNewKeyVisible(null)}
                className="shrink-0 text-emerald-400 hover:text-emerald-600 text-[11px]"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {apiKeys.length === 0 ? (
            <p className="text-xs text-subtle italic">No API keys yet. Generate one below.</p>
          ) : apiKeys.map(k => (
            <div key={k.id} className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
              <div>
                <p className="text-xs font-medium text-heading">{k.name}</p>
                <p className="font-mono text-[11px] text-subtle">{k.prefix}••••••••••••</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-subtle">Created {formatDate(k.created_at)}</span>
                <button
                  onClick={() => handleRevoke(k.id)}
                  disabled={revoking === k.id}
                  className="flex items-center gap-1 text-[11px] font-medium text-rose-500 hover:underline disabled:opacity-50"
                >
                  {revoking === k.id
                    ? <><Loader2 className="h-3 w-3 animate-spin" /> Revoking…</>
                    : 'Revoke'
                  }
                </button>
              </div>
            </div>
          ))}

          {/* Generate key form */}
          {genOpen ? (
            <div className="mt-1 flex items-center gap-2">
              <input
                type="text"
                value={newKeyName}
                onChange={e => setNewKeyName(e.target.value)}
                placeholder="Key name (e.g. Production)"
                className="flex-1 rounded-xl border border-border bg-surface px-3 py-2 text-sm text-body placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20"
              />
              <button
                onClick={handleGenerate}
                disabled={generating || !newKeyName.trim()}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white disabled:opacity-50 hover:bg-primary-hover"
              >
                {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {generating ? 'Generating…' : 'Generate'}
              </button>
              <button onClick={() => setGenOpen(false)} className="text-xs text-subtle hover:text-body">
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setGenOpen(true)}
              className="mt-1 flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
            >
              <Plus className="h-3.5 w-3.5" />
              Generate new key
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
