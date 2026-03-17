'use client'

import { useState, useEffect } from 'react'
import { Archive, History, Trash2, Brain, FolderOpen, AlertTriangle, ChevronRight, Loader2 } from 'lucide-react'
import { clearUserHistory, requestDataDeletion, requestDataExport } from '@/lib/api/privacy'
import { listBriefs, updateBriefStatus } from '@/lib/api/briefs'
import type { BriefResponse } from '@/lib/api/types'

// ── Toggle switch ─────────────────────────────────────────────────────────────

function Toggle({ enabled, onToggle, disabled }: { enabled: boolean; onToggle: () => void; disabled?: boolean }) {
  return (
    <button
      onClick={onToggle}
      disabled={disabled}
      role="switch"
      aria-checked={enabled}
      className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:opacity-50 ${
        enabled ? 'bg-primary' : 'bg-muted'
      }`}
    >
      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
        enabled ? 'translate-x-4' : 'translate-x-0'
      }`} />
    </button>
  )
}

// ── Confirm dialog ────────────────────────────────────────────────────────────

function ConfirmDialog({
  title,
  body,
  confirmLabel,
  destructive,
  onConfirm,
  onCancel,
}: {
  title: string
  body: string
  confirmLabel: string
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-surface p-6 shadow-modal">
        <div className="mb-4 flex items-start gap-3">
          <AlertTriangle className={`mt-0.5 h-5 w-5 flex-shrink-0 ${destructive ? 'text-rose-500' : 'text-amber-500'}`} strokeWidth={1.5} />
          <div>
            <p className="text-sm font-medium text-heading">{title}</p>
            <p className="mt-1 text-xs leading-relaxed text-subtle">{body}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-border py-2 text-sm font-medium text-body hover:bg-muted transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 rounded-xl py-2 text-sm font-medium text-white transition-colors ${
              destructive ? 'bg-rose-500 hover:bg-rose-600' : 'bg-primary hover:bg-primary-hover'
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function DataPrivacySection() {
  const [allowAiLearning, setAllowAiLearning] = useState(true)
  const [personalised,   setPersonalised]     = useState(true)
  const [analytics,      setAnalytics]        = useState(false)
  const [showArchived,   setShowArchived]      = useState(false)
  const [confirm, setConfirm] = useState<null | 'history' | 'account'>(null)
  const [historyCleared, setHistoryCleared]   = useState(false)
  const [confirming, setConfirming]           = useState(false)
  const [deletionRequested, setDeletionRequested] = useState(false)
  const [exportRequesting, setExportRequesting] = useState(false)
  const [exportRequested, setExportRequested]   = useState(false)
  const [exportError, setExportError]           = useState(false)
  const [historyError, setHistoryError]         = useState(false)
  const [deletionError, setDeletionError]       = useState(false)
  const [archivedBriefs, setArchivedBriefs]     = useState<BriefResponse[]>([])
  const [restoringId, setRestoringId]           = useState<string | null>(null)

  useEffect(() => {
    listBriefs({ status: 'archived', limit: 50 })
      .then(res => setArchivedBriefs(res.items ?? []))
      .catch(() => { /* keep empty state on error */ })
  }, [])

  async function handleConfirm() {
    setConfirming(true)
    setHistoryError(false)
    setDeletionError(false)
    try {
      if (confirm === 'history') {
        await clearUserHistory()
        setHistoryCleared(true)
      } else if (confirm === 'account') {
        await requestDataDeletion()
        setDeletionRequested(true)
      }
    } catch {
      if (confirm === 'history') setHistoryError(true)
      else setDeletionError(true)
    } finally {
      setConfirming(false)
      setConfirm(null)
    }
  }

  async function handleRequestExport() {
    setExportRequesting(true)
    setExportError(false)
    try {
      await requestDataExport()
      setExportRequested(true)
    } catch {
      setExportError(true)
    } finally {
      setExportRequesting(false)
    }
  }

  async function handleRestore(brief: BriefResponse) {
    setRestoringId(brief.id)
    try {
      await updateBriefStatus(brief.id, { status: 'published' })
      setArchivedBriefs(prev => prev.filter(b => b.id !== brief.id))
    } catch {
      // Keep item in list on failure
    } finally {
      setRestoringId(null)
    }
  }

  return (
    <>
      {confirm && (
        <ConfirmDialog
          title={confirm === 'history' ? 'Clear all history?' : 'Request data deletion?'}
          body={
            confirm === 'history'
              ? 'This will permanently delete all your investigation sessions, chat history, and search history. This cannot be undone.'
              : 'We will send you an email to begin the account data deletion process. This may take up to 30 days to complete.'
          }
          confirmLabel={
            confirming
              ? confirm === 'history' ? 'Clearing…' : 'Submitting…'
              : confirm === 'history' ? 'Clear history' : 'Request deletion'
          }
          destructive
          onConfirm={handleConfirm}
          onCancel={() => !confirming && setConfirm(null)}
        />
      )}

      <div className="flex flex-col gap-8">

        {/* ── AI & Model learning ───────────────────────────────────────── */}
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
          <div className="mb-1 flex items-center gap-2">
            <Brain className="h-4 w-4 text-primary" strokeWidth={1.5} />
            <h3 className="text-sm font-medium text-heading">AI & Model Learning</h3>
          </div>
          <p className="mb-5 text-xs text-subtle">
            Control whether Cogent can use your usage data to improve the intelligence models.
          </p>

          <div className="flex flex-col divide-y divide-border">
            {[
              {
                key: 'aiLearning',
                label: 'Allow model improvement',
                desc: 'Let Cogent use anonymised patterns from your queries to improve signal detection accuracy',
                value: allowAiLearning,
                onToggle: () => setAllowAiLearning(v => !v),
              },
              {
                key: 'personalised',
                label: 'Personalised intelligence',
                desc: 'Tailor signals, briefs, and recommendations based on your tracked entities and interests',
                value: personalised,
                onToggle: () => setPersonalised(v => !v),
              },
              {
                key: 'analytics',
                label: 'Share usage analytics',
                desc: 'Send anonymous product usage data to help improve the platform experience',
                value: analytics,
                onToggle: () => setAnalytics(v => !v),
              },
            ].map(row => (
              <div key={row.key} className="flex items-center justify-between gap-4 py-4">
                <div>
                  <p className="text-sm font-medium text-body">{row.label}</p>
                  <p className="mt-0.5 text-xs text-subtle">{row.desc}</p>
                </div>
                <Toggle enabled={row.value} onToggle={row.onToggle} />
              </div>
            ))}
          </div>
        </div>

        {/* ── History & Archive ──────────────────────────────────────────── */}
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
          <div className="mb-1 flex items-center gap-2">
            <History className="h-4 w-4 text-subtle" strokeWidth={1.5} />
            <h3 className="text-sm font-medium text-heading">History & Archive</h3>
          </div>
          <p className="mb-5 text-xs text-subtle">Manage your investigation sessions, searches, and archived items.</p>

          <div className="flex flex-col gap-3">
            {/* Clear history */}
            <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
              <div className="flex items-center gap-3">
                <Trash2 className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-body">
                    Clear all history
                    {historyCleared && <span className="ml-2 text-[10px] font-normal text-emerald-600">✓ Cleared</span>}
                  </p>
                  <p className="text-xs text-subtle">Deletes investigation sessions, chats, and search history</p>
                </div>
              </div>
              <button
                onClick={() => setConfirm('history')}
                disabled={historyCleared}
                className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-medium text-rose-600 hover:bg-rose-100 transition-colors disabled:opacity-40"
              >
                Clear
              </button>
            </div>
            {historyError && <p className="text-[10px] text-rose-500 px-1">Failed to clear history. Please try again.</p>}
            </div>

            {/* Archive data */}
            <div className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
              <div className="flex items-center gap-3">
                <Archive className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-body">Archive my data</p>
                  <p className="text-xs text-subtle">Download a full export of your contracts, briefs, and history</p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <button
                  onClick={handleRequestExport}
                  disabled={exportRequesting || exportRequested}
                  className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-1.5 text-[11px] font-medium text-body hover:bg-muted transition-colors disabled:opacity-50"
                >
                  {exportRequesting && <Loader2 className="h-3 w-3 animate-spin" />}
                  {exportRequested ? '✓ Requested — check your email' : exportRequesting ? 'Requesting…' : 'Request export'}
                </button>
                {exportError && <p className="text-[10px] text-rose-500">Request failed — please try again.</p>}
              </div>
            </div>

            {/* View archived */}
            <button
              onClick={() => setShowArchived(v => !v)}
              className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3 text-left w-full hover:bg-muted/70 transition-colors"
            >
              <div className="flex items-center gap-3">
                <FolderOpen className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-body">View archived data</p>
                  <p className="text-xs text-subtle">{archivedBriefs.length} archived item{archivedBriefs.length !== 1 ? 's' : ''}</p>
                </div>
              </div>
              <ChevronRight className={`h-4 w-4 text-subtle transition-transform ${showArchived ? 'rotate-90' : ''}`} strokeWidth={1.5} />
            </button>

            {/* Archived list */}
            {showArchived && (
              <div className="ml-4 flex flex-col gap-1.5">
                {archivedBriefs.length === 0 && (
                  <p className="px-4 py-3 text-xs text-subtle">No archived items.</p>
                )}
                {archivedBriefs.map(brief => (
                  <div key={brief.id} className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-2.5">
                    <div>
                      <p className="text-xs font-medium text-body">{brief.title}</p>
                      <p className="text-[10px] text-subtle">{brief.brief_type} · Archived {formatDate(brief.updated_at)}</p>
                    </div>
                    <button
                      onClick={() => handleRestore(brief)}
                      disabled={restoringId === brief.id}
                      className="flex items-center gap-1 text-xs font-medium text-primary hover:underline disabled:opacity-50"
                    >
                      {restoringId === brief.id && <Loader2 className="h-3 w-3 animate-spin" />}
                      {restoringId === brief.id ? 'Restoring…' : 'Restore'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ── Account data ──────────────────────────────────────────────── */}
        <div className="rounded-2xl border border-rose-100 bg-rose-50/50 p-6">
          <h3 className="mb-1 text-sm font-medium text-rose-700">Delete account data</h3>
          <p className="mb-4 text-xs text-rose-600">
            Request permanent deletion of all your data. This will remove your account, contracts, and history after a 30-day grace period.
          </p>
          <button
            onClick={() => !deletionRequested && setConfirm('account')}
            disabled={deletionRequested}
            className="rounded-xl border border-rose-300 bg-white px-4 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 transition-colors disabled:opacity-50"
          >
            {deletionRequested ? '✓ Deletion requested — check your email' : 'Request data deletion'}
          </button>
          {deletionError && (
            <p className="mt-2 text-xs text-rose-600">Failed to submit deletion request. Please try again.</p>
          )}
        </div>
      </div>
    </>
  )
}
