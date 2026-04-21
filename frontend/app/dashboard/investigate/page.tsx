'use client'

import { Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { ArrowRight, Search, Sparkles } from 'lucide-react'
import { useInvestigate } from '@/lib/hooks/useInvestigate'
import { ChatInterface } from '@/components/investigate/ChatInterface'
import { EvidenceBoard } from '@/components/investigate/EvidenceBoard'

function InvestigateInner() {
  const router = useRouter()
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
    <div
      data-onboarding="investigate-page"
      className="flex min-h-[calc(100vh-var(--omnibar-height))] flex-col gap-4 px-3 py-4 sm:px-4 lg:px-0"
    >
      <div
        data-onboarding="investigate-header"
        className="surface-panel shrink-0 overflow-hidden border border-border/80 bg-surface/95 backdrop-blur"
      >
        <div className="flex flex-col gap-4 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">
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

          <div className="flex flex-col gap-2 sm:max-w-[24rem] sm:min-w-[18rem]">
            <label className="text-[11px] font-medium text-subtle" htmlFor="investigate-industry">
              Industry scope
            </label>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <select
                data-onboarding="investigate-scope"
                id="investigate-industry"
                value={selectedIndustrySlug}
                onChange={(event) => setSelectedIndustrySlug(event.target.value)}
                disabled={industriesLoading || isProcessing}
                className="min-w-0 flex-1 rounded-xl border border-border bg-canvas px-3 py-2.5 text-[12px] text-body outline-none transition-colors focus:border-primary/40 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <option value="">All monitored industries</option>
                {industries.map((industry) => (
                  <option key={industry.id} value={industry.slug}>
                    {industry.name}
                  </option>
                ))}
              </select>
              {selectedIndustry && (
                <span className="inline-flex rounded-full border border-primary/15 bg-primary/5 px-2.5 py-1 text-[10px] font-medium text-primary">
                  {selectedIndustry.name}
                </span>
              )}
            </div>
          </div>
        </div>
      {industriesError && (
        <div className="px-5 pb-4 text-[11px] text-amber-700">
          {industriesError}
        </div>
      )}
      </div>

      {!isRestoringSession && messages.length === 0 && (
        <div className="surface-panel border border-border/80 bg-surface/95 p-5">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-2xl">
              <p className="eyebrow">Best results</p>
              <h2 className="mt-2 text-title">Investigate works best once live signals are already flowing.</h2>
              <p className="mt-2 text-[0.82rem] text-subtle">
                Use this workspace to ask follow-up questions about monitored entities, policy shifts, competitors, or market events. If your workspace is still empty, define monitoring in Studio or activate managed sources first so the backend has real evidence to work with.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => router.push('/dashboard/signals')}
                className="button-press inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-[0.82rem] font-semibold text-white shadow-glow transition-all duration-200 hover:-translate-y-0.5 hover:bg-primary-hover"
              >
                <Search size={14} />
                Open signals
              </button>
              <button
                onClick={() => router.push('/dashboard/studio')}
                className="button-press inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-2.5 text-[0.82rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
              >
                <Sparkles size={14} />
                Create contract
              </button>
              <button
                onClick={() => router.push('/dashboard/marketplace')}
                className="button-press inline-flex items-center gap-2 rounded-full border border-border bg-surface px-5 py-2.5 text-[0.82rem] font-semibold text-heading transition-all duration-200 hover:-translate-y-0.5 hover:border-border-hover hover:bg-surface-2"
              >
                Browse sources
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid min-h-0 flex-1 gap-4 xl:grid-cols-[minmax(24rem,0.92fr)_minmax(0,1.18fr)]">
        <div
          data-onboarding="investigate-chat"
          className="min-h-[34rem] overflow-hidden rounded-[28px] border border-border bg-surface shadow-card"
        >
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

        <div
          data-onboarding="investigate-evidence"
          className="min-h-[34rem] overflow-hidden rounded-[28px] border border-border bg-canvas shadow-card"
        >
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
