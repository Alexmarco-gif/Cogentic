'use client'

import { useState } from 'react'
import { KeyRound, Loader2, Monitor, ShieldCheck } from 'lucide-react'

import type {
  APIKeyResponse,
  CreateAPIKeyRequest,
  MappedCreateAPIKeyResponse,
} from '@/lib/api/types'
import { formatLastSeen, type UserSession } from '@/lib/api/sessions'

interface SecuritySectionProps {
  twoFAEnabled: boolean
  onSetTwoFA: (value: boolean) => void
  sessions: UserSession[]
  sessionsLoading?: boolean
  onRevokeSession: (id: string) => Promise<void>
  apiKeys: APIKeyResponse[]
  onRevokeKey: (keyId: string) => Promise<void>
  onGenerateKey: (req: CreateAPIKeyRequest) => Promise<MappedCreateAPIKeyResponse | null>
  onRotateKey: (keyId: string) => Promise<MappedCreateAPIKeyResponse | null>
}

export function SecuritySection({
  sessions,
  sessionsLoading,
  onRevokeSession,
  apiKeys,
  onRevokeKey,
  onGenerateKey,
  onRotateKey,
}: SecuritySectionProps) {
  const [revoking, setRevoking] = useState<string | null>(null)
  const [rotating, setRotating] = useState<string | null>(null)
  const [revokingSession, setRevokingSession] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genOpen, setGenOpen] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyVisible, setNewKeyVisible] = useState<string | null>(null)

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

  async function handleRotate(keyId: string) {
    setRotating(keyId)
    try {
      const result = await onRotateKey(keyId)
      if (result?.key) {
        setNewKeyVisible(result.key)
      }
    } finally {
      setRotating(null)
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
    return new Date(iso).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/8">
            <ShieldCheck className="h-5 w-5 text-primary" strokeWidth={1.5} />
          </div>
          <div>
            <h3 className="text-sm font-medium text-heading">Identity security</h3>
            <p className="text-xs text-subtle">Password resets and multi-factor setup are managed by Auth0.</p>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-muted/30 p-4">
          <p className="text-sm font-medium text-body">Authentication settings live in the identity provider</p>
          <p className="mt-1 text-xs leading-relaxed text-subtle">
            Cogent does not store local passwords. Use the Auth0-hosted sign-in flow to reset your password,
            update your login method, or manage multi-factor authentication for this account.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <div className="mb-5 flex items-center gap-3">
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
            Loading sessions...
          </div>
        ) : sessions.length === 0 ? (
          <p className="text-xs italic text-subtle">No active sessions found.</p>
        ) : (
          <div className="flex flex-col gap-3">
            {sessions.map((session) => (
              <div
                key={session.id}
                className={`flex items-center justify-between rounded-xl border px-4 py-3 ${
                  session.is_current
                    ? 'border-emerald-200 bg-emerald-50/60'
                    : 'border-border bg-muted/40'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Monitor
                    className={`h-4 w-4 shrink-0 ${session.is_current ? 'text-emerald-600' : 'text-subtle'}`}
                    strokeWidth={1.5}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-medium text-heading">{session.device}</p>
                      {session.is_current && (
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                          This device
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-subtle">
                      {session.ip_address} · {formatLastSeen(session.last_active_at, session.is_current)}
                    </p>
                  </div>
                </div>

                {!session.is_current && (
                  <button
                    onClick={() => {
                      void handleRevokeSession(session.id)
                    }}
                    disabled={revokingSession === session.id}
                    className="flex items-center gap-1 text-[11px] font-medium text-rose-500 hover:underline disabled:opacity-50"
                  >
                    {revokingSession === session.id
                      ? <><Loader2 className="h-3 w-3 animate-spin" /> Signing out...</>
                      : 'Sign out'
                    }
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
        <h3 className="mb-1 text-sm font-medium text-heading">Active API Keys</h3>
        <p className="mb-5 text-xs text-subtle">Manage machine-to-machine access for the Cogent API.</p>

        {newKeyVisible && (
          <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="mb-1 text-xs font-medium text-emerald-700">
              API key created or rotated. Copy it now because it will not be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded-lg border border-emerald-200 bg-white px-3 py-1.5 font-mono text-[11px] text-emerald-800">
                {newKeyVisible}
              </code>
              <button
                onClick={() => {
                  void navigator.clipboard.writeText(newKeyVisible)
                }}
                className="shrink-0 rounded-lg border border-emerald-300 bg-white px-3 py-1.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-50"
              >
                Copy
              </button>
              <button
                onClick={() => setNewKeyVisible(null)}
                className="shrink-0 text-[11px] text-emerald-500 hover:text-emerald-700"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {apiKeys.length === 0 ? (
            <p className="text-xs italic text-subtle">No API keys yet. Generate one below.</p>
          ) : (
            apiKeys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3"
              >
                <div>
                  <p className="text-xs font-medium text-heading">{key.name}</p>
                  <p className="font-mono text-[11px] text-subtle">{key.key_prefix}••••••••••••</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[11px] text-subtle">Created {formatDate(key.created_at)}</span>
                  <button
                    onClick={() => {
                      void handleRotate(key.id)
                    }}
                    disabled={rotating === key.id || revoking === key.id}
                    className="flex items-center gap-1 text-[11px] font-medium text-primary hover:underline disabled:opacity-50"
                  >
                    {rotating === key.id
                      ? <><Loader2 className="h-3 w-3 animate-spin" /> Rotating...</>
                      : 'Rotate'
                    }
                  </button>
                  <button
                    onClick={() => {
                      void handleRevoke(key.id)
                    }}
                    disabled={revoking === key.id || rotating === key.id}
                    className="flex items-center gap-1 text-[11px] font-medium text-rose-500 hover:underline disabled:opacity-50"
                  >
                    {revoking === key.id
                      ? <><Loader2 className="h-3 w-3 animate-spin" /> Revoking...</>
                      : 'Revoke'
                    }
                  </button>
                </div>
              </div>
            ))
          )}

          {genOpen ? (
            <div className="mt-1 flex items-center gap-2">
              <input
                type="text"
                value={newKeyName}
                onChange={(event) => setNewKeyName(event.target.value)}
                placeholder="Key name (e.g. Production)"
                className="flex-1 rounded-xl border border-border bg-surface px-3 py-2 text-sm text-body placeholder:text-subtle focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20"
              />
              <button
                onClick={() => {
                  void handleGenerate()
                }}
                disabled={generating || !newKeyName.trim()}
                className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-medium text-white hover:bg-primary-hover disabled:opacity-50"
              >
                {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                {generating ? 'Generating...' : 'Generate'}
              </button>
              <button onClick={() => setGenOpen(false)} className="text-xs text-subtle hover:text-body">
                Cancel
              </button>
            </div>
          ) : (
            <button
              onClick={() => setGenOpen(true)}
              className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
            >
              <KeyRound className="h-3.5 w-3.5" />
              Generate new key
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
