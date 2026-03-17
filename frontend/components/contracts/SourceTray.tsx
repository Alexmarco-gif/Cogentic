'use client'

import { ChevronUp, ChevronDown, BookOpen, Loader2 } from 'lucide-react'
import type { SourceDocument } from '@/lib/hooks/useContractStudio'

// ── Status badge ──────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<SourceDocument['status'], string> = {
  reading: 'text-amber-600 bg-amber-50 border-amber-200',
  indexed: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  cited:   'text-primary bg-primary/5 border-primary/20',
}

const STATUS_LABEL: Record<SourceDocument['status'], string> = {
  reading: 'Reading…',
  indexed: 'Indexed',
  cited:   'Cited',
}

// ── Source card ───────────────────────────────────────────────────────────────

function SourceCard({ doc }: { doc: SourceDocument }) {
  return (
    <div className="flex w-full flex-shrink-0 flex-col gap-2 rounded-xl border border-border bg-surface p-3 shadow-sm sm:w-64">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-2">
          <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded bg-primary/8">
            <BookOpen className="h-3 w-3 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-[11px] font-medium text-heading">{doc.title}</p>
            <p className="text-[9px] text-subtle">{doc.source}</p>
          </div>
        </div>
        <span className={`flex-shrink-0 rounded-pill border px-1.5 py-0.5 text-[9px] font-medium ${STATUS_STYLES[doc.status]}`}>
          {doc.status === 'reading' ? (
            <span className="flex items-center gap-0.5">
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
              {STATUS_LABEL[doc.status]}
            </span>
          ) : STATUS_LABEL[doc.status]}
        </span>
      </div>

      {/* Snippet */}
      <p className="line-clamp-2 text-[10px] leading-relaxed text-subtle">"{doc.snippet}"</p>

      {/* Relevance bar */}
      <div className="flex items-center gap-2">
        <div className="h-1 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary/60 transition-all duration-700"
            style={{ width: `${doc.relevance}%` }}
          />
        </div>
        <span className="text-[9px] font-medium text-subtle">{doc.relevance}% rel</span>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

interface SourceTrayProps {
  docs: SourceDocument[]
  isOpen: boolean
  onToggle: () => void
  isProcessing?: boolean
}

export function SourceTray({ docs, isOpen, onToggle, isProcessing }: SourceTrayProps) {
  const readingCount = docs.filter(d => d.status === 'reading').length
  const citedCount   = docs.filter(d => d.status === 'cited').length

  return (
    <div className="flex-shrink-0 border-t border-border bg-canvas/60">
      {/* ── Toggle header ────────────────────────────────────────────────── */}
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-5 py-2.5 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <BookOpen className="h-3.5 w-3.5 text-subtle" />
          <span className="text-[11px] font-medium text-heading">Source Documents</span>
          {docs.length > 0 && (
            <div className="flex items-center gap-1.5">
              <span className="rounded-pill bg-muted px-2 py-0.5 text-[9px] font-medium text-data">
                {docs.length} sources
              </span>
              {readingCount > 0 && (
                <span className="flex items-center gap-1 rounded-pill border border-amber-200 bg-amber-50 px-2 py-0.5 text-[9px] font-medium text-amber-700">
                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                  {readingCount} reading
                </span>
              )}
              {citedCount > 0 && (
                <span className="rounded-pill border border-primary/20 bg-primary/5 px-2 py-0.5 text-[9px] font-medium text-primary">
                  {citedCount} cited
                </span>
              )}
            </div>
          )}
          {docs.length === 0 && (
            <span className="text-[10px] text-subtle">
              {isProcessing ? 'Searching data sources…' : 'Sources appear after validation runs'}
            </span>
          )}
        </div>
        <span className="text-subtle">
          {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
        </span>
      </button>

      {/* ── Tray content ─────────────────────────────────────────────────── */}
      {isOpen && docs.length > 0 && (
        <div className="overflow-x-auto px-5 pb-4">
          <div className="flex gap-3">
            {docs.map(doc => (
              <SourceCard key={doc.id} doc={doc} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
