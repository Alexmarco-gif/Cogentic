'use client'

import { cn } from '@/lib/utils'
import {
  Brain,
  FileSearch,
  GitFork,
  BarChart2,
  Sparkles,
  MessageSquare,
} from 'lucide-react'
import { ProcessTracker }      from './ProcessTracker'
import { CitationsView }       from './CitationsView'
import { EntityGraph }         from './EntityGraph'
import { VisualizationChart }  from './VisualizationChart'
import type {
  EvidenceState,
  ProcessStep,
  Citation,
  GraphNode,
  GraphEdge,
  EvidencePackage,
} from '@/lib/hooks/useInvestigate'
import type { ReactNode } from 'react'
import { ScrollArea } from '@/components/ui'
import { INVESTIGATE_SUGGESTIONS } from '@/lib/hooks/useInvestigate'

// ── State config ──────────────────────────────────────────────────────────────
const STATE_CONFIG: Record<EvidenceState, {
  label: string
  icon: ReactNode
  description: string
}> = {
  idle: {
    label: 'Evidence Board',
    icon: <Sparkles size={13} />,
    description: 'Ask a question to populate this panel',
  },
  thinking: {
    label: 'Processing',
    icon: <Brain size={13} className="animate-pulse" />,
    description: 'Cogent is analyzing your query',
  },
  citations: {
    label: 'Source Documents',
    icon: <FileSearch size={13} />,
    description: 'Referenced intelligence sources',
  },
  graph: {
    label: 'Entity Relationships',
    icon: <GitFork size={13} />,
    description: 'Relationship map for queried entities',
  },
  visualization: {
    label: 'Data Visualization',
    icon: <BarChart2 size={13} />,
    description: 'Chart derived from correlated signals',
  },
}

interface EvidenceBoardProps {
  state: EvidenceState
  processSteps: ProcessStep[]
  citations: Citation[]
  graphNodes: GraphNode[]
  graphEdges: GraphEdge[]
  evidencePackage: EvidencePackage
  onSuggestionClick: (text: string) => void
}

// ── Shared inline markdown renderer for evidence report ───────────────────────
function ReportMarkdown({ markdown }: { markdown: string }) {
  if (!markdown) return null
  const lines = markdown.split('\n')
  return (
    <div className="space-y-1.5 text-[12.5px] leading-relaxed">
      {lines.map((line, i) => {
        if (!line.trim()) return <div key={i} className="h-1" />
        if (line.startsWith('### ')) {
          return (
            <p key={i} className="text-[11px] font-semibold uppercase tracking-widest text-subtle pt-2 pb-0.5">
              {line.replace('### ', '')}
            </p>
          )
        }
        if (line.startsWith('> ')) {
          return (
            <div key={i} className="border-l-2 border-primary/30 pl-3 py-0.5 bg-primary/5 rounded-r text-[12px] text-body">
              {line.replace(/^> \*\*(.+?)\*\*/, (_, t) => t).replace(/^> /, '')}
            </div>
          )
        }
        if (line.startsWith('---')) {
          return <hr key={i} className="border-border my-1" />
        }
        // Replace **bold**
        const parts = line.split(/(\*\*[^*]+\*\*)/g)
        return (
          <p key={i} className="text-body">
            {parts.map((part, j) =>
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={j} className="font-semibold text-heading">{part.slice(2, -2)}</strong>
                : <span key={j}>{part}</span>
            )}
          </p>
        )
      })}
    </div>
  )
}

// ── Report panel shown above evidence content ────────────────────────────────
function EvidenceReportSection({ markdown }: { markdown: string }) {
  if (!markdown) return null
  return (
    <div className="bg-surface border border-border rounded-xl p-4 mb-4">
      <ReportMarkdown markdown={markdown} />
    </div>
  )
}

