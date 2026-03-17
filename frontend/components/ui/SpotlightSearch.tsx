'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import {
  Search, Home, Activity, Globe, BookOpen, Sparkles,
  Clock, ArrowRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface SpotlightResult {
  type: 'nav' | 'recent' | 'ai'
  label: string
  description?: string
  href?: string
  icon: React.ReactNode
}

interface SpotlightSearchProps {
  query: string
  onClose: () => void
  onNavigate?: (href: string) => void
}

// ─── Static nav quick-links ───────────────────────────────────────────────────

const NAV_LINKS: SpotlightResult[] = [
  { type: 'nav', label: 'Home',        description: 'Intelligence Feed',     href: '/dashboard/home',       icon: <Home      size={15} strokeWidth={1.5} /> },
  { type: 'nav', label: 'Investigate', description: 'AI War Room',           href: '/dashboard/investigate', icon: <Search    size={15} strokeWidth={1.5} /> },
  { type: 'nav', label: 'Signals',     description: 'Data Grid',             href: '/dashboard/signals',     icon: <Activity  size={15} strokeWidth={1.5} /> },
  { type: 'nav', label: 'Domains',     description: 'Geo Intelligence Map',  href: '/dashboard/domains',     icon: <Globe     size={15} strokeWidth={1.5} /> },
  { type: 'nav', label: 'Library',     description: 'Institutional Memory',  href: '/dashboard/library',     icon: <BookOpen  size={15} strokeWidth={1.5} /> },
]

// ─── Component ────────────────────────────────────────────────────────────────

export function SpotlightSearch({ query, onClose, onNavigate }: SpotlightSearchProps) {
  const router = useRouter()
  const [activeIdx, setActiveIdx] = React.useState(0)

  // Filter nav links by query
  const filtered = query.trim()
    ? NAV_LINKS.filter(r =>
        r.label.toLowerCase().includes(query.toLowerCase()) ||
        r.description?.toLowerCase().includes(query.toLowerCase()),
      )
    : NAV_LINKS

  // AI suggestion row (always shown when query is non-empty)
  const aiSuggestion: SpotlightResult | null = query.trim()
    ? {
        type: 'ai',
        label: `Ask AI: "${query}"`,
        description: 'Investigate with Cogent Intelligence',
        href: `/dashboard/investigate?q=${encodeURIComponent(query)}`,
        icon: <Sparkles size={15} strokeWidth={1.5} />,
      }
    : null

  const results: SpotlightResult[] = aiSuggestion
    ? [aiSuggestion, ...filtered]
    : filtered

  // Keyboard navigation
  React.useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIdx(i => Math.min(i + 1, results.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIdx(i => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        const item = results[activeIdx]
        if (item?.href) {
          router.push(item.href)
          onClose()
        }
      } else if (e.key === 'Escape') {
        onClose()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [activeIdx, results, router, onClose])

  if (!results.length) return null

  return (
    <div
      className={cn(
        'absolute top-full left-0 right-0 mt-1 z-50',
        'bg-surface border border-border shadow-modal rounded-lg py-1.5',
        'animate-fade-up',
      )}
      role="listbox"
      aria-label="Search suggestions"
    >
      {/* Section header */}
      {!query.trim() && (
        <p className="px-4 pt-1 pb-2 text-[11px] font-medium uppercase tracking-wide text-subtle">
          Quick Navigation
        </p>
      )}

      {results.map((result, i) => (
        <button
          key={i}
          role="option"
          aria-selected={i === activeIdx}
          onClick={() => {
            if (result.href) {
              router.push(result.href)
              onNavigate?.(result.href)
              onClose()
            }
          }}
          onMouseEnter={() => setActiveIdx(i)}
          className={cn(
            'w-full flex items-center gap-3 px-4 py-2.5 text-left',
            'hover:bg-muted transition-colors',
            i === activeIdx && 'bg-muted',
          )}
        >
          {/* Icon */}
          <span className={cn(
            'w-7 h-7 rounded-lg flex items-center justify-center shrink-0',
            result.type === 'ai'
              ? 'bg-primary/10 text-primary'
              : 'bg-muted text-neutral',
          )}>
            {result.icon}
          </span>

          {/* Label + description */}
          <div className="flex-1 min-w-0">
            <p className={cn(
              'text-sm truncate',
              result.type === 'ai' ? 'text-primary font-medium' : 'text-body font-medium',
            )}>
              {result.label}
            </p>
            {result.description && (
              <p className="text-xs text-subtle truncate">{result.description}</p>
            )}
          </div>

          {/* Arrow */}
          <ArrowRight size={13} className="text-subtle shrink-0" aria-hidden="true" />
        </button>
      ))}

      {/* Footer hint */}
      <div className="px-4 pt-1.5 pb-1 border-t border-border mt-1 flex items-center gap-3 text-[11px] text-subtle">
        <span><kbd className="font-mono">↑↓</kbd> navigate</span>
        <span><kbd className="font-mono">↵</kbd> open</span>
        <span><kbd className="font-mono">Esc</kbd> close</span>
      </div>
    </div>
  )
}
