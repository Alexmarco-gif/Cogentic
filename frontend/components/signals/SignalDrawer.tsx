'use client'

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  X, ExternalLink, Bookmark, Share2, Link2, Download,
  FileText, HelpCircle, MapPin, Radio, BarChart2,
  TrendingUp, Compass, Zap, Target, Lightbulb, AlertCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge, ScrollArea } from '@/components/ui'
import { exportBrief } from '@/lib/api/exports'
import type {
  Signal,
  BriefConfidenceLevel,
  BriefPriorityLevel,
  SituationStatus,
  BriefTimeframe,
} from '@/lib/hooks/useSignals'

interface SignalDrawerProps {
  signal: Signal | null
  onClose: () => void
  onSave: (id: string) => void
}

import { getDomainBadge } from '@/lib/domain-colors'

// ── Confidence level styles ───────────────────────────────────────────────────
const CONFIDENCE_STYLES: Record<BriefConfidenceLevel, string> = {
  Low:      'bg-red-50 text-red-700 border-red-200',
  Medium:   'bg-amber-50 text-amber-700 border-amber-200',
  High:     'bg-emerald-50 text-emerald-700 border-emerald-200',
  Verified: 'bg-primary/10 text-primary border-primary/20',
}

// ── Priority level styles ─────────────────────────────────────────────────────
const PRIORITY_STYLES: Record<BriefPriorityLevel, string> = {
  Low:      'bg-slate-50 text-slate-600 border-slate-200',
  Medium:   'bg-amber-50 text-amber-700 border-amber-200',
  High:     'bg-orange-50 text-orange-700 border-orange-200',
  Critical: 'bg-red-50 text-red-700 border-red-200',
}

// ── Situation status styles ───────────────────────────────────────────────────
const SITUATION_STYLES: Record<SituationStatus, string> = {
  Emerging:    'bg-amber-50 text-amber-700 border-amber-200',
  Stable:      'bg-slate-100 text-slate-600 border-slate-200',
  Escalating:  'bg-orange-50 text-orange-700 border-orange-200',
  Improving:   'bg-emerald-50 text-emerald-700 border-emerald-200',
  Declining:   'bg-blue-50 text-blue-700 border-blue-200',
}

// ── Timeframe styles ──────────────────────────────────────────────────────────
const TIMEFRAME_STYLES: Record<BriefTimeframe, string> = {
  Immediate:    'bg-red-50 text-red-700',
  'Short-term': 'bg-amber-50 text-amber-700',
  'Long-term':  'bg-blue-50 text-blue-700',
}

// ── Evidence bar color ────────────────────────────────────────────────────────
function evidenceBarColor(conf: number) {
  if (conf >= 0.85) return 'bg-emerald-500'
  if (conf >= 0.70) return 'bg-amber-500'
  return 'bg-red-400'
}

// ── Null-safe display ─────────────────────────────────────────────────────────
function NullValue() {
  return <span className="text-subtle">—</span>
}

