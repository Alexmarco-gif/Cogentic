'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import {
  Activity,
  ArrowRight,
  BookOpen,
  Command,
  Globe,
  Home,
  Search,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SpotlightResult {
  type: 'nav' | 'recent' | 'ai'
  label: string
  description?: string
  href?: string
  icon: React.ReactNode
  shortcut?: string
}

interface SpotlightSearchProps {
  query: string
  onClose: () => void
  onNavigate?: (href: string) => void
}

const NAV_LINKS: SpotlightResult[] = [
  { type: 'nav', label: 'Home', description: 'Executive overview and next actions', href: '/dashboard/home', icon: <Home size={15} strokeWidth={1.8} />, shortcut: 'H' },
  { type: 'nav', label: 'Investigate', description: 'Ask AI and build an investigation', href: '/dashboard/investigate', icon: <Search size={15} strokeWidth={1.8} />, shortcut: '/' },
  { type: 'nav', label: 'Signals', description: 'Track new risks and opportunities', href: '/dashboard/signals', icon: <Activity size={15} strokeWidth={1.8} />, shortcut: 'S' },
  { type: 'nav', label: 'Domains', description: 'See coverage across monitored markets', href: '/dashboard/domains', icon: <Globe size={15} strokeWidth={1.8} />, shortcut: 'D' },
  { type: 'nav', label: 'Library', description: 'Open saved briefs and exports', href: '/dashboard/library', icon: <BookOpen size={15} strokeWidth={1.8} />, shortcut: 'L' },
]

export function SpotlightSearch({ query, onClose, onNavigate }: SpotlightSearchProps) {
  const router = useRouter()
  const [activeIdx, setActiveIdx] = React.useState(0)

  const filtered = query.trim()
    ? NAV_LINKS.filter((item) => (
      item.label.toLowerCase().includes(query.toLowerCase())
      || item.description?.toLowerCase().includes(query.toLowerCase())
    ))
    : NAV_LINKS

  const aiSuggestion: SpotlightResult | null = query.trim()
    ? {
      type: 'ai',
      label: `Investigate "${query}"`,
      description: 'Open a focused AI workspace for this topic',
      href: `/dashboard/investigate?q=${encodeURIComponent(query)}`,
      icon: <Sparkles size={15} strokeWidth={1.8} />,
      shortcut: 'AI',
    }
    : null

  const createSuggestion: SpotlightResult = {
    type: 'recent',
    label: 'Create contract',
    description: 'Start a new monitoring workflow',
    href: '/dashboard/studio',
    icon: <Command size={15} strokeWidth={1.8} />,
    shortcut: 'C',
  }

  const results = [
    ...(aiSuggestion ? [aiSuggestion] : []),
    createSuggestion,
    ...filtered,
  ]

  React.useEffect(() => {
    setActiveIdx(0)
  }, [query])

  React.useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIdx((index) => Math.min(index + 1, results.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIdx((index) => Math.max(index - 1, 0))
      } else if (e.key === 'Enter') {
        const item = results[activeIdx]
        if (item?.href) {
          router.push(item.href)
          onNavigate?.(item.href)
          onClose()
        }
      } else if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [activeIdx, onClose, onNavigate, results, router])

  if (!results.length) {
    return null
  }

  return (
    <div
      id="spotlight-results"
      className="surface-elevated absolute left-0 right-0 top-full z-50 mt-3 overflow-hidden p-2 animate-fade-up"
      role="listbox"
      aria-label="Search suggestions"
    >
      <div className="rounded-[20px] bg-surface-2 px-4 py-3">
        <p className="text-[0.76rem] font-semibold uppercase tracking-[0.18em] text-subtle">
          {query.trim() ? 'Suggested actions' : 'Quick navigation'}
        </p>
      </div>

      <div className="mt-2 space-y-1">
        {results.map((result, index) => (
          <button
            key={`${result.label}-${index}`}
            role="option"
            aria-selected={index === activeIdx}
            onClick={() => {
              if (result.href) {
                router.push(result.href)
                onNavigate?.(result.href)
                onClose()
              }
            }}
            onMouseEnter={() => setActiveIdx(index)}
            className={cn(
              'button-press flex w-full items-center gap-3 rounded-[20px] px-4 py-3 text-left transition-all duration-200',
              index === activeIdx
                ? 'bg-primary/[0.08] text-primary'
                : 'hover:bg-surface-2',
            )}
          >
            <span className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl',
              result.type === 'ai'
                ? 'bg-primary text-white shadow-glow'
                : result.type === 'recent'
                ? 'bg-surface text-heading'
                : 'bg-surface-2 text-neutral',
            )}>
              {result.icon}
            </span>

            <div className="min-w-0 flex-1">
              <p className={cn(
                'truncate text-[0.88rem] font-semibold',
                result.type === 'ai' ? 'text-primary' : 'text-heading',
              )}>
                {result.label}
              </p>
              {result.description && (
                <p className="truncate text-[0.78rem] text-subtle">{result.description}</p>
              )}
            </div>

            {result.shortcut && (
              <span className="rounded-full border border-border bg-surface px-2 py-1 text-[0.66rem] font-semibold uppercase tracking-[0.16em] text-subtle">
                {result.shortcut}
              </span>
            )}

            <ArrowRight size={14} className="shrink-0 text-subtle" aria-hidden="true" />
          </button>
        ))}
      </div>

      <div className="mt-2 flex items-center gap-3 border-t border-border px-4 pt-3 text-[0.72rem] text-subtle">
        <span><kbd className="font-mono">↑↓</kbd> move</span>
        <span><kbd className="font-mono">Enter</kbd> open</span>
        <span><kbd className="font-mono">Esc</kbd> close</span>
      </div>
    </div>
  )
}
