'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useInvestigate } from '@/lib/hooks/useInvestigate'
import { ChatInterface } from '@/components/investigate/ChatInterface'
import { EvidenceBoard } from '@/components/investigate/EvidenceBoard'

function InvestigateInner() {
  const searchParams = useSearchParams()
  const initialQuery = searchParams.get('q') ?? undefined
  const initialIndustrySlug =
    searchParams.get('industry')
    ?? searchParams.get('industry_slug')
    ?? undefined
  const initialSessionId = searchParams.get('session') ?? undefined

  const {
    messages,
    evidenceState,
    processSteps,
    citations,
    recommendations,
    graphNodes,
    graphEdges,
    evidencePackage,
    isProcessing,
    isRestoringSession,
    industries,
    industriesLoading,
    industriesError,
    selectedIndustrySlug,
    sessionTitle,
    sendMessage,
    stopStreaming,
    clearConversation,
    setSelectedIndustrySlug,
  } = useInvestigate({
    initialQuery,
    initialIndustrySlug,
    initialSessionId,
  })

  const selectedIndustry = industries.find((industry) => industry.slug === selectedIndustrySlug)

  return (
    <div className="flex h-[calc(100vh-var(--omnibar-height))] min-h-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-border bg-surface/95 backdrop-blur">
        <div className="flex flex-col gap-3 px-4 py-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-1">
            <p className="text-[13px] font-semibold text-heading">Investigate</p>
            <p className="text-[12px] text-subtle">
              Run a live investigation, keep the active thread, and review structured evidence when the backend returns it.
            </p>
            {(sessionTitle || isRestoringSession) && (
              <p className="text-[11px] text-subtle">
                {isRestoringSession
                  ? 'Restoring your latest investigation thread...'
                  : `Active thread: ${sessionTitle ?? 'Untitled investigation'}`}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <label className="text-[11px] font-medium text-subtle" htmlFor="investigate-industry">
              Industry scope
            </label>
            <select
              id="investigate-industry"
              value={selectedIndustrySlug}
              onChange={(event) => setSelectedIndustrySlug(event.target.value)}
              disabled={industriesLoading || isProcessing}
              className="min-w-[220px] rounded-lg border border-border bg-canvas px-3 py-2 text-[12px] text-body outline-none transition-colors focus:border-primary/40 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <option value="">All monitored industries</option>
              {industries.map((industry) => (
                <option key={industry.id} value={industry.slug}>
                  {industry.name}
                </option>
              ))}
            </select>
            {selectedIndustry && (
              <span className="rounded-full border border-primary/15 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary">
                {selectedIndustry.name}
              </span>
            )}
          </div>
        </div>
        {industriesError && (
          <div className="px-4 pb-3 text-[11px] text-amber-700">
            {industriesError}
          </div>
        )}
      </div>

      <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
        <div className="min-h-[44vh] w-full border-b border-border xl:min-h-0 xl:w-[40%] xl:min-w-[320px] xl:max-w-[520px] xl:border-b-0 xl:border-r">
          <ChatInterface
            messages={messages}
            isProcessing={isProcessing}
            sessionTitle={sessionTitle}
            onSend={sendMessage}
            onStop={stopStreaming}
            onClear={clearConversation}
            onSuggestionClick={sendMessage}
          />
        </div>

        <div className="min-h-0 flex-1">
          <EvidenceBoard
            state={evidenceState}
            processSteps={processSteps}
            citations={citations}
            recommendations={recommendations}
            graphNodes={graphNodes}
            graphEdges={graphEdges}
            evidencePackage={evidencePackage}
            onSuggestionClick={sendMessage}
          />
        </div>
      </div>
    </div>
  )
}

export default function InvestigatePage() {
  return (
    <Suspense fallback={(
      <div className="flex h-full items-center justify-center text-sm text-subtle">
        Loading...
      </div>
    )}>
      <InvestigateInner />
    </Suspense>
  )
}
