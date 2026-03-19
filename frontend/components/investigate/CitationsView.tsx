'use client'

import { ExternalLink, FileText } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Citation } from '@/lib/hooks/useInvestigate'

interface CitationsViewProps {
  citations: Citation[]
}

const RELEVANCE_CONFIG = {
  high:   { label: 'High relevance',   dot: 'bg-emerald-500', tag: 'text-emerald-700 bg-emerald-50 border-emerald-200' },
  medium: { label: 'Medium relevance', dot: 'bg-amber-500',   tag: 'text-amber-700   bg-amber-50   border-amber-200'   },
  low:    { label: 'Low relevance',    dot: 'bg-slate-400',   tag: 'text-slate-600   bg-slate-100  border-slate-200'   },
}

export function CitationsView({ citations }: CitationsViewProps) {
  return (
    <div className="flex flex-col gap-3">
      {citations.map(citation => (
        <CitationCard key={citation.id} citation={citation} />
      ))}
    </div>
  )
}

function CitationCard({ citation }: { citation: Citation }) {
  const rel = RELEVANCE_CONFIG[citation.relevance]

  // Split excerpt around highlight to render the highlight portion styled
  const hasHighlight = Boolean(citation.highlight)
  const parts = hasHighlight ? citation.excerpt.split(citation.highlight) : [citation.excerpt]

  return (
    <div className="border border-border rounded-xl bg-surface hover:border-primary/30 transition-colors group">
      {/* Card header */}
      <div className="flex items-start justify-between gap-3 px-4 pt-3.5 pb-2.5 border-b border-border/60">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-primary/8 flex items-center justify-center shrink-0 mt-0.5">
            <FileText size={13} className="text-primary" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[10px] font-bold bg-muted text-subtle border border-border rounded px-1.5 py-0.5 shrink-0">
                [{citation.index}]
              </span>
              <p className="text-[12px] font-medium text-heading truncate leading-snug">
                {citation.sourceTitle}
              </p>
            </div>
            <p className="text-[11px] text-subtle">{citation.sourceName}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={cn('text-[10px] font-medium px-2 py-0.5 rounded-full border', rel.tag)}>
            {rel.label}
          </span>
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-lg text-subtle hover:text-primary hover:bg-primary/5 transition-colors"
            title="Open source"
          >
            <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {/* Excerpt with highlighted portion */}
      <div className="px-4 py-3">
        <p className="text-[12px] text-body leading-relaxed">
          {parts[0]}
          {hasHighlight && (
            <mark className="bg-primary/10 text-primary rounded px-0.5 not-italic font-medium">
              {citation.highlight}
            </mark>
          )}
          {parts[1]}
        </p>
      </div>

      {/* Footer */}
      <div className="px-4 pb-3">
        <span className="text-[10px] text-subtle">
          Published{' '}
          {new Date(citation.publishedAt).toLocaleDateString('en-GB', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
          })}
        </span>
      </div>
    </div>
  )
}
