'use client'

import { useState } from 'react'
import { Bookmark, BookmarkCheck, Clock, ChevronRight, Sparkles, BarChart2, FileText, TrendingUp } from 'lucide-react'
import { AbstractPattern } from './AbstractPattern'
import type { LibraryBrief, LibraryBriefType } from '@/lib/hooks/useLibrary'

// ── Type label + icon map ─────────────────────────────────────────────────────

const TYPE_META: Record<LibraryBriefType, { label: string; icon: React.ReactNode; color: string }> = {
  'ai-brief':      { label: 'AI Brief',      icon: <Sparkles className="h-3 w-3" />,  color: 'text-indigo-500 bg-indigo-50 border-indigo-100' },
  'weekly-report': { label: 'Weekly Report', icon: <BarChart2 className="h-3 w-3" />, color: 'text-violet-600 bg-violet-50 border-violet-100' },
  'deep-analysis': { label: 'Deep Analysis', icon: <TrendingUp className="h-3 w-3" />,color: 'text-blue-600 bg-blue-50 border-blue-100' },
  'sector-review': { label: 'Sector Review', icon: <FileText className="h-3 w-3" />,  color: 'text-slate-600 bg-slate-50 border-slate-200' },
}

// ── Confidence pill ───────────────────────────────────────────────────────────

function ConfidencePill({ score }: { score: number }) {
  const color =
    score >= 85 ? 'bg-emerald-50 text-emerald-700 border-emerald-100' :
    score >= 70 ? 'bg-amber-50  text-amber-700  border-amber-100' :
                  'bg-slate-50  text-slate-600  border-slate-200'
  return (
    <span className={`inline-flex items-center gap-1 rounded-pill border px-1.5 py-0.5 text-[10px] font-medium ${color}`}>
      <span className="font-mono">{score}%</span>
    </span>
  )
}

// ── Main card ─────────────────────────────────────────────────────────────────

interface BriefCardProps {
  brief: LibraryBrief
  onOpen: (brief: LibraryBrief) => void
  onToggleSave: (id: string) => void
}

export function BriefCard({ brief, onOpen, onToggleSave }: BriefCardProps) {
  const [hovered, setHovered] = useState(false)
  const typeMeta = TYPE_META[brief.type]

  return (
    <article
      className="group flex flex-col overflow-hidden rounded-xl border border-border bg-surface shadow-card transition-all duration-200 hover:shadow-modal cursor-pointer"
      style={{ transform: 'translateZ(0)' }}
      onClick={() => onOpen(brief)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={`Open brief: ${brief.title}`}
    >
      {/* ── Abstract pattern header ─────────────────────────────────────────── */}
      <div className="relative h-44 w-full overflow-hidden">
        <AbstractPattern
          id={brief.id}
          domain={brief.domain}
          type={brief.type}
          width={400}
          height={176}
        />

        {/* Type badge — overlaid top-left */}
        <div className="absolute left-3 top-3">
          <span
            className={`inline-flex items-center gap-1 rounded-pill border px-2 py-0.5 text-[10px] font-medium backdrop-blur-sm ${typeMeta.color}`}
          >
            {typeMeta.icon}
            {typeMeta.label}
          </span>
        </div>

        {/* Save button — overlaid top-right */}
        <button
          className="absolute right-2.5 top-2.5 flex h-7 w-7 items-center justify-center rounded-full bg-white/80 text-subtle backdrop-blur-sm transition-colors hover:text-primary"
          onClick={e => { e.stopPropagation(); onToggleSave(brief.id) }}
          aria-label={brief.isSaved ? 'Unsave brief' : 'Save brief'}
        >
          {brief.isSaved ? (
            <BookmarkCheck className="h-3.5 w-3.5 text-primary" />
          ) : (
            <Bookmark className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* ── Card body ──────────────────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col gap-3 p-4">

        {/* Title */}
        <div className="flex-1">
          <h3 className="font-serif text-[15px] font-normal leading-snug text-heading line-clamp-2 group-hover:text-primary transition-colors">
            {brief.title}
          </h3>
          {brief.subtitle && (
            <p className="mt-0.5 text-xs text-subtle line-clamp-1">{brief.subtitle}</p>
          )}
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-1">
          {brief.tags.slice(0, 3).map(tag => (
            <span
              key={tag}
              className="rounded-pill bg-muted px-2 py-0.5 text-[10px] text-data"
            >
              {tag}
            </span>
          ))}
          {brief.tags.length > 3 && (
            <span className="rounded-pill bg-muted px-2 py-0.5 text-[10px] text-subtle">
              +{brief.tags.length - 3}
            </span>
          )}
        </div>

        {/* Footer row */}
        <div className="flex items-center justify-between border-t border-border pt-3">
          <div className="flex items-center gap-2 text-[11px] text-subtle">
            <span>{brief.relativeDate}</span>
            <span className="text-border">·</span>
            <span className="flex items-center gap-0.5">
              <Clock className="h-3 w-3" />
              {brief.readTimeMinutes}m
            </span>
            <span className="text-border">·</span>
            <span>{brief.author}</span>
          </div>
          <ConfidencePill score={brief.confidence} />
        </div>
      </div>

      {/* ── Hover CTA strip ─────────────────────────────────────────────────── */}
      <div
        className={`flex items-center justify-between bg-primary/5 px-4 py-2.5 text-xs font-medium text-primary transition-all duration-200 ${hovered ? 'opacity-100 max-h-10' : 'opacity-0 max-h-0 overflow-hidden'}`}
        aria-hidden={!hovered}
      >
        <span>Open full brief</span>
        <ChevronRight className="h-3.5 w-3.5" />
      </div>
    </article>
  )
}
