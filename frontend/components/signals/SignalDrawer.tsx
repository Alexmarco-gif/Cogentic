'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  AlertCircle,
  BarChart2,
  Bookmark,
  Compass,
  Download,
  ExternalLink,
  FileText,
  Lightbulb,
  Link2,
  Radio,
  Share2,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Badge, ScrollArea } from '@/components/ui'
import { exportBrief } from '@/lib/api/exports'
import { cn } from '@/lib/utils'
import type {
  BriefClaim,
  BriefConfidenceLevel,
  BriefPriorityLevel,
  BriefTimeframe,
  Signal,
  SituationStatus,
} from '@/lib/hooks/useSignals'
import { getDomainBadge } from '@/lib/domain-colors'

interface SignalDrawerProps {
  signal: Signal | null
  onClose: () => void
  onSave: (id: string) => void
}

type BriefViewMode = 'executive' | 'analyst'

const CONFIDENCE_STYLES: Record<BriefConfidenceLevel, string> = {
  Low: 'bg-red-50 text-red-700 border-red-200',
  Medium: 'bg-amber-50 text-amber-700 border-amber-200',
  High: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Verified: 'bg-primary/10 text-primary border-primary/20',
}

const PRIORITY_STYLES: Record<BriefPriorityLevel, string> = {
  Low: 'bg-slate-50 text-slate-600 border-slate-200',
  Medium: 'bg-amber-50 text-amber-700 border-amber-200',
  High: 'bg-orange-50 text-orange-700 border-orange-200',
  Critical: 'bg-red-50 text-red-700 border-red-200',
}

const SITUATION_STYLES: Record<SituationStatus, string> = {
  Emerging: 'bg-amber-50 text-amber-700 border-amber-200',
  Stable: 'bg-slate-100 text-slate-600 border-slate-200',
  Escalating: 'bg-orange-50 text-orange-700 border-orange-200',
  Improving: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  Declining: 'bg-blue-50 text-blue-700 border-blue-200',
}

const TIMEFRAME_STYLES: Record<BriefTimeframe, string> = {
  Immediate: 'bg-red-50 text-red-700',
  'Short-term': 'bg-amber-50 text-amber-700',
  'Long-term': 'bg-blue-50 text-blue-700',
}

function NullValue() {
  return <span className="text-subtle">-</span>
}

function evidenceBarColor(confidence: number) {
  if (confidence >= 0.85) return 'bg-emerald-500'
  if (confidence >= 0.7) return 'bg-amber-500'
  return 'bg-red-400'
}

function percentage(value: number) {
  return Math.round((value <= 1 ? value * 100 : value))
}

