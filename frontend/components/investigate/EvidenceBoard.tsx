'use client'

import { cn } from '@/lib/utils'
import {
  Brain,
  FileSearch,
  GitFork,
  BarChart2,
  Sparkles,
  MessageSquare,
  Compass,
} from 'lucide-react'
import { ProcessTracker } from './ProcessTracker'
import { CitationsView } from './CitationsView'
import { EntityGraph } from './EntityGraph'
import { VisualizationChart } from './VisualizationChart'
import type {
  EvidenceState,
  ProcessStep,
  Citation,
  Recommendation,
  GraphNode,
  GraphEdge,
  EvidencePackage,
} from '@/lib/hooks/useInvestigate'
import type { ReactNode } from 'react'
import { ScrollArea } from '@/components/ui'
import { INVESTIGATE_SUGGESTIONS } from '@/lib/hooks/useInvestigate'

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
    description: 'Referenced intelligence sources and actions',
  },
  graph: {
    label: 'Entity Relationships',
    icon: <GitFork size={13} />,
    description: 'Relationship map for queried entities',
  },
  visualization: {
    label: 'Data Visualization',
    icon: <BarChart2 size={13} />,
    description: 'Charts derived from correlated signals',
  },
}

interface EvidenceBoardProps {
  state: EvidenceState
  processSteps: ProcessStep[]
  citations: Citation[]
  recommendations: Recommendation[]
  graphNodes: GraphNode[]
  graphEdges: GraphEdge[]
  evidencePackage: EvidencePackage
  onSuggestionClick: (text: string) => void
}

function ReportMarkdown({ markdown }: { markdown: string }) {
  if (!markdown) return null
  const lines = markdown.split('\n')

  return (
    <div className="space-y-1.5 text-[12.5px] leading-relaxed">
      {lines.map((line, index) => {
        if (!line.trim()) return <div key={index} className="h-1" />

        if (line.startsWith('### ')) {
          return (
            <p key={index} className="pb-0.5 pt-2 text-[11px] font-semibold uppercase tracking-widest text-subtle">
              {line.replace('### ', '')}
            </p>
          )
        }

        if (line.startsWith('> ')) {
          return (
            <div key={index} className="rounded-r border-l-2 border-primary/30 bg-primary/5 py-0.5 pl-3 text-[12px] text-body">
              {line.replace(/^> \*\*(.+?)\*\*/, (_, title) => title).replace(/^> /, '')}
            </div>
          )
        }

        if (line.startsWith('---')) {
          return <hr key={index} className="my-1 border-border" />
        }

        const parts = line.split(/(\*\*[^*]+\*\*)/g)
        return (
          <p key={index} className="text-body">
            {parts.map((part, partIndex) => (
              part.startsWith('**') && part.endsWith('**')
                ? <strong key={partIndex} className="font-semibold text-heading">{part.slice(2, -2)}</strong>
                : <span key={partIndex}>{part}</span>
            ))}
          </p>
        )
      })}
    </div>
  )
}

function EvidenceReportSection({ markdown }: { markdown: string }) {
  if (!markdown) return null
  return (
    <div className="mb-4 rounded-xl border border-border bg-surface p-4">
      <ReportMarkdown markdown={markdown} />
    </div>
  )
}