export function SignalDrawer({ signal, onClose, onSave }: SignalDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null)
  const shareRef  = useRef<HTMLDivElement>(null)
  const [shareOpen,    setShareOpen]    = useState(false)
  const [mounted,      setMounted]      = useState(false)
  const [exportingFmt, setExportingFmt] = useState<string | null>(null)

  // Portal mount guard — avoids SSR document.body access
  useEffect(() => { setMounted(true) }, [])

  // Close share menu on outside click
  useEffect(() => {
    if (!shareOpen) return
    function handler(e: MouseEvent) {
      if (shareRef.current && !shareRef.current.contains(e.target as Node)) setShareOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [shareOpen])

  function copyLink() {
    if (!signal) return
    navigator.clipboard.writeText(`${window.location.origin}/dashboard/signals?open=${signal.id}`).catch(() => {})
    setShareOpen(false)
  }

  function shareToTwitter() {
    if (!signal) return
    const title = encodeURIComponent(`${signal.headline} — ${signal.entityName}`)
    const url   = encodeURIComponent(`${window.location.origin}/dashboard/signals?open=${signal.id}`)
    window.open(`https://twitter.com/intent/tweet?text=${title}&url=${url}`, '_blank')
    setShareOpen(false)
  }

  function shareToLinkedIn() {
    if (!signal) return
    const url   = encodeURIComponent(`${window.location.origin}/dashboard/signals?open=${signal.id}`)
    const title = encodeURIComponent(signal.headline)
    window.open(`https://www.linkedin.com/shareArticle?mini=true&url=${url}&title=${title}`, '_blank')
    setShareOpen(false)
  }

  function downloadMarkdown() {
    if (!signal) return
    const b = signal.brief
    const md = [
      `# ${signal.headline}`,
      '',
      `**Entity**: ${signal.entityName} · **Domain**: ${signal.domain} · **Severity**: ${signal.severity.toUpperCase()} · **Confidence**: ${signal.confidence}%`,
      '',
      '## Executive Summary',
      ...(b.executive_summary?.insights?.map((i: string) => `- ${i}`) ?? []),
      '',
      '## Situation Overview',
      b.situation_overview?.overview ?? '',
      '',
      '## Key Intelligence Questions',
      b.key_intelligence_questions?.what_is_happening      ? `**What is happening:** ${b.key_intelligence_questions.what_is_happening}`      : '',
      b.key_intelligence_questions?.why_is_it_happening    ? `**Why it is happening:** ${b.key_intelligence_questions.why_is_it_happening}`    : '',
      b.key_intelligence_questions?.what_will_happen_next  ? `**What happens next:** ${b.key_intelligence_questions.what_will_happen_next}`    : '',
      b.key_intelligence_questions?.impact_on_organization ? `**Impact on organisation:** ${b.key_intelligence_questions.impact_on_organization}` : '',
      '',
      '---',
      `*Cogent Intelligence Signal Brief · ${new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}*`,
    ].filter(Boolean).join('\n')
    const blob = new Blob([md], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${signal.entityName.replace(/[\s/]+/g, '-').toLowerCase()}-brief.md`
    a.click()
    URL.revokeObjectURL(a.href)
    setShareOpen(false)
  }

  function buildExportSections(sig: Signal) {
    const b = sig.brief
    const sections: { heading: string; content: string }[] = []
    const execInsights = b.executive_summary?.insights ?? []
    if (execInsights.length) {
      sections.push({ heading: 'Executive Summary', content: execInsights.join('\n') })
    }
    if (b.situation_overview?.overview) {
      sections.push({ heading: 'Situation Overview', content: b.situation_overview.overview })
    }
    const kiq = b.key_intelligence_questions
    if (kiq) {
      const kiqLines = [
        kiq.what_is_happening      ? `What is happening: ${kiq.what_is_happening}`      : null,
        kiq.why_is_it_happening    ? `Why it is happening: ${kiq.why_is_it_happening}`    : null,
        kiq.what_will_happen_next  ? `What happens next: ${kiq.what_will_happen_next}`   : null,
        kiq.impact_on_organization ? `Impact: ${kiq.impact_on_organization}`             : null,
      ].filter(Boolean) as string[]
      if (kiqLines.length) {
        sections.push({ heading: 'Key Intelligence Questions', content: kiqLines.join('\n\n') })
      }
    }
    if (b.recommended_actions?.immediate?.length || b.recommended_actions?.strategic?.length) {
      const actions = [
        ...(b.recommended_actions.immediate ?? []),
        ...(b.recommended_actions.strategic ?? []),
      ]
      sections.push({ heading: 'Recommended Actions', content: actions.join('\n') })
    }
    return sections
  }

  async function handleExport(format: 'pdf-html' | 'pptx' | 'docx') {
    if (!signal || exportingFmt) return
    setExportingFmt(format)
    setShareOpen(false)
    try {
      await exportBrief({
        title: signal.headline,
        subtitle: signal.entityName,
        domain: signal.domain,
        author: 'Cogent Intelligence',
        confidence: signal.confidence,
        sections: buildExportSections(signal),
        format,
      })
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExportingFmt(null)
    }
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  useEffect(() => {
    if (signal) {
      document.body.style.overflow = 'hidden'
      drawerRef.current?.focus()
    } else {
      document.body.style.overflow = ''
    }
    return () => { document.body.style.overflow = '' }
  }, [signal])

  if (!mounted) return null

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={cn(
          'fixed inset-0 z-[200] bg-black/20 backdrop-blur-[2px] transition-opacity duration-200',
          signal ? 'opacity-100' : 'opacity-0 pointer-events-none',
        )}
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        tabIndex={-1}
        className={cn(
          'fixed top-0 right-0 h-full z-[201] w-[600px] max-w-[95vw]',
          'bg-surface border-l border-border shadow-2xl',
          'flex flex-col outline-none',
          'transition-transform duration-300 ease-out',
          signal ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {signal && (() => {
          const b = signal.brief
          return (
            <>
              {/* ── Header ─────────────────────────────────── */}
              <div className="flex items-start justify-between px-6 pt-5 pb-4 border-b border-border">
                <div className="flex-1 min-w-0 pr-4">
                  <div className="flex items-center gap-2 mb-2 flex-wrap">
                    <Badge variant={(getDomainBadge(signal.domain)) as any}>
                      {signal.domain}
                    </Badge>
                    {signal.severity === 'critical' && (
                      <Badge variant="critical">Critical</Badge>
                    )}
                    <span className="text-xs text-subtle ml-auto">{signal.relativeTime}</span>
                  </div>
                  <h2 className="text-[15px] font-medium text-heading leading-snug">
                    {signal.headline}
                  </h2>
                  <p className="text-xs text-subtle mt-1">{signal.entityName}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => onSave(signal.id)}
                    className={cn(
                      'p-2 rounded-lg transition-colors',
                      signal.isSaved
                        ? 'text-primary bg-primary/10'
                        : 'text-subtle hover:text-body hover:bg-muted',
                    )}
                    title="Save"
                  >
                    <Bookmark size={15} fill={signal.isSaved ? 'currentColor' : 'none'} />
                  </button>
                  {/* ── Share / Export dropdown ────────── */}
                  <div ref={shareRef} className="relative">
                    <button
                      onClick={() => setShareOpen(v => !v)}
                      className={cn(
                        'p-2 rounded-lg transition-colors',
                        shareOpen ? 'text-primary bg-primary/10' : 'text-subtle hover:text-body hover:bg-muted',
                      )}
                      title="Share / Export"
                    >
                      <Share2 size={15} />
                    </button>
                    {shareOpen && (
                      <div className="absolute right-0 top-full mt-1 z-10 w-52 rounded-xl bg-surface border border-border shadow-2xl overflow-hidden text-left">
                        <div className="px-3 pt-2.5 pb-1">
                          <p className="text-[9px] font-semibold uppercase tracking-widest text-subtle">Share</p>
                        </div>
                        <div className="px-1 pb-1">
                          <button onClick={copyLink} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors">
                            <Link2 size={13} className="shrink-0 text-subtle" /> Copy link
                          </button>
                          <button onClick={shareToTwitter} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors">
                            <ExternalLink size={13} className="shrink-0 text-subtle" /> Twitter / X
                          </button>
                          <button onClick={shareToLinkedIn} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors">
                            <ExternalLink size={13} className="shrink-0 text-subtle" /> LinkedIn
                          </button>
                        </div>
                        <div className="border-t border-border px-3 pt-2.5 pb-1">
                          <p className="text-[9px] font-semibold uppercase tracking-widest text-subtle">Export</p>
                        </div>
                        <div className="px-1 pb-2">
                          <button onClick={downloadMarkdown} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors">
                            <FileText size={13} className="shrink-0 text-subtle" /> Markdown (.md)
                          </button>
                          <button onClick={() => handleExport('pdf-html')} disabled={!!exportingFmt} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors disabled:opacity-50">
                            <Download size={13} className="shrink-0 text-subtle" />
                            {exportingFmt === 'pdf-html' ? 'Preparing…' : 'PDF'}
                          </button>
                          <button onClick={() => handleExport('pptx')} disabled={!!exportingFmt} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors disabled:opacity-50">
                            <Download size={13} className="shrink-0 text-subtle" />
                            {exportingFmt === 'pptx' ? 'Generating…' : 'PowerPoint (.pptx)'}
                          </button>
                          <button onClick={() => handleExport('docx')} disabled={!!exportingFmt} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body hover:bg-muted transition-colors disabled:opacity-50">
                            <Download size={13} className="shrink-0 text-subtle" />
                            {exportingFmt === 'docx' ? 'Generating…' : 'Word (.docx)'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                  <button onClick={onClose} className="p-2 rounded-lg text-subtle hover:text-body hover:bg-muted transition-colors" title="Close">
                    <X size={15} />
                  </button>
                </div>
              </div>

              {/* ── Section 0: Metadata bar (outside scroll) ── */}
              <div className="flex items-center gap-2 px-6 py-2 border-b border-border bg-muted/30 flex-wrap">
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full border bg-blue-50 text-blue-700 border-blue-200">
                  Category: {b.metadata.category}
                </span>
                <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', CONFIDENCE_STYLES[b.metadata.confidence_level])}>
                  Confidence: {b.metadata.confidence_level}
                </span>
                <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', PRIORITY_STYLES[b.metadata.priority_level])}>
                  Priority: {b.metadata.priority_level}
                </span>
              </div>

              {/* ── Scrollable body ────────────────────────── */}
              <ScrollArea className="flex-1 overflow-y-auto">
                <div className="px-6 py-5 space-y-6">

                  {/* ── Section 1: Executive Summary ─────────── */}
                  <section>
                    <SectionHeader label="Executive Summary" icon={FileText} />
                    <div className="bg-primary/5 border border-primary/10 rounded-xl px-4 py-4 space-y-3">
                      {/* Insights */}
                      <ul className="space-y-2">
                        {b.executive_summary.insights.map((ins, i) => (
                          <li key={i} className="flex gap-2 text-[13px] text-body leading-relaxed">
                            <span className="text-primary mt-1 shrink-0">•</span>
                            <span>{ins}</span>
                          </li>
                        ))}
                      </ul>
                      {/* Situation status */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[11px] text-subtle">Situation:</span>
                        <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', SITUATION_STYLES[b.executive_summary.situation_status as SituationStatus] ?? 'bg-muted text-subtle border-border')}>
                          {b.executive_summary.situation_status}
                        </span>
                      </div>
                      {/* Decision required */}
                      {b.executive_summary.decision_required && b.executive_summary.decision_description && (
                        <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-[12px] text-amber-800">
                          <strong>Decision required:</strong> {b.executive_summary.decision_description}
                        </div>
                      )}
                    </div>
                  </section>

                  {/* ── Section 2: Key Intelligence Questions ── */}
                  <section>
                    <SectionHeader label="Key Intelligence Questions" icon={HelpCircle} />
                    <div className="grid grid-cols-1 gap-3">
                      {(
                        [
                          { label: 'What is happening?',    field: b.key_intelligence_questions.what_is_happening },
                          { label: 'Why is it happening?',  field: b.key_intelligence_questions.why_is_it_happening },
                          { label: 'What will happen next?',field: b.key_intelligence_questions.what_will_happen_next },
                          { label: 'What is the impact?',   field: b.key_intelligence_questions.impact_on_organization },
                        ] as const
                      ).map(({ label, field }) => (
                        <div key={label} className="bg-muted/50 border border-border rounded-lg px-3 py-2.5">
                          <p className="text-[10px] font-bold uppercase tracking-wide text-subtle">{label}</p>
                          <p className="text-[13px] text-body leading-relaxed mt-1">
                            {field ?? <NullValue />}
                          </p>
                        </div>
                      ))}
                    </div>
                  </section>

                  {/* ── Section 3: Situation Overview ──────────── */}
                  <section>
                    <SectionHeader label="Situation Overview" icon={MapPin} />
                    <div className="space-y-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-subtle">Region / Market:</span>
                        <span className="text-[13px] text-body">{b.situation_overview.region_market ?? '—'}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-subtle">Timeframe:</span>
                        <span className={cn('text-[11px] font-medium px-2 py-0.5 rounded-full', TIMEFRAME_STYLES[b.situation_overview.timeframe])}>
                          {b.situation_overview.timeframe}
                        </span>
                      </div>
                    </div>
                    {b.situation_overview.overview && (
                      <p className="text-[13px] text-body leading-relaxed mt-2">{b.situation_overview.overview}</p>
                    )}
                  </section>

                  {/* ── Section 4: Signals & Indicators ─────────── */}
                  <section>
                    <SectionHeader label="Signals & Indicators" icon={Radio} />
                    <div className="space-y-4">
                      {/* A) Leading indicators */}
                      {b.signals_and_indicators.leading_indicators.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold text-subtle mb-1">Leading Indicators</p>
                          <ul className="space-y-1.5">
                            {b.signals_and_indicators.leading_indicators.map((item, i) => (
                              <li key={i} className="flex gap-2 text-[13px] text-body leading-relaxed">
                                <span className="text-emerald-600 shrink-0 mt-0.5">◆</span>
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {/* B) Triggers */}
                      {b.signals_and_indicators.triggers.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold text-subtle mb-1">Triggers</p>
                          <ul className="space-y-1.5">
                            {b.signals_and_indicators.triggers.map((item, i) => (
                              <li key={i} className="flex gap-2 text-[13px] text-body leading-relaxed">
                                <span className="text-amber-500 shrink-0 mt-0.5">⚡</span>
                                {item}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {/* C) Signal Evidence */}
                      {b.signals_and_indicators.signal_evidence.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold text-subtle mb-1.5">Signal Evidence</p>
                          <div className="space-y-2">
                            {b.signals_and_indicators.signal_evidence.map((ev, i) => (
                              <div key={i} className="bg-muted/40 border border-border rounded-lg px-3 py-2.5 space-y-1.5">
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] font-medium bg-muted border border-border text-subtle px-1.5 py-0.5 rounded shrink-0">
                                    {ev.signal_ref}
                                  </span>
                                  <span className="text-[12px] font-medium text-heading truncate">{ev.signal_title}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                  <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
                                    <div
                                      className={cn('h-full rounded-full', evidenceBarColor(ev.confidence))}
                                      style={{ width: `${ev.confidence * 100}%` }}
                                    />
                                  </div>
                                  <span className="text-[10px] text-subtle tabular-nums shrink-0">
                                    {Math.round(ev.confidence * 100)}%
                                  </span>
                                </div>
                                <p className="text-[12px] text-body leading-relaxed">{ev.contribution}</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </section>

                  {/* ── Section 5: Analysis ──────────────────────── */}
                  <section>
                    <SectionHeader label="Analysis" icon={BarChart2} />
                    <div className="space-y-4">
                      {/* A) Drivers */}
                      {(b.analysis.drivers.technology.length > 0 || b.analysis.drivers.market.length > 0 || b.analysis.drivers.regulatory.length > 0) && (
                        <div>
                          <p className="text-[11px] font-semibold text-subtle mb-2">Drivers</p>
                          <div className="space-y-2">
                            {b.analysis.drivers.technology.length > 0 && (
                              <div className="flex items-start gap-2 flex-wrap">
                                <span className="text-[10px] font-semibold text-subtle shrink-0 mt-1">Technology:</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {b.analysis.drivers.technology.map((item, i) => (
                                    <span key={i} className="text-[11px] bg-muted border border-border rounded-md px-2 py-0.5 text-body">{item}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {b.analysis.drivers.market.length > 0 && (
                              <div className="flex items-start gap-2 flex-wrap">
                                <span className="text-[10px] font-semibold text-subtle shrink-0 mt-1">Market:</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {b.analysis.drivers.market.map((item, i) => (
                                    <span key={i} className="text-[11px] bg-muted border border-border rounded-md px-2 py-0.5 text-body">{item}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                            {b.analysis.drivers.regulatory.length > 0 && (
                              <div className="flex items-start gap-2 flex-wrap">
                                <span className="text-[10px] font-semibold text-subtle shrink-0 mt-1">Regulatory:</span>
                                <div className="flex flex-wrap gap-1.5">
                                  {b.analysis.drivers.regulatory.map((item, i) => (
                                    <span key={i} className="text-[11px] bg-muted border border-border rounded-md px-2 py-0.5 text-body">{item}</span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      {/* B) Patterns */}
                      {b.analysis.patterns_detected.length > 0 && (
                        <div>
                          <p className="text-[11px] font-semibold text-subtle mb-1">Patterns Detected</p>
                          <ul className="space-y-1.5">
                            {b.analysis.patterns_detected.map((p, i) => (
                              <li key={i} className="flex gap-2 text-[13px] text-body leading-relaxed">
                                <span className="text-primary shrink-0 mt-0.5">→</span>
                                {p}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {/* C) Risk Assessment */}
                      <div>
                        <p className="text-[11px] font-semibold text-subtle mb-2">Risk Assessment</p>
                        <div className="grid grid-cols-2 gap-2">
                          {(
                            [
                              { label: 'Operational', value: b.analysis.risk_assessment.operational },
                              { label: 'Strategic',   value: b.analysis.risk_assessment.strategic },
                              { label: 'Technical',   value: b.analysis.risk_assessment.technical },
                              { label: 'Market',      value: b.analysis.risk_assessment.market },
                            ]
                          ).map(({ label, value }) => (
                            <div key={label} className="bg-red-50/50 border border-red-100 rounded-lg px-3 py-2">
                              <p className="text-[10px] font-semibold uppercase tracking-wide text-red-700 mb-1">{label}</p>
                              <p className="text-[12px] text-body leading-relaxed">{value ?? <NullValue />}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </section>

                  {/* ── Section 6: Impact Assessment ─────────────── */}
                  <section>
                    <SectionHeader label="Impact Assessment" icon={TrendingUp} />
                    <div className="space-y-3">
                      {/* Short-term */}
                      <div className="bg-orange-50/60 border border-orange-100 rounded-xl px-4 py-3 space-y-2">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[10px] font-bold uppercase bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full">Short-Term</span>
                        </div>
                        {(
                          [
                            { label: 'Operations',     value: b.impact_assessment.short_term.operations },
                            { label: 'Infrastructure', value: b.impact_assessment.short_term.infrastructure },
                            { label: 'Product Roadmap',value: b.impact_assessment.short_term.product_roadmap },
                          ]
                        ).map(({ label, value }) => (
                          <div key={label}>
                            <p className="text-[10px] font-semibold uppercase text-orange-700">{label}</p>
                            <p className="text-[13px] text-body leading-relaxed">{value ?? <NullValue />}</p>
                          </div>
                        ))}
                      </div>
                      {/* Long-term */}
                      <div className="bg-blue-50/60 border border-blue-100 rounded-xl px-4 py-3 space-y-2">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[10px] font-bold uppercase bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Long-Term</span>
                        </div>
                        {(
                          [
                            { label: 'Market Position',        value: b.impact_assessment.long_term.market_position },
                            { label: 'Innovation Strategy',    value: b.impact_assessment.long_term.innovation_strategy },
                            { label: 'Competitive Landscape',  value: b.impact_assessment.long_term.competitive_landscape },
                          ]
                        ).map(({ label, value }) => (
                          <div key={label}>
                            <p className="text-[10px] font-semibold uppercase text-blue-700">{label}</p>
                            <p className="text-[13px] text-body leading-relaxed">{value ?? <NullValue />}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </section>

                  {/* ── Section 7: Outlook 30–90 Days ─────────────── */}
                  {b.outlook && (
                    <section>
                      <SectionHeader label="Outlook — 30 to 90 Days" icon={Compass} />
                      <div className="bg-surface border border-border border-l-4 border-l-primary rounded-xl px-4 py-3">
                        <p className="text-[13px] text-body leading-relaxed">{b.outlook}</p>
                      </div>
                    </section>
                  )}

                  {/* ── Section 8: Recommended Actions ────────────── */}
                  <section>
                    <SectionHeader label="Recommended Actions" icon={Zap} />
                    <div className="space-y-4">
                      {/* Immediate */}
                      {b.recommended_actions.immediate.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2">
                            <span className="text-[10px] font-bold uppercase bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Immediate</span>
                          </div>
                          <ol className="space-y-2">
                            {b.recommended_actions.immediate.map((action, i) => (
                              <li key={i} className="flex gap-2.5 items-start">
                                <span className="w-4 h-4 rounded-full bg-red-100 text-red-700 text-[10px] flex items-center justify-center shrink-0 mt-0.5 font-semibold">
                                  {i + 1}
                                </span>
                                <span className="text-[13px] text-body leading-snug">{action}</span>
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}
                      {/* Strategic */}
                      {b.recommended_actions.strategic.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1.5 mb-2">
                            <span className="text-[10px] font-bold uppercase bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Strategic</span>
                          </div>
                          <ol className="space-y-2">
                            {b.recommended_actions.strategic.map((action, i) => (
                              <li key={i} className="flex gap-2.5 items-start">
                                <span className="w-4 h-4 rounded-full bg-blue-100 text-blue-700 text-[10px] flex items-center justify-center shrink-0 mt-0.5 font-semibold">
                                  {i + 1}
                                </span>
                                <span className="text-[13px] text-body leading-snug">{action}</span>
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}
                    </div>
                  </section>

                  {/* ── Section 9: Sources ────────────────────────── */}
                  <section>
                    <SectionHeader label="Sources" count={signal.sources.length} icon={ExternalLink as LucideIcon} />
                    <div className="flex flex-col gap-1.5">
                      {signal.sources.map(src => (
                        <a
                          key={src.id}
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center justify-between px-3 py-2 rounded-lg
                                     border border-border bg-muted/50 hover:bg-muted group transition-colors"
                          onClick={e => e.stopPropagation()}
                        >
                          <div>
                            <p className="text-[12px] font-medium text-heading">{src.name}</p>
                            <p className="text-[11px] text-subtle">
                              {new Date(src.publishedAt).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                          <ExternalLink size={12} className="text-subtle group-hover:text-primary transition-colors" />
                        </a>
                      ))}
                    </div>
                  </section>

                  {/* ── Section 10: Decision Lens + Limitations ──── */}
                  <section className="space-y-3">
                    {/* Decision Lens */}
                    {b.decision_lens && (
                      <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 flex gap-3">
                        <Lightbulb size={14} className="text-amber-600 shrink-0 mt-0.5" />
                        <p className="text-[13px] text-body leading-relaxed">{b.decision_lens}</p>
                      </div>
                    )}
                    {/* Limitations */}
                    {b.limitations.length > 0 && (
                      <div>
                        <p className="text-[11px] font-semibold text-subtle mb-1.5">Data Limitations</p>
                        <ul className="space-y-1">
                          {b.limitations.map((lim, i) => (
                            <li key={i} className="flex gap-1.5 items-start text-[11px] text-subtle italic">
                              <AlertCircle size={12} className="text-amber-500 shrink-0 mt-0.5" />
                              {lim}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {/* Confidence footnote */}
                    <div className="border-t border-border pt-3">
                      <p className="text-[11px] text-subtle">
                        Confidence score:{' '}
                        <span className="font-medium text-body">{signal.confidence}%</span>
                        {' '}— based on source corroboration, recency, and entity reliability model.
                      </p>
                    </div>
                  </section>

                </div>
              </ScrollArea>
            </>
          )
        })()}
      </div>
    </>,
    document.body,
  )
}

// ── Section header helper ────────────────────────────────────────────────────
function SectionHeader({ label, count, icon: Icon }: {
  label: string
  count?: number
  icon?: LucideIcon
}) {
  return (
    <div className="flex items-center gap-2 mb-2">
      {Icon && <Icon size={13} className="text-subtle shrink-0" />}
      <h3 className="text-[11px] font-semibold tracking-widest uppercase text-subtle">{label}</h3>
      {count != null && (
        <span className="text-[10px] bg-muted text-subtle px-1.5 py-0.5 rounded-pill">
          {count}
        </span>
      )}
    </div>
  )
}
