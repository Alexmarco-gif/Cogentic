'use client'

import { useEffect, useState } from 'react'
import {
  AlertTriangle,
  Archive,
  Brain,
  ChevronRight,
  FolderOpen,
  History,
  Loader2,
  Trash2,
} from 'lucide-react'

import { listBriefs, updateBriefStatus } from '@/lib/api/briefs'
import {
  clearUserHistory,
  getConsentHistory,
  requestDataDeletion,
  requestDataExport,
  updateConsentDecision,
  type ConsentHistoryEntry,
  type ConsentType,
} from '@/lib/api/privacy'
import { friendlyErrorMessage } from '@/lib/api/errors'
import type { BriefResponse } from '@/lib/api/types'

function Toggle({
  enabled,
  onToggle,
  disabled,
}: {
  enabled: boolean
  onToggle: () => void
  disabled?: boolean
}) {
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
      <span
        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
          enabled ? 'translate-x-4' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

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
          <AlertTriangle
            className={`mt-0.5 h-5 w-5 flex-shrink-0 ${destructive ? 'text-rose-500' : 'text-amber-500'}`}
            strokeWidth={1.5}
          />
          <div>
            <p className="text-sm font-medium text-heading">{title}</p>
            <p className="mt-1 text-xs leading-relaxed text-subtle">{body}</p>
          </div>
        </div>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-border py-2 text-sm font-medium text-body transition-colors hover:bg-muted"
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

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

const CONSENT_LABELS: Record<ConsentType, { label: string; desc: string }> = {
  data_processing: {
    label: 'Allow core data processing',
    desc: 'Required for account activity, contract execution, alerts, and investigations.',
  },
  ai_training: {
    label: 'Allow model improvement',
    desc: 'Lets Cogent learn from anonymised workspace usage patterns to improve model quality.',
  },
  analytics: {
    label: 'Share usage analytics',
    desc: 'Sends product telemetry that helps us improve performance and reliability.',
  },
  marketing: {
    label: 'Receive product updates',
    desc: 'Receive release notes, product announcements, and optional lifecycle emails.',
  },
}

function deriveConsentValues(entries: ConsentHistoryEntry[]) {
  const values: Record<ConsentType, boolean> = {
    data_processing: false,
    ai_training: false,
    analytics: false,
    marketing: false,
  }

  for (const entry of entries) {
    if (entry.consent_type && typeof entry.granted === 'boolean') {
      values[entry.consent_type] = entry.granted
    }
  }

  return values
}

function downloadExportArchive(data: Record<string, unknown> | null) {
  if (!data || typeof window === 'undefined') return

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `cogent-data-export-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function DataPrivacySection() {
  const [consentValues, setConsentValues] = useState<Record<ConsentType, boolean>>({
    data_processing: false,
    ai_training: false,
    analytics: false,
    marketing: false,
  })
  const [consentHistory, setConsentHistory] = useState<ConsentHistoryEntry[]>([])
  const [consentPending, setConsentPending] = useState<ConsentType | null>(null)
  const [consentError, setConsentError] = useState<string | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  const [confirm, setConfirm] = useState<null | 'history' | 'account'>(null)
  const [historyCleared, setHistoryCleared] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [deletionRequested, setDeletionRequested] = useState(false)
  const [exportRequesting, setExportRequesting] = useState(false)
  const [exportRequested, setExportRequested] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exportMessage, setExportMessage] = useState<string | null>(null)
  const [historyError, setHistoryError] = useState<string | null>(null)
  const [historyMessage, setHistoryMessage] = useState<string | null>(null)
  const [deletionError, setDeletionError] = useState<string | null>(null)
  const [deletionMessage, setDeletionMessage] = useState<string | null>(null)
  const [archivedBriefs, setArchivedBriefs] = useState<BriefResponse[]>([])
  const [restoringId, setRestoringId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadPrivacyState() {
      const [briefsResult, consentResult] = await Promise.allSettled([
        listBriefs({ status: 'archived', limit: 50 }),
        getConsentHistory(),
      ])

      if (!cancelled && briefsResult.status === 'fulfilled') {
        setArchivedBriefs(briefsResult.value.items ?? [])
      }

      if (!cancelled && consentResult.status === 'fulfilled') {
        setConsentHistory(consentResult.value)
        setConsentValues(deriveConsentValues(consentResult.value))
      }
    }

    void loadPrivacyState()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleConsentToggle(consentType: ConsentType) {
    const nextValue = !consentValues[consentType]
    setConsentPending(consentType)
    setConsentError(null)

    try {
      await updateConsentDecision(consentType, nextValue)
      const history = await getConsentHistory()
      setConsentHistory(history)
      setConsentValues(deriveConsentValues(history))
    } catch (error) {
      setConsentError(friendlyErrorMessage(error))
    } finally {
      setConsentPending(null)
    }
  }

  async function handleConfirm() {
    setConfirming(true)
    setHistoryError(null)
    setHistoryMessage(null)
    setDeletionError(null)
    setDeletionMessage(null)

    try {
      if (confirm === 'history') {
        const response = await clearUserHistory()
        setHistoryCleared(true)
        setHistoryMessage(response.message)
      } else if (confirm === 'account') {
        const response = await requestDataDeletion()
        setDeletionRequested(true)
        setDeletionMessage(response.message)
      }
    } catch (error) {
      const message = friendlyErrorMessage(error)
      if (confirm === 'history') {
        setHistoryError(message)
      } else {
        setDeletionError(message)
      }
    } finally {
      setConfirming(false)
      setConfirm(null)
    }
  }

  async function handleRequestExport() {
    setExportRequesting(true)
    setExportError(null)
    setExportMessage(null)

    try {
      const response = await requestDataExport()
      downloadExportArchive(response.data)
      setExportRequested(true)
      setExportMessage(response.message)
    } catch (error) {
      setExportError(friendlyErrorMessage(error))
    } finally {
      setExportRequesting(false)
    }
  }

  async function handleRestore(brief: BriefResponse) {
    setRestoringId(brief.id)
    try {
      await updateBriefStatus(brief.id, { status: 'published' })
      setArchivedBriefs((previous) => previous.filter((item) => item.id !== brief.id))
    } finally {
      setRestoringId(null)
    }
  }

  return (
    <>
      {confirm && (
        <ConfirmDialog
          title={confirm === 'history' ? 'Clear all history?' : 'Delete account data now?'}
          body={
            confirm === 'history'
              ? 'This permanently deletes investigation sessions and their associated chat messages. This cannot be undone.'
              : 'This permanently deletes your user record, chat sessions, search queries, feedback events, and device sessions, and anonymises your audit trail.'
          }
          confirmLabel={
            confirming
              ? confirm === 'history'
                ? 'Clearing...'
                : 'Deleting...'
              : confirm === 'history'
                ? 'Clear history'
                : 'Delete data now'
          }
          destructive
          onConfirm={handleConfirm}
          onCancel={() => {
            if (!confirming) setConfirm(null)
          }}
        />
      )}

      <div className="flex flex-col gap-8">
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
          <div className="mb-1 flex items-center gap-2">
            <Brain className="h-4 w-4 text-primary" strokeWidth={1.5} />
            <h3 className="text-sm font-medium text-heading">Privacy Controls</h3>
          </div>
          <p className="mb-5 text-xs text-subtle">
            These toggles are backed by the live consent ledger and update your current workspace preferences.
          </p>

          <div className="flex flex-col divide-y divide-border">
            {(Object.entries(CONSENT_LABELS) as Array<[ConsentType, { label: string; desc: string }]>).map(
              ([consentType, copy]) => (
                <div key={consentType} className="flex items-center justify-between gap-4 py-4">
                  <div>
                    <p className="text-sm font-medium text-body">{copy.label}</p>
                    <p className="mt-0.5 text-xs text-subtle">{copy.desc}</p>
                  </div>
                  <Toggle
                    enabled={consentValues[consentType]}
                    disabled={consentPending === consentType}
                    onToggle={() => {
                      void handleConsentToggle(consentType)
                    }}
                  />
                </div>
              ),
            )}
          </div>

          {consentError && <p className="mt-4 text-xs text-rose-500">{consentError}</p>}

          {consentHistory.length > 0 && (
            <div className="mt-5 rounded-xl border border-border bg-muted/30 p-4">
              <p className="text-[11px] font-medium uppercase tracking-wide text-subtle">Recent consent changes</p>
              <div className="mt-3 flex flex-col gap-2">
                {consentHistory
                  .filter(
                    (
                      entry,
                    ): entry is ConsentHistoryEntry & {
                      consent_type: ConsentType
                      recorded_at: string
                    } => Boolean(entry.consent_type && entry.recorded_at),
                  )
                  .slice(-4)
                  .reverse()
                  .map((entry, index) => (
                    <div
                      key={`${entry.consent_type}-${entry.recorded_at}-${index}`}
                      className="flex items-center justify-between gap-3 text-xs"
                    >
                      <span className="text-body">{CONSENT_LABELS[entry.consent_type].label}</span>
                      <span className={entry.granted ? 'text-emerald-600' : 'text-rose-500'}>
                        {entry.granted ? 'Allowed' : 'Declined'} on {formatDate(entry.recorded_at)}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
          <div className="mb-1 flex items-center gap-2">
            <History className="h-4 w-4 text-subtle" strokeWidth={1.5} />
            <h3 className="text-sm font-medium text-heading">History & Archive</h3>
          </div>
          <p className="mb-5 text-xs text-subtle">Manage investigation history, portable user-data exports, and archived briefs.</p>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
                <div className="flex items-center gap-3">
                  <Trash2 className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                  <div>
                    <p className="text-sm font-medium text-body">
                      Clear all history
                      {historyCleared && <span className="ml-2 text-[10px] font-normal text-emerald-600">Cleared</span>}
                    </p>
                    <p className="text-xs text-subtle">Deletes investigation sessions and their associated chat history.</p>
                  </div>
                </div>
                <button
                  onClick={() => setConfirm('history')}
                  disabled={historyCleared}
                  className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-1.5 text-[11px] font-medium text-rose-600 transition-colors hover:bg-rose-100 disabled:opacity-40"
                >
                  Clear
                </button>
              </div>
              {historyError && <p className="px-1 text-[10px] text-rose-500">{historyError}</p>}
              {historyMessage && <p className="px-1 text-[10px] text-emerald-600">{historyMessage}</p>}
            </div>

            <div className="flex items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3">
              <div className="flex items-center gap-3">
                <Archive className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-body">Download my data</p>
                  <p className="text-xs text-subtle">Download a JSON export of your profile, chat sessions, search queries, feedback, and device sessions.</p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <button
                  onClick={() => {
                    void handleRequestExport()
                  }}
                  disabled={exportRequesting}
                  className="flex items-center gap-1.5 rounded-xl border border-border bg-surface px-3 py-1.5 text-[11px] font-medium text-body transition-colors hover:bg-muted disabled:opacity-50"
                >
                  {exportRequesting && <Loader2 className="h-3 w-3 animate-spin" />}
                  {exportRequested ? 'Downloaded' : exportRequesting ? 'Preparing...' : 'Download export'}
                </button>
                {exportMessage && <p className="text-[10px] text-emerald-600">{exportMessage}</p>}
                {exportError && <p className="text-[10px] text-rose-500">{exportError}</p>}
              </div>
            </div>

            <button
              onClick={() => setShowArchived((value) => !value)}
              className="flex w-full items-center justify-between rounded-xl border border-border bg-muted/40 px-4 py-3 text-left transition-colors hover:bg-muted/70"
            >
              <div className="flex items-center gap-3">
                <FolderOpen className="h-4 w-4 text-subtle" strokeWidth={1.5} />
                <div>
                  <p className="text-sm font-medium text-body">View archived briefs</p>
                  <p className="text-xs text-subtle">
                    {archivedBriefs.length} archived item{archivedBriefs.length !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>
              <ChevronRight
                className={`h-4 w-4 text-subtle transition-transform ${showArchived ? 'rotate-90' : ''}`}
                strokeWidth={1.5}
              />
            </button>

            {showArchived && (
              <div className="ml-4 flex flex-col gap-1.5">
                {archivedBriefs.length === 0 && (
                  <p className="px-4 py-3 text-xs text-subtle">No archived items.</p>
                )}
                {archivedBriefs.map((brief) => (
                  <div
                    key={brief.id}
                    className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-2.5"
                  >
                    <div>
                      <p className="text-xs font-medium text-body">{brief.title}</p>
                      <p className="text-[10px] text-subtle">
                        {brief.brief_type} · Archived {formatDate(brief.updated_at)}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        void handleRestore(brief)
                      }}
                      disabled={restoringId === brief.id}
                      className="flex items-center gap-1 text-xs font-medium text-primary hover:underline disabled:opacity-50"
                    >
                      {restoringId === brief.id && <Loader2 className="h-3 w-3 animate-spin" />}
                      {restoringId === brief.id ? 'Restoring...' : 'Restore'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-rose-100 bg-rose-50/50 p-6">
          <h3 className="mb-1 text-sm font-medium text-rose-700">Delete account data</h3>
          <p className="mb-4 text-xs text-rose-600">
            Delete your user-owned data immediately. This removes your chat sessions, search queries, feedback events, device sessions, and anonymises audit logs.
          </p>
          <button
            onClick={() => {
              if (!deletionRequested) setConfirm('account')
            }}
            disabled={deletionRequested}
            className="rounded-xl border border-rose-300 bg-white px-4 py-2 text-sm font-medium text-rose-600 transition-colors hover:bg-rose-50 disabled:opacity-50"
          >
            {deletionRequested ? 'Deletion completed' : 'Delete data now'}
          </button>
          {deletionMessage && <p className="mt-2 text-xs text-emerald-700">{deletionMessage}</p>}
          {deletionError && <p className="mt-2 text-xs text-rose-600">{deletionError}</p>}
        </div>
      </div>
    </>
  )
}