function scrollToAnchor(id: string) {
  const element = document.getElementById(id)
  if (!element) return
  element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export function buildSourceRefs(signal: Signal) {
  return signal.sources.map((source, index) => ({
    ...source,
    label: `SRC-${index + 1}`,
    anchorId: `brief-source-ref-SRC-${index + 1}`,
  }))
}

function formatClaimForExport(claim: BriefClaim) {
  const refs = [...claim.signal_refs, ...claim.source_refs]
  return refs.length > 0
    ? `${claim.text} [${refs.join(', ')}]`
    : claim.text
}

function ModeToggle({
  value,
  onChange,
}: {
  value: BriefViewMode
  onChange: (value: BriefViewMode) => void
}) {
  return (
    <div className="inline-flex rounded-lg border border-border bg-muted/60 p-1">
      {([
        { id: 'executive', label: 'Executive' },
        { id: 'analyst', label: 'Analyst' },
      ] as const).map((mode) => (
        <button
          key={mode.id}
          onClick={() => onChange(mode.id)}
          className={cn(
            'rounded-md px-3 py-1.5 text-[11px] font-medium transition-colors',
            value === mode.id
              ? 'bg-surface text-heading shadow-sm'
              : 'text-subtle hover:text-body',
          )}
        >
          {mode.label}
        </button>
      ))}
    </div>
  )
}

function SectionHeader({
  label,
  icon: Icon,
  count,
}: {
  label: string
  icon?: LucideIcon
  count?: number
}) {
  return (
    <div className="mb-2 flex items-center gap-2">
      {Icon && <Icon size={13} className="shrink-0 text-subtle" />}
      <h3 className="text-[11px] font-semibold uppercase tracking-widest text-subtle">{label}</h3>
      {count != null && (
        <span className="rounded-pill bg-muted px-1.5 py-0.5 text-[10px] text-subtle">
          {count}
        </span>
      )}
    </div>
  )
}

function SnapshotCard({
  label,
  value,
  tone,
}: {
  label: string
  value: string | null
  tone: string
}) {
  return (
    <div className={cn('rounded-xl border px-4 py-3', tone)}>
      <p className="text-[10px] font-semibold uppercase tracking-wider">{label}</p>
      <p className="mt-1 text-[13px] leading-relaxed text-body">
        {value ?? <NullValue />}
      </p>
    </div>
  )
}

function QuestionCard({
  label,
  value,
  compact = false,
}: {
  label: string
  value: string | null
  compact?: boolean
}) {
  return (
    <div className={cn('rounded-xl border border-border bg-surface px-4 py-3', compact && 'min-h-[88px]')}>
      <p className="text-[10px] font-semibold uppercase tracking-widest text-subtle">{label}</p>
      <p className="mt-1 text-[13px] leading-relaxed text-body">{value ?? <NullValue />}</p>
    </div>
  )
}

function ActionListCard({
  label,
  actions,
  tone,
}: {
  label: string
  actions: string[]
  tone: string
}) {
  return (
    <div className={cn('rounded-xl border px-4 py-3', tone)}>
      <p className="text-[10px] font-semibold uppercase tracking-widest">{label}</p>
      {actions.length > 0 ? (
        <ol className="mt-2 space-y-2">
          {actions.map((action, index) => (
            <li key={`${label}-${action}`} className="flex gap-2 text-[13px] leading-relaxed text-body">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-white/60 text-[10px] font-semibold">
                {index + 1}
              </span>
              <span>{action}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-2 text-[13px] text-subtle">No actions yet.</p>
      )}
    </div>
  )
}

function AnalystList({
  title,
  items,
  tone,
}: {
  title: string
  items: string[]
  tone: string
}) {
  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold text-subtle">{title}</p>
      <ul className="space-y-2">
        {items.map((item) => (
          <li key={item} className="flex gap-2 text-[13px] leading-relaxed text-body">
            <span className={cn('mt-0.5 shrink-0 font-semibold', tone)}>+</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

function DriverGroup({
  title,
  items,
}: {
  title: string
  items: string[]
}) {
  if (items.length === 0) return null

  return (
    <div>
      <p className="mb-2 text-[11px] font-semibold text-subtle">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item} className="rounded-md border border-border bg-muted px-2 py-1 text-[11px] text-body">
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}

function ClaimItem({
  claim,
  index,
}: {
  claim: BriefClaim
  index: number
}) {
  const refs = [
    ...claim.signal_refs.map((ref) => ({ label: ref, anchor: `brief-evidence-${ref}` })),
    ...claim.source_refs.map((ref) => ({ label: ref, anchor: `brief-source-ref-${ref}` })),
  ]

  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] leading-relaxed text-body">{claim.text}</p>
          {(refs.length > 0 || claim.evidence_note) && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {refs.map((ref) => (
                <button
                  key={`${claim.text}-${ref.label}`}
                  onClick={() => scrollToAnchor(ref.anchor)}
                  className="rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-subtle transition-colors hover:bg-primary/10 hover:text-primary"
                >
                  {ref.label}
                </button>
              ))}
              {claim.evidence_note && (
                <span className="text-[11px] text-subtle">{claim.evidence_note}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function EvidenceCard({
  item,
  detailed = false,
}: {
  item: Signal['brief']['signals_and_indicators']['signal_evidence'][number]
  detailed?: boolean
}) {
  return (
    <div
      id={`brief-evidence-${item.signal_ref}`}
      className="rounded-xl border border-border bg-surface px-4 py-3"
    >
      <div className="flex items-center gap-2">
        <span className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-subtle">
          {item.signal_ref}
        </span>
        <span className="truncate text-[12px] font-medium text-heading">{item.signal_title}</span>
      </div>
      <div className="mt-2 flex items-center gap-2">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className={cn('h-full rounded-full', evidenceBarColor(item.confidence))}
            style={{ width: `${percentage(item.confidence)}%` }}
          />
        </div>
        <span className="text-[10px] tabular-nums text-subtle">{percentage(item.confidence)}%</span>
      </div>
      <p className="mt-2 text-[12px] leading-relaxed text-body">{item.contribution}</p>
      {detailed && item.source_refs.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {item.source_refs.map((ref) => (
            <button
              key={`${item.signal_ref}-${ref}`}
              onClick={() => scrollToAnchor(`brief-source-ref-${ref}`)}
              className="rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-subtle transition-colors hover:bg-primary/10 hover:text-primary"
            >
              {ref}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function ImpactCard({
  label,
  items,
  tone,
}: {
  label: string
  items: Array<[string, string | null]>
  tone: string
}) {
  return (
    <div className={cn('rounded-xl border px-4 py-3', tone)}>
      <p className="text-[10px] font-semibold uppercase tracking-widest">{label}</p>
      <div className="mt-2 space-y-2">
        {items.map(([itemLabel, value]) => (
          <div key={itemLabel}>
            <p className="text-[10px] font-semibold uppercase text-subtle">{itemLabel}</p>
            <p className="text-[13px] leading-relaxed text-body">{value ?? <NullValue />}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function buildCoverageStats(signal: Signal) {
  const brief = signal.brief
  return [
    { label: 'Claims', value: String(brief.executive_summary.insights.length), tone: 'bg-slate-50 text-slate-700 border-slate-200' },
    { label: 'Evidence', value: String(brief.signals_and_indicators.signal_evidence.length), tone: 'bg-blue-50 text-blue-700 border-blue-200' },
    { label: 'Actions', value: String(brief.recommended_actions.immediate.length + brief.recommended_actions.strategic.length), tone: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    { label: 'Limitations', value: String(brief.limitations.length), tone: 'bg-amber-50 text-amber-700 border-amber-200' },
  ]
}

export function buildExecutiveSections(signal: Signal) {
  const brief = signal.brief
  const actionLines = [
    ...brief.recommended_actions.immediate.map((item, index) => `Immediate ${index + 1}: ${item}`),
    ...brief.recommended_actions.strategic.map((item, index) => `Strategic ${index + 1}: ${item}`),
  ]

  return [
    {
      heading: 'Bottom Line',
      content: [
        brief.executive_summary.bottom_line,
        brief.executive_summary.why_it_matters && `Why it matters now: ${brief.executive_summary.why_it_matters}`,
        brief.executive_summary.recommended_action && `Action now: ${brief.executive_summary.recommended_action}`,
        brief.executive_summary.watchpoint && `Watchpoint: ${brief.executive_summary.watchpoint}`,
      ].filter(Boolean).join('\n\n'),
    },
    {
      heading: 'Key Claims',
      content: brief.executive_summary.insights.map(formatClaimForExport).join('\n'),
    },
    {
      heading: 'Actions',
      content: actionLines.join('\n'),
    },
    {
      heading: 'Confidence',
      content: `${signal.confidence}% confidence\n${brief.confidence_note ?? ''}`.trim(),
    },
  ].filter((section) => section.content)
}

export function buildAnalystSections(signal: Signal) {
  const brief = signal.brief
  const questionLines = [
    brief.key_intelligence_questions.what_is_happening ? `What is happening: ${brief.key_intelligence_questions.what_is_happening}` : null,
    brief.key_intelligence_questions.why_is_it_happening ? `Why it is happening: ${brief.key_intelligence_questions.why_is_it_happening}` : null,
    brief.key_intelligence_questions.what_will_happen_next ? `What happens next: ${brief.key_intelligence_questions.what_will_happen_next}` : null,
    brief.key_intelligence_questions.impact_on_organization ? `Impact: ${brief.key_intelligence_questions.impact_on_organization}` : null,
  ].filter((line): line is string => Boolean(line))

  const evidenceLines = brief.signals_and_indicators.signal_evidence.map((item) => (
    `${item.signal_ref}: ${item.signal_title}\nConfidence: ${percentage(item.confidence)}%\nSources: ${item.source_refs.join(', ') || 'None'}\n${item.contribution}`
  ))

  const driverLines = [
    ...brief.analysis.drivers.technology.map((item) => `Technology: ${item}`),
    ...brief.analysis.drivers.market.map((item) => `Market: ${item}`),
    ...brief.analysis.drivers.regulatory.map((item) => `Regulatory: ${item}`),
    ...brief.analysis.patterns_detected.map((item) => `Pattern: ${item}`),
  ]

  const impactLines = [
    brief.impact_assessment.short_term.operations ? `Short-term operations: ${brief.impact_assessment.short_term.operations}` : null,
    brief.impact_assessment.short_term.infrastructure ? `Short-term infrastructure: ${brief.impact_assessment.short_term.infrastructure}` : null,
    brief.impact_assessment.short_term.product_roadmap ? `Short-term product roadmap: ${brief.impact_assessment.short_term.product_roadmap}` : null,
    brief.impact_assessment.long_term.market_position ? `Long-term market position: ${brief.impact_assessment.long_term.market_position}` : null,
    brief.impact_assessment.long_term.innovation_strategy ? `Long-term innovation strategy: ${brief.impact_assessment.long_term.innovation_strategy}` : null,
    brief.impact_assessment.long_term.competitive_landscape ? `Long-term competitive landscape: ${brief.impact_assessment.long_term.competitive_landscape}` : null,
  ].filter((line): line is string => Boolean(line))

  const actionLines = [
    ...brief.recommended_actions.immediate.map((item, index) => `Immediate ${index + 1}: ${item}`),
    ...brief.recommended_actions.strategic.map((item, index) => `Strategic ${index + 1}: ${item}`),
  ]

  return [
    {
      heading: 'Executive Summary',
      content: [
        brief.executive_summary.bottom_line,
        brief.executive_summary.why_it_matters,
        ...brief.executive_summary.insights.map(formatClaimForExport),
      ].filter(Boolean).join('\n\n'),
    },
    {
      heading: 'Key Intelligence Questions',
      content: questionLines.join('\n\n'),
    },
    {
      heading: 'Situation Overview',
      content: brief.situation_overview.overview ?? '',
    },
    {
      heading: 'Signal Evidence',
      content: evidenceLines.join('\n\n'),
    },
    {
      heading: 'Analysis',
      content: driverLines.join('\n\n'),
    },
    {
      heading: 'Impact Assessment',
      content: impactLines.join('\n\n'),
    },
    {
      heading: 'Recommended Actions',
      content: actionLines.join('\n'),
    },
    {
      heading: 'Outlook',
      content: brief.outlook ?? '',
    },
    {
      heading: 'Limitations',
      content: brief.limitations.join('\n'),
    },
  ].filter((section) => section.content)
}

export function SignalDrawer({ signal, onClose, onSave }: SignalDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null)
  const shareRef = useRef<HTMLDivElement>(null)
  const [mounted, setMounted] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const [exportingFmt, setExportingFmt] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<BriefViewMode>('executive')

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    setViewMode('executive')
  }, [signal?.id])

  useEffect(() => {
    if (!shareOpen) return
    function handleClick(event: MouseEvent) {
      if (shareRef.current && !shareRef.current.contains(event.target as Node)) {
        setShareOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [shareOpen])

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose])

  useEffect(() => {
    if (signal) {
      document.body.style.overflow = 'hidden'
      drawerRef.current?.focus()
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [signal])

  const sourceRefs = useMemo(() => (signal ? buildSourceRefs(signal) : []), [signal])

  if (!mounted) return null

  function copyLink() {
    if (!signal) return
    navigator.clipboard.writeText(`${window.location.origin}/dashboard/signals?open=${signal.id}`).catch(() => {})
    setShareOpen(false)
  }

  function shareToTwitter() {
    if (!signal) return
    const title = encodeURIComponent(`${signal.headline} - ${signal.entityName}`)
    const url = encodeURIComponent(`${window.location.origin}/dashboard/signals?open=${signal.id}`)
    window.open(`https://twitter.com/intent/tweet?text=${title}&url=${url}`, '_blank')
    setShareOpen(false)
  }

  function shareToLinkedIn() {
    if (!signal) return
    const url = encodeURIComponent(`${window.location.origin}/dashboard/signals?open=${signal.id}`)
    const title = encodeURIComponent(signal.headline)
    window.open(`https://www.linkedin.com/shareArticle?mini=true&url=${url}&title=${title}`, '_blank')
    setShareOpen(false)
  }

  function downloadMarkdown() {
    if (!signal) return
    const sections = viewMode === 'executive' ? buildExecutiveSections(signal) : buildAnalystSections(signal)
    const markdown = [
      `# ${signal.headline}`,
      '',
      `**Entity**: ${signal.entityName}  `,
      `**Domain**: ${signal.domain}  `,
      `**Confidence**: ${signal.confidence}%  `,
      `**View**: ${viewMode === 'executive' ? 'Executive' : 'Analyst'}  `,
      '',
      ...sections.flatMap((section) => [`## ${section.heading}`, section.content, '']),
    ].join('\n')

    const blob = new Blob([markdown], { type: 'text/markdown' })
    const anchor = document.createElement('a')
    anchor.href = URL.createObjectURL(blob)
    anchor.download = `${signal.entityName.replace(/[\s/]+/g, '-').toLowerCase()}-${viewMode}-brief.md`
    anchor.click()
    URL.revokeObjectURL(anchor.href)
    setShareOpen(false)
  }

  async function handleExport(format: 'pdf-html' | 'pptx' | 'docx') {
    if (!signal || exportingFmt) return
    setExportingFmt(format)
    setShareOpen(false)
    try {
      const sections = viewMode === 'executive' ? buildExecutiveSections(signal) : buildAnalystSections(signal)
      await exportBrief({
        title: signal.headline,
        subtitle: `${signal.entityName} - ${viewMode === 'executive' ? 'Executive Brief' : 'Analyst Brief'}`,
        domain: signal.domain,
        author: 'Cogent Intelligence',
        confidence: signal.confidence,
        sections,
        format,
      })
    } catch (error) {
      console.error('Export failed:', error)
    } finally {
      setExportingFmt(null)
    }
  }

  return createPortal(
    <>
      <div
        onClick={onClose}
        className={cn(
          'fixed inset-0 z-[200] bg-black/20 backdrop-blur-[2px] transition-opacity duration-200',
          signal ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />

      <div
        ref={drawerRef}
        tabIndex={-1}
        className={cn(
          'fixed right-0 top-0 z-[201] flex h-full w-[680px] max-w-[96vw] flex-col border-l border-border bg-surface shadow-2xl outline-none transition-transform duration-300 ease-out',
          signal ? 'translate-x-0' : 'translate-x-full',
        )}
      >
        {signal && (
          <>
            <div className="border-b border-border px-6 pb-4 pt-5">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge variant={getDomainBadge(signal.domain) as never}>
                      {signal.domain}
                    </Badge>
                    {signal.severity === 'critical' && <Badge variant="critical">Critical</Badge>}
                    <span className="ml-auto text-xs text-subtle">{signal.relativeTime}</span>
                  </div>
                  <h2 className="text-[16px] font-medium leading-snug text-heading">{signal.headline}</h2>
                  <p className="mt-1 text-xs text-subtle">{signal.entityName}</p>
                </div>

                <div className="flex shrink-0 items-start gap-2">
                  <ModeToggle value={viewMode} onChange={setViewMode} />
                  <button
                    onClick={() => onSave(signal.id)}
                    className={cn(
                      'rounded-lg p-2 transition-colors',
                      signal.isSaved
                        ? 'bg-primary/10 text-primary'
                        : 'text-subtle hover:bg-muted hover:text-body',
                    )}
                    title="Save"
                  >
                    <Bookmark size={15} fill={signal.isSaved ? 'currentColor' : 'none'} />
                  </button>
                  <div ref={shareRef} className="relative">
                    <button
                      onClick={() => setShareOpen((current) => !current)}
                      className={cn(
                        'rounded-lg p-2 transition-colors',
                        shareOpen ? 'bg-primary/10 text-primary' : 'text-subtle hover:bg-muted hover:text-body',
                      )}
                      title="Share or export"
                    >
                      <Share2 size={15} />
                    </button>
                    {shareOpen && (
                      <div className="absolute right-0 top-full z-10 mt-1 w-56 overflow-hidden rounded-xl border border-border bg-surface text-left shadow-2xl">
                        <div className="px-3 pb-1 pt-2.5">
                          <p className="text-[9px] font-semibold uppercase tracking-widest text-subtle">Share</p>
                        </div>
                        <div className="px-1 pb-1">
                          <button onClick={copyLink} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted">
                            <Link2 size={13} className="shrink-0 text-subtle" />
                            Copy link
                          </button>
                          <button onClick={shareToTwitter} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted">
                            <ExternalLink size={13} className="shrink-0 text-subtle" />
                            Twitter / X
                          </button>
                          <button onClick={shareToLinkedIn} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted">
                            <ExternalLink size={13} className="shrink-0 text-subtle" />
                            LinkedIn
                          </button>
                        </div>
                        <div className="border-t border-border px-3 pb-1 pt-2.5">
                          <p className="text-[9px] font-semibold uppercase tracking-widest text-subtle">Export</p>
                        </div>
                        <div className="px-1 pb-2">
                          <button onClick={downloadMarkdown} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted">
                            <FileText size={13} className="shrink-0 text-subtle" />
                            Markdown (.md)
                          </button>
                          <button onClick={() => handleExport('pdf-html')} disabled={Boolean(exportingFmt)} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted disabled:opacity-50">
                            <Download size={13} className="shrink-0 text-subtle" />
                            {exportingFmt === 'pdf-html' ? 'Preparing...' : 'PDF'}
                          </button>
                          <button onClick={() => handleExport('pptx')} disabled={Boolean(exportingFmt)} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted disabled:opacity-50">
                            <Download size={13} className="shrink-0 text-subtle" />
                            {exportingFmt === 'pptx' ? 'Generating...' : 'PowerPoint (.pptx)'}
                          </button>
                          <button onClick={() => handleExport('docx')} disabled={Boolean(exportingFmt)} className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-[12px] text-body transition-colors hover:bg-muted disabled:opacity-50">
                            <Download size={13} className="shrink-0 text-subtle" />
                            {exportingFmt === 'docx' ? 'Generating...' : 'Word (.docx)'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                  <button onClick={onClose} className="rounded-lg p-2 text-subtle transition-colors hover:bg-muted hover:text-body" title="Close">
                    <X size={15} />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 border-b border-border bg-muted/30 px-6 py-2">
              <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                Category: {signal.brief.metadata.category}
              </span>
              <span className={cn('rounded-full border px-2 py-0.5 text-[10px] font-medium', CONFIDENCE_STYLES[signal.brief.metadata.confidence_level])}>
                Confidence: {signal.brief.metadata.confidence_level}
              </span>
              <span className={cn('rounded-full border px-2 py-0.5 text-[10px] font-medium', PRIORITY_STYLES[signal.brief.metadata.priority_level])}>
                Priority: {signal.brief.metadata.priority_level}
              </span>
              <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-medium', TIMEFRAME_STYLES[signal.brief.situation_overview.timeframe])}>
                {signal.brief.situation_overview.timeframe}
              </span>
            </div>

            <ScrollArea className="flex-1 overflow-y-auto">
              <div className="space-y-6 px-6 py-5">
                <section>
                  <SectionHeader label="Decision Snapshot" icon={Lightbulb} />
                  <div className="grid gap-3 md:grid-cols-2">
                    <SnapshotCard
                      label="Bottom line"
                      value={signal.brief.executive_summary.bottom_line}
                      tone="border-primary/15 bg-primary/5"
                    />
                    <SnapshotCard
                      label="Why it matters now"
                      value={signal.brief.executive_summary.why_it_matters}
                      tone="border-amber-100 bg-amber-50/70"
                    />
                    <SnapshotCard
                      label="Action this week"
                      value={signal.brief.executive_summary.recommended_action}
                      tone="border-emerald-100 bg-emerald-50/70"
                    />
                    <SnapshotCard
                      label="What could change this view"
                      value={signal.brief.executive_summary.watchpoint}
                      tone="border-blue-100 bg-blue-50/70"
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <span className={cn('rounded-full border px-2 py-0.5 text-[10px] font-medium', SITUATION_STYLES[signal.brief.executive_summary.situation_status])}>
                      {signal.brief.executive_summary.situation_status}
                    </span>
                    {signal.brief.executive_summary.decision_required && signal.brief.executive_summary.decision_description && (
                      <span className="rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">
                        Decision required: {signal.brief.executive_summary.decision_description}
                      </span>
                    )}
                    {signal.brief.tags.map((tag) => (
                      <span key={tag} className="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] text-subtle">
                        {tag}
                      </span>
                    ))}
                  </div>
                </section>

                {viewMode === 'executive' ? (
                  <>
                    <section>
                      <SectionHeader label="Key Claims" icon={FileText} count={signal.brief.executive_summary.insights.length} />
                      <div className="space-y-3">
                        {signal.brief.executive_summary.insights.length > 0 ? (
                          signal.brief.executive_summary.insights.map((claim, index) => (
                            <ClaimItem key={`${claim.text}-${index}`} claim={claim} index={index} />
                          ))
                        ) : (
                          <div className="rounded-xl border border-border bg-muted/30 px-4 py-3 text-[13px] text-subtle">
                            No executive claims are available yet.
                          </div>
                        )}
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="What To Do" icon={Zap} />
                      <div className="grid gap-3 md:grid-cols-2">
                        <ActionListCard label="Immediate" actions={signal.brief.recommended_actions.immediate} tone="border-red-100 bg-red-50/70" />
                        <ActionListCard label="Strategic" actions={signal.brief.recommended_actions.strategic} tone="border-blue-100 bg-blue-50/70" />
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Support Signals" icon={Radio} count={signal.brief.signals_and_indicators.signal_evidence.length} />
                      <div className="space-y-3">
                        {signal.brief.signals_and_indicators.signal_evidence.slice(0, 3).map((item) => (
                          <EvidenceCard key={item.signal_ref} item={item} />
                        ))}
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Confidence And Limits" icon={AlertCircle} />
                      <div className="space-y-3">
                        <div className="rounded-xl border border-border bg-surface px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                              <div
                                className={cn('h-full rounded-full', evidenceBarColor(signal.confidence / 100))}
                                style={{ width: `${signal.confidence}%` }}
                              />
                            </div>
                            <span className="text-[12px] font-medium tabular-nums text-body">{signal.confidence}%</span>
                          </div>
                          <p className="mt-2 text-[12px] leading-relaxed text-subtle">
                            {signal.brief.confidence_note ?? `Confidence ${signal.confidence}% reflects source corroboration, recency, and signal reliability.`}
                          </p>
                        </div>
                        {signal.brief.limitations.length > 0 && (
                          <div className="rounded-xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                            <p className="text-[11px] font-semibold uppercase tracking-widest text-amber-700">Limitations</p>
                            <ul className="mt-2 space-y-1.5">
                              {signal.brief.limitations.map((item) => (
                                <li key={item} className="text-[12px] leading-relaxed text-body">
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </section>
                  </>
                ) : (
                  <>
                    <section>
                      <SectionHeader label="Analyst Coverage" icon={BarChart2} />
                      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        {buildCoverageStats(signal).map((item) => (
                          <div key={item.label} className={cn('rounded-xl border px-4 py-3', item.tone)}>
                            <p className="text-[10px] font-semibold uppercase tracking-widest">{item.label}</p>
                            <p className="mt-1 text-[20px] font-semibold leading-none">{item.value}</p>
                          </div>
                        ))}
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Executive Summary" icon={FileText} />
                      <div className="space-y-3">
                        {signal.brief.executive_summary.insights.length > 0 ? (
                          signal.brief.executive_summary.insights.map((claim, index) => (
                            <ClaimItem key={`${claim.text}-${index}`} claim={claim} index={index} />
                          ))
                        ) : (
                          <div className="rounded-xl border border-border bg-muted/30 px-4 py-3 text-[13px] text-subtle">
                            No analyst claims are available yet.
                          </div>
                        )}
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Key Intelligence Questions" icon={Lightbulb} />
                      <div className="grid gap-3 md:grid-cols-2">
                        <QuestionCard label="What is happening?" value={signal.brief.key_intelligence_questions.what_is_happening} />
                        <QuestionCard label="Why is it happening?" value={signal.brief.key_intelligence_questions.why_is_it_happening} />
                        <QuestionCard label="What happens next?" value={signal.brief.key_intelligence_questions.what_will_happen_next} />
                        <QuestionCard label="What is the impact?" value={signal.brief.key_intelligence_questions.impact_on_organization} />
                      </div>
                    </section>
                    
                    <section>
                      <SectionHeader label="Situation Overview" icon={Compass} />
                      <div className="rounded-xl border border-border bg-surface px-4 py-3">
                        <div className="mb-2 flex flex-wrap gap-2">
                          {signal.brief.situation_overview.topic && (
                            <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] text-subtle">
                              Topic: {signal.brief.situation_overview.topic}
                            </span>
                          )}
                          {signal.brief.situation_overview.region_market && (
                            <span className="rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] text-subtle">
                              Region: {signal.brief.situation_overview.region_market}
                            </span>
                          )}
                        </div>
                        <p className="text-[13px] leading-relaxed text-body">
                          {signal.brief.situation_overview.overview ?? <NullValue />}
                        </p>
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Signals And Indicators" icon={Radio} />
                      <div className="space-y-4">
                        {signal.brief.signals_and_indicators.leading_indicators.length > 0 && (
                          <AnalystList
                            title="Leading indicators"
                            items={signal.brief.signals_and_indicators.leading_indicators}
                            tone="text-emerald-700"
                          />
                        )}
                        {signal.brief.signals_and_indicators.triggers.length > 0 && (
                          <AnalystList
                            title="Triggers"
                            items={signal.brief.signals_and_indicators.triggers}
                            tone="text-amber-700"
                          />
                        )}
                        {signal.brief.signals_and_indicators.signal_evidence.length > 0 && (
                          <div>
                            <p className="mb-2 text-[11px] font-semibold text-subtle">Evidence matrix</p>
                            <div className="space-y-3">
                              {signal.brief.signals_and_indicators.signal_evidence.map((item) => (
                                <EvidenceCard key={item.signal_ref} item={item} detailed />
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Analysis" icon={BarChart2} />
                      <div className="space-y-4">
                        <DriverGroup title="Technology" items={signal.brief.analysis.drivers.technology} />
                        <DriverGroup title="Market" items={signal.brief.analysis.drivers.market} />
                        <DriverGroup title="Regulatory" items={signal.brief.analysis.drivers.regulatory} />
                        {signal.brief.analysis.patterns_detected.length > 0 && (
                          <AnalystList title="Patterns detected" items={signal.brief.analysis.patterns_detected} tone="text-primary" />
                        )}
                        <div>
                          <p className="mb-2 text-[11px] font-semibold text-subtle">Risk assessment</p>
                          <div className="grid gap-3 md:grid-cols-2">
                            <QuestionCard label="Operational" value={signal.brief.analysis.risk_assessment.operational} compact />
                            <QuestionCard label="Strategic" value={signal.brief.analysis.risk_assessment.strategic} compact />
                            <QuestionCard label="Technical" value={signal.brief.analysis.risk_assessment.technical} compact />
                            <QuestionCard label="Market" value={signal.brief.analysis.risk_assessment.market} compact />
                          </div>
                        </div>
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Impact Assessment" icon={TrendingUp} />
                      <div className="grid gap-3 md:grid-cols-2">
                        <ImpactCard
                          label="Short-term"
                          tone="border-orange-100 bg-orange-50/70"
                          items={[
                            ['Operations', signal.brief.impact_assessment.short_term.operations],
                            ['Infrastructure', signal.brief.impact_assessment.short_term.infrastructure],
                            ['Product roadmap', signal.brief.impact_assessment.short_term.product_roadmap],
                          ]}
                        />
                        <ImpactCard
                          label="Long-term"
                          tone="border-blue-100 bg-blue-50/70"
                          items={[
                            ['Market position', signal.brief.impact_assessment.long_term.market_position],
                            ['Innovation strategy', signal.brief.impact_assessment.long_term.innovation_strategy],
                            ['Competitive landscape', signal.brief.impact_assessment.long_term.competitive_landscape],
                          ]}
                        />
                      </div>
                    </section>

                    {signal.brief.outlook && (
                      <section>
                        <SectionHeader label="Outlook" icon={Compass} />
                        <div className="rounded-xl border border-border border-l-4 border-l-primary bg-surface px-4 py-3">
                          <p className="text-[13px] leading-relaxed text-body">{signal.brief.outlook}</p>
                        </div>
                      </section>
                    )}

                    <section>
                      <SectionHeader label="Recommended Actions" icon={Zap} />
                      <div className="grid gap-3 md:grid-cols-2">
                        <ActionListCard label="Immediate" actions={signal.brief.recommended_actions.immediate} tone="border-red-100 bg-red-50/70" />
                        <ActionListCard label="Strategic" actions={signal.brief.recommended_actions.strategic} tone="border-blue-100 bg-blue-50/70" />
                      </div>
                    </section>

                    <section>
                      <SectionHeader label="Decision Lens And Reliability" icon={AlertCircle} />
                      <div className="space-y-3">
                        {signal.brief.decision_lens && (
                          <div className="rounded-xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                            <p className="text-[13px] leading-relaxed text-body">{signal.brief.decision_lens}</p>
                          </div>
                        )}
                        <div className="rounded-xl border border-border bg-surface px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                              <div
                                className={cn('h-full rounded-full', evidenceBarColor(signal.confidence / 100))}
                                style={{ width: `${signal.confidence}%` }}
                              />
                            </div>
                            <span className="text-[12px] font-medium tabular-nums text-body">{signal.confidence}%</span>
                          </div>
                          <p className="mt-2 text-[12px] leading-relaxed text-subtle">
                            {signal.brief.confidence_note ?? `Confidence ${signal.confidence}% reflects source corroboration, recency, and signal reliability.`}
                          </p>
                        </div>
                        {signal.brief.limitations.length > 0 && (
                          <div className="rounded-xl border border-amber-100 bg-amber-50/70 px-4 py-3">
                            <p className="text-[11px] font-semibold uppercase tracking-widest text-amber-700">Constraints and limitations</p>
                            <ul className="mt-2 space-y-1.5">
                              {signal.brief.limitations.map((item) => (
                                <li key={item} className="text-[12px] leading-relaxed text-body">
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </section>
                  </>
                )}

                <section>
                  <SectionHeader label="Sources" icon={ExternalLink} count={sourceRefs.length} />
                  <div className="space-y-2">
                    {sourceRefs.length > 0 ? (
                      sourceRefs.map((source) => (
                        <a
                          key={source.id}
                          id={source.anchorId}
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2 transition-colors hover:bg-muted"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <div>
                            <p className="text-[12px] font-medium text-heading">{source.label} - {source.name}</p>
                            <p className="text-[11px] text-subtle">
                              {new Date(source.publishedAt).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                            </p>
                          </div>
                          <ExternalLink size={12} className="text-subtle transition-colors group-hover:text-primary" />
                        </a>
                      ))
                    ) : (
                      <div className="rounded-xl border border-border bg-muted/30 px-4 py-3 text-[13px] text-subtle">
                        No linked sources are available for this brief yet.
                      </div>
                    )}
                  </div>
                </section>
              </div>
            </ScrollArea>
          </>
        )}
      </div>
    </>,
    document.body,
  )
}