function RecommendationsSection({ recommendations }: { recommendations: Recommendation[] }) {
  if (!recommendations.length) return null

  return (
    <div className="mb-5">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-subtle">
        Recommended Actions
      </p>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {recommendations.map((recommendation) => (
          <div key={recommendation.id} className="rounded-xl border border-border bg-surface p-4">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[12px] font-semibold text-heading">{recommendation.title}</p>
                <p className="text-[10px] uppercase tracking-widest text-subtle">
                  {recommendation.recommendationType.replace(/_/g, ' ')}
                </p>
              </div>
              <span className="shrink-0 rounded-full border border-primary/15 bg-primary/5 px-2 py-0.5 text-[10px] font-medium text-primary">
                {recommendation.confidence !== null ? `${Math.round(recommendation.confidence * 100)}%` : 'Suggested'}
              </span>
            </div>
            <p className="text-[12px] leading-relaxed text-body">{recommendation.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function EmptyEvidenceState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border bg-surface px-4 py-6 text-[12px] text-subtle">
      {message}
    </div>
  )
}

export function EvidenceBoard({
  state,
  processSteps,
  citations,
  recommendations,
  graphNodes,
  graphEdges,
  evidencePackage,
  onSuggestionClick,
}: EvidenceBoardProps) {
  const cfg = STATE_CONFIG[state]

  return (
    <div className="flex h-full flex-col bg-canvas">
      <div className="flex shrink-0 items-center gap-2.5 border-b border-border bg-surface px-5 py-3.5">
        <span
          className={cn(
            'flex h-6 w-6 items-center justify-center rounded-lg text-xs',
            state === 'idle' && 'bg-muted text-subtle',
            state === 'thinking' && 'bg-primary/10 text-primary',
            state === 'citations' && 'bg-blue-50 text-blue-600',
            state === 'graph' && 'bg-violet-50 text-violet-600',
            state === 'visualization' && 'bg-emerald-50 text-emerald-600',
          )}
        >
          {cfg.icon}
        </span>
        <div>
          <p className="text-[12px] font-medium text-heading">{cfg.label}</p>
          <p className="text-[10px] text-subtle">{cfg.description}</p>
        </div>

        {state !== 'idle' && (
          <span
            className={cn(
              'ml-auto rounded-full border px-2 py-0.5 text-[10px] font-medium',
              state === 'thinking' && 'animate-pulse border-primary/20 bg-primary/5 text-primary',
              state === 'citations' && 'border-blue-200 bg-blue-50 text-blue-700',
              state === 'graph' && 'border-violet-200 bg-violet-50 text-violet-700',
              state === 'visualization' && 'border-emerald-200 bg-emerald-50 text-emerald-700',
            )}
          >
            {state === 'thinking' && 'Analyzing...'}
            {state === 'citations' && `${citations.length} sources`}
            {state === 'graph' && `${graphNodes.length} nodes`}
            {state === 'visualization' && `${evidencePackage.charts.length} charts`}
          </span>
        )}
      </div>

      <ScrollArea className="flex-1 overflow-y-auto">
        <div className="p-5">
          {state === 'idle' && (
            <div className="flex h-full flex-col items-center justify-center py-8">
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-2xl border border-primary/10 bg-primary/5">
                <MessageSquare size={18} className="text-primary" />
              </div>
              <p className="mb-1.5 text-[13px] font-medium text-heading">War Room Intelligence</p>
              <p className="mb-6 max-w-[260px] text-center text-[12px] leading-relaxed text-subtle">
                Ask about any entity, market signal, or policy event across your monitored domains.
              </p>
              <div className="grid w-full grid-cols-1 gap-2">
                {INVESTIGATE_SUGGESTIONS.map((suggestion) => (
                  <button
                    key={suggestion.label}
                    onClick={() => onSuggestionClick(suggestion.label)}
                    className="group flex items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2.5 text-left transition-colors hover:border-primary/20 hover:bg-muted"
                  >
                    <span className="shrink-0 rounded-full border border-primary/10 bg-primary/5 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                      {suggestion.tag}
                    </span>
                    <span className="text-[12px] leading-snug text-body transition-colors group-hover:text-heading">
                      {suggestion.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {state === 'thinking' && (
            <div>
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                Investigation Progress
              </p>
              <ProcessTracker steps={processSteps} />
            </div>
          )}

          {state === 'citations' && (
            <div>
              <EvidenceReportSection markdown={evidencePackage.citationsNarrative} />
              <RecommendationsSection recommendations={recommendations} />
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                Referenced Sources
              </p>
              {citations.length > 0 ? (
                <CitationsView citations={citations} />
              ) : (
                <EmptyEvidenceState message="This investigation finished without source cards. Review the chat response for the full narrative, or retry with a more specific company, policy, or metric question." />
              )}
            </div>
          )}

          {state === 'graph' && (
            <div>
              <EvidenceReportSection markdown={evidencePackage.graphNarrative} />
              {recommendations.length > 0 && <RecommendationsSection recommendations={recommendations} />}
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                Entity Relationship Map
              </p>
              {graphNodes.length > 0 ? (
                <EntityGraph nodes={graphNodes} edges={graphEdges} />
              ) : (
                <EmptyEvidenceState message="No relationship graph was returned for this run. Cogent will show a graph here when the backend includes structured relationship data." />
              )}
            </div>
          )}

          {state === 'visualization' && (
            <div>
              <EvidenceReportSection markdown={evidencePackage.reportMarkdown} />
              {recommendations.length > 0 && <RecommendationsSection recommendations={recommendations} />}
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-subtle">
                Correlated Signal Analysis
              </p>
              {evidencePackage.charts.length > 0 ? (
                <VisualizationChart charts={evidencePackage.charts} />
              ) : (
                <EmptyEvidenceState message="No chart package was returned for this investigation. Cogent will render charts here when the backend includes structured analytics data." />
              )}
            </div>
          )}

          {state !== 'idle' && state !== 'thinking' && recommendations.length === 0 && citations.length === 0 && !evidencePackage.citationsNarrative && (
            <div className="mt-5 flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-[11px] text-subtle">
              <Compass size={13} className="text-primary" />
              Continue the investigation from the chat pane to gather more specific evidence.
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
