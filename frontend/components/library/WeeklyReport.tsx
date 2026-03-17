'use client'

import { TrendingUp, TrendingDown, Minus, BarChart2, AlertTriangle, Calendar } from 'lucide-react'
import { ExportMenu } from './ExportMenu'
import type { LibraryBrief } from '@/lib/hooks/useLibrary'

import { getStringColor } from '@/lib/domain-colors'

interface WeeklyReportProps {
  brief: LibraryBrief
}

// ── Domain severity data ──────────────────────────────────────────────────────
// Parsed from the weekly-report brief's section content

interface DomainDigest {
  domain: string
  trend: 'up' | 'down' | 'flat'
  headline: string
  color: string
}

function TrendIcon({ trend }: { trend: 'up' | 'down' | 'flat' }) {
  if (trend === 'up')   return <TrendingUp   className="h-4 w-4 text-emerald-500" />
  if (trend === 'down') return <TrendingDown className="h-4 w-4 text-rose-500" />
  return <Minus className="h-4 w-4 text-slate-400" />
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionBlock({ heading, content }: { heading: string; content: string }) {
  return (
    <div className="mb-8">
      <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-subtle">{heading}</h3>
      <p className="font-serif text-[14px] leading-[1.8] text-body">{content}</p>
    </div>
  )
}

function KeySignalRow({ text, index }: { text: string; index: number }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 px-4 py-3">
      <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-primary/10 text-[9px] font-bold text-primary">
        {index + 1}
      </span>
      <p className="font-serif text-xs leading-relaxed text-body">{text}</p>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function WeeklyReport({ brief }: WeeklyReportProps) {
  // Parse key signals from the "Key Signals" section if present
  const keySignalsSection = brief.sections.find(
    s => s.heading.toLowerCase().includes('key signal')
  )
  const keySignals = keySignalsSection
    ? keySignalsSection.content.split('.').filter(s => s.trim().length > 20).slice(0, 5)
    : []

  // Domain digests — derived from section headings (data-driven, not hardcoded domain list)
  const excludedHeadings = ['key signal', 'executive', 'outlook', 'summary', 'introduction']
  const domainSections = brief.sections.filter(s =>
    !excludedHeadings.some(h => s.heading.toLowerCase().includes(h))
  )
  const digests: DomainDigest[] = domainSections.map(s => {
    const domain = s.heading
    const content = s.content.toLowerCase()
    const trend: 'up' | 'down' | 'flat' =
      content.includes('growth') || content.includes('increase') || content.includes('positive') ? 'up' :
      content.includes('decline') || content.includes('delay') || content.includes('stress') ? 'down' : 'flat'
    const firstSentence = s.content.split('.')[0] + '.'
    return { domain, trend, headline: firstSentence, color: getStringColor(domain) }
  })

  const execSummary = brief.sections.find(s => s.heading.toLowerCase().includes('executive'))
  const outlookSection = brief.sections.find(s => s.heading.toLowerCase().includes('outlook'))
  const otherSections = brief.sections.filter(
    s => !s.heading.toLowerCase().includes('key signal') &&
         !s.heading.toLowerCase().includes('executive') &&
         !s.heading.toLowerCase().includes('outlook') &&
         !domainSections.includes(s)
  )

  return (
    <div className="mx-auto max-w-[820px] px-6 py-8">

      {/* ── Report masthead ──────────────────────────────────────────────── */}
      <div className="mb-8 border-b-2 border-heading pb-6">
        <div className="mb-2 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-subtle">
            <BarChart2 className="h-3.5 w-3.5" />
            Cogent Intelligence
          </div>
          <ExportMenu brief={brief} />
        </div>
        <h1 className="font-serif text-2xl font-normal text-heading">{brief.title}</h1>
        <p className="mt-1 font-serif text-sm text-subtle">{brief.subtitle}</p>
        <div className="mt-4 flex items-center gap-4 text-[11px] text-subtle">
          <span className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5" />
            {brief.relativeDate}
          </span>
          <span>·</span>
          <span>{brief.tags.join(' · ')}</span>
          <span>·</span>
          <span className="text-primary">{brief.confidence}% confidence</span>
        </div>
      </div>

      {/* ── Executive Summary ────────────────────────────────────────────── */}
      {execSummary && (
        <div className="mb-8 rounded-xl border-l-4 border-primary bg-primary/5 p-5">
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-primary">
            Executive Summary
          </p>
          <p className="font-serif text-sm leading-[1.8] text-body">{execSummary.content}</p>
        </div>
      )}

      {/* ── Key Signals ─────────────────────────────────────────────────── */}
      {keySignals.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-[11px] font-bold uppercase tracking-widest text-subtle">
            Key Signals This Week
          </h2>
          <div className="flex flex-col gap-2">
            {keySignals.map((signal, i) => (
              <KeySignalRow key={i} text={signal.trim()} index={i} />
            ))}
          </div>
        </div>
      )}

      {/* ── Domain deep dives ────────────────────────────────────────────── */}
      {digests.length > 0 && (
        <div className="mb-8">
          <h2 className="mb-4 text-[11px] font-bold uppercase tracking-widest text-subtle">
            Domain Digest
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {digests.map(d => (
              <div
                key={d.domain}
                className="flex items-start gap-3 rounded-xl border border-border bg-surface p-4"
              >
                <div
                  className="mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg"
                  style={{ background: d.color + '18' }}
                >
                  <TrendIcon trend={d.trend} />
                </div>
                <div>
                  <p className="text-[11px] font-semibold text-heading"
                     style={{ color: d.color }}>{d.domain}</p>
                  <p className="mt-0.5 font-serif text-xs leading-relaxed text-body line-clamp-2">{d.headline}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Additional sections ──────────────────────────────────────────── */}
      {otherSections.map(s => (
        <SectionBlock key={s.heading} heading={s.heading} content={s.content} />
      ))}

      {/* ── Outlook ─────────────────────────────────────────────────────── */}
      {outlookSection && (
        <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 p-5">
          <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-amber-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            Outlook & Watch Items
          </div>
          <p className="font-serif text-sm leading-[1.8] text-amber-900">{outlookSection.content}</p>
        </div>
      )}

      {/* Footer */}
      <div className="mt-10 flex items-center justify-between border-t border-border pt-6 text-[10px] text-subtle">
        <span>Cogent Research Platform · AI-assisted intelligence synthesis</span>
        <span>{brief.relativeDate} · {brief.confidence}% confidence</span>
      </div>
    </div>
  )
}
