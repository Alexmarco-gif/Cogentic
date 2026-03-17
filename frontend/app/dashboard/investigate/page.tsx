'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useInvestigate } from '@/lib/hooks/useInvestigate'
import { ChatInterface }  from '@/components/investigate/ChatInterface'
import { EvidenceBoard }  from '@/components/investigate/EvidenceBoard'

function InvestigateInner() {
  const searchParams = useSearchParams()
  const initialQuery = searchParams.get('q') ?? undefined

  const {
    messages,
    evidenceState,
    processSteps,
    citations,
    graphNodes,
    graphEdges,
    evidencePackage,
    isProcessing,
    sendMessage,
    clearConversation,
  } = useInvestigate(initialQuery)

  return (
    // Full-height split: 40% chat / 60% evidence board
    // Use viewport calc so the pane fills the space below OmniBar
    <div
      className="flex overflow-hidden"
      style={{ height: 'calc(100vh - var(--omnibar-height))' }}
    >
      {/* ── Left pane: Chat (40%) ─────────────────────── */}
      <div className="w-[40%] min-w-[320px] max-w-[520px] flex flex-col h-full">
        <ChatInterface
          messages={messages}
          isProcessing={isProcessing}
          onSend={sendMessage}
          onClear={clearConversation}
          onSuggestionClick={sendMessage}
        />
      </div>

      {/* ── Right pane: Evidence board (60%) ─────────── */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <EvidenceBoard
          state={evidenceState}
          processSteps={processSteps}
          citations={citations}
          graphNodes={graphNodes}
          graphEdges={graphEdges}
          evidencePackage={evidencePackage}
          onSuggestionClick={sendMessage}
        />
      </div>
    </div>
  )
}

export default function InvestigatePage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-full text-subtle text-sm">
        Loading…
      </div>
    }>
      <InvestigateInner />
    </Suspense>
  )
}