export function EvidenceBoard({
  state,
  processSteps,
  citations,
  graphNodes,
  graphEdges,
  evidencePackage,
  onSuggestionClick,
}: EvidenceBoardProps) {
  const cfg = STATE_CONFIG[state]

  return (
    <div className="flex flex-col h-full bg-canvas">
      {/* ── Header bar ────────────────────────────────── */}
      <div className="flex items-center gap-2.5 px-5 py-3.5 border-b border-border bg-surface shrink-0">
        <span className={cn(
          'w-6 h-6 rounded-lg flex items-center justify-center text-xs',
          state === 'idle'          && 'bg-muted        text-subtle',
          state === 'thinking'     && 'bg-primary/10   text-primary',
          state === 'citations'    && 'bg-blue-50       text-blue-600',
          state === 'graph'        && 'bg-violet-50     text-violet-600',
          state === 'visualization'&& 'bg-emerald-50   text-emerald-600',
        )}>
          {cfg.icon}
        </span>
        <div>
          <p className="text-[12px] font-medium text-heading">{cfg.label}</p>
          <p className="text-[10px] text-subtle">{cfg.description}</p>
        </div>

        {/* State pill */}
        {state !== 'idle' && (
          <span className={cn(
            'ml-auto text-[10px] font-medium px-2 py-0.5 rounded-full border',
            state === 'thinking'      && 'bg-primary/5    text-primary    border-primary/20  animate-pulse',
            state === 'citations'     && 'bg-blue-50       text-blue-700   border-blue-200',
            state === 'graph'         && 'bg-violet-50     text-violet-700 border-violet-200',
            state === 'visualization' && 'bg-emerald-50   text-emerald-700 border-emerald-200',
          )}>
            {state === 'thinking'      && '● Analyzing…'}
            {state === 'citations'     && `${citations.length} sources`}
            {state === 'graph'         && `${graphNodes.length} nodes`}
            {state === 'visualization' && `${evidencePackage.charts.length} charts`}
          </span>
        )}
      </div>

      {/* ── Content ───────────────────────────────────── */}
      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="p-5">

          {/* ── IDLE: Suggestion grid ─────────────────── */}
          {state === 'idle' && (
            <div className="h-full flex flex-col items-center justify-center py-8">
              <div className="w-10 h-10 rounded-2xl bg-primary/5 border border-primary/10 flex items-center justify-center mb-4">
                <MessageSquare size={18} className="text-primary" />
              </div>
              <p className="text-[13px] font-medium text-heading mb-1.5">War Room Intelligence</p>
              <p className="text-[12px] text-subtle text-center max-w-[260px] mb-6 leading-relaxed">
                Ask about any entity, market signal, or policy event across your monitored domains.
              </p>
              <div className="w-full grid grid-cols-1 gap-2">
                {INVESTIGATE_SUGGESTIONS.map(s => (
                  <button
                    key={s.label}
                    onClick={() => onSuggestionClick(s.label)}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border bg-surface
                               hover:bg-muted hover:border-primary/20 transition-colors text-left group"
                  >
                    <span className="text-[10px] font-semibold bg-primary/5 text-primary border border-primary/10 px-1.5 py-0.5 rounded-full shrink-0">
                      {s.tag}
                    </span>
                    <span className="text-[12px] text-body group-hover:text-heading transition-colors leading-snug">
                      {s.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── THINKING: Process tracker ─────────────── */}
          {state === 'thinking' && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-subtle mb-3">
                Intelligence Retrieval
              </p>
              <ProcessTracker steps={processSteps} />
            </div>
          )}

          {/* ── CITATIONS: Report + Source documents ──── */}
          {state === 'citations' && (
            <div>
              <EvidenceReportSection markdown={evidencePackage.citationsNarrative} />
              <p className="text-[11px] font-semibold uppercase tracking-widest text-subtle mb-3">
                Referenced Sources
              </p>
              <CitationsView citations={citations} />
            </div>
          )}

          {/* ── GRAPH: Report + Entity relationships ───── */}
          {state === 'graph' && (
            <div>
              <EvidenceReportSection markdown={evidencePackage.graphNarrative} />
              <p className="text-[11px] font-semibold uppercase tracking-widest text-subtle mb-3">
                Entity Relationship Map
              </p>
              <EntityGraph nodes={graphNodes} edges={graphEdges} />
            </div>
          )}

          {/* ── VISUALIZATION: Report + Charts ────────── */}
          {state === 'visualization' && (
            <div>
              <EvidenceReportSection markdown={evidencePackage.reportMarkdown} />
              <p className="text-[11px] font-semibold uppercase tracking-widest text-subtle mb-3">
                Correlated Signal Analysis
              </p>
              <VisualizationChart charts={evidencePackage.charts} />
            </div>
          )}

        </div>
      </ScrollArea>
    </div>
  )
}
