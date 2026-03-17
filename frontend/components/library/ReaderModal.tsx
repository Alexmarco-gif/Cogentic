'use client'

import { useEffect, useCallback } from 'react'
import { X, ArrowLeft, Clock, Calendar, User, Shield } from 'lucide-react'
import { AbstractPattern } from './AbstractPattern'
import { ExportMenu } from './ExportMenu'
import type { LibraryBrief } from '@/lib/hooks/useLibrary'

interface ReaderModalProps {
  brief: LibraryBrief | null
  onClose: () => void
}

// ── Confidence badge ──────────────────────────────────────────────────────────

function ConfidenceBadge({ score }: { score: number }) {
  const label = score >= 85 ? 'High' : score >= 70 ? 'Medium' : 'Low'
  const color =
    score >= 85 ? 'text-emerald-700 bg-emerald-50 border-emerald-200' :
    score >= 70 ? 'text-amber-700 bg-amber-50 border-amber-200' :
                  'text-slate-600 bg-slate-50 border-slate-200'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-xs font-medium ${color}`}>
      <Shield className="h-3 w-3" />
      {label} Confidence · {score}%
    </span>
  )
}

// ── Reader section ────────────────────────────────────────────────────────────

function ReaderSection({ heading, content, index }: { heading: string; content: string; index: number }) {
  // Split content on newlines; lines starting with • or ✓ or ✗ become styled items
  const lines = content.split('\n').filter(l => l.trim() !== '')
  return (
    <section className="mb-10">
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
          {index + 1}
        </span>
        <h2 className="font-serif text-lg font-normal text-heading">{heading}</h2>
      </div>
      <div className="space-y-2">
        {lines.map((line, i) => {
          const isBullet = /^[\s]*[•✓✗]/.test(line)
          const isLabel = /^(Evidence:|Counter-argument:|Why it holds:|Confirms if:|Watch out if:)/i.test(line.trim())
          if (isLabel) {
            return (
              <p key={i} className="font-serif text-[13px] font-semibold uppercase tracking-wide text-subtle mt-3">
                {line.trim()}
              </p>
            )
          }
          if (isBullet) {
            return (
              <p key={i} className="font-serif text-[14px] leading-relaxed text-body pl-4">
                {line.trim()}
              </p>
            )
          }
          return (
            <p key={i} className="font-serif text-[15px] leading-[1.85] text-body">
              {line.trim()}
            </p>
          )
        })}
      </div>
    </section>
  )
}

// ── Modal ─────────────────────────────────────────────────────────────────────

export function ReaderModal({ brief, onClose }: ReaderModalProps) {
  const isOpen = brief !== null

  // Keyboard close + body lock
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() },
    [onClose]
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, handleKeyDown])

  if (!brief) return null

  return (
    <>
      {/* ── Backdrop ───────────────────────────────────────────────────────── */}
      <div
        className="fixed inset-0 z-40 bg-black/25 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* ── Modal panel — slides up from bottom ────────────────────────────── */}
      <div
        className="fixed inset-x-0 bottom-0 top-0 z-50 flex items-stretch justify-center overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-label={brief.title}
      >
        {/* Side click zones to close */}
        <div className="hidden flex-1 cursor-pointer lg:block" onClick={onClose} />

        {/* Reader panel */}
        <div className="flex w-full max-w-[780px] flex-col overflow-hidden bg-surface shadow-[0_0_80px_rgba(0,0,0,0.2)]">

          {/* ── Top bar ──────────────────────────────────────────────────────── */}
          <div className="flex flex-shrink-0 items-center justify-between border-b border-border bg-surface/90 px-6 py-3 backdrop-blur-sm">
            <button
              onClick={onClose}
              className="flex items-center gap-2 text-xs text-subtle transition-colors hover:text-heading"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Library
            </button>
            <div className="flex items-center gap-2">
              <ExportMenu brief={brief} />
              <button
                onClick={onClose}
                className="flex h-7 w-7 items-center justify-center rounded-lg text-subtle transition-colors hover:bg-muted hover:text-heading"
                aria-label="Close reader"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* ── Scrollable reader body ────────────────────────────────────── */}
          <div className="flex-1 overflow-y-auto">

            {/* Pattern header */}
            <div className="h-52 w-full overflow-hidden">
              <AbstractPattern
                id={brief.id}
                domain={brief.domain}
                type={brief.type}
                width={780}
                height={208}
              />
            </div>

            {/* Content area */}
            <div className="mx-auto max-w-reader px-6 py-10">

              {/* Domain + type breadcrumb */}
              <p className="mb-3 text-xs font-medium uppercase tracking-widest text-subtle">
                {brief.domain} · {brief.type.replace('-', ' ')}
              </p>

              {/* Title */}
              <h1 className="mb-2 font-serif text-[1.65rem] font-normal leading-tight text-heading">
                {brief.title}
              </h1>
              {brief.subtitle && (
                <p className="mb-6 font-serif text-base font-light text-data">{brief.subtitle}</p>
              )}

              {/* Metadata row */}
              <div className="mb-8 flex flex-wrap items-center gap-3">
                <ConfidenceBadge score={brief.confidence} />
                <span className="flex items-center gap-1 text-xs text-subtle">
                  <Calendar className="h-3.5 w-3.5" />
                  {brief.relativeDate}
                </span>
                <span className="flex items-center gap-1 text-xs text-subtle">
                  <Clock className="h-3.5 w-3.5" />
                  {brief.readTimeMinutes} min read
                </span>
                <span className="flex items-center gap-1 text-xs text-subtle">
                  <User className="h-3.5 w-3.5" />
                  {brief.author}
                </span>
              </div>

              {/* Tags */}
              <div className="mb-10 flex flex-wrap gap-1.5">
                {brief.tags.map(tag => (
                  <span
                    key={tag}
                    className="rounded-pill bg-muted px-2.5 py-1 text-xs text-data"
                  >
                    {tag}
                  </span>
                ))}
              </div>

              {/* Summary / abstract box */}
              <div className="mb-10 rounded-xl border border-primary/10 bg-primary/5 px-5 py-4">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-widest text-primary">
                  Abstract
                </p>
                <p className="font-serif text-sm leading-relaxed text-body">
                  {brief.summary}
                </p>
              </div>

              {/* Divider */}
              <div className="mb-10 flex items-center gap-4">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[10px] uppercase tracking-widest text-subtle">Analysis</span>
                <div className="h-px flex-1 bg-border" />
              </div>

              {/* Sections */}
              {brief.sections.map((section, i) => (
                <ReaderSection
                  key={section.heading}
                  heading={section.heading}
                  content={section.content}
                  index={i}
                />
              ))}

              {/* End marker */}
              <div className="mt-10 flex items-center justify-center gap-4 border-t border-border pt-10">
                <div className="h-1 w-1 rounded-full bg-border" />
                <p className="text-[11px] text-subtle">End of brief · {brief.author}</p>
                <div className="h-1 w-1 rounded-full bg-border" />
              </div>

              {/* Bottom padding */}
              <div className="h-16" />
            </div>
          </div>
        </div>

        <div className="hidden flex-1 cursor-pointer lg:block" onClick={onClose} />
      </div>
    </>
  )
}
