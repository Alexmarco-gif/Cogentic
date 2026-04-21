'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { createChatSession, sendChatMessage, archiveChatSession, listChatSessions, getChatSession } from '@/lib/api/chat'
import { getIndustries, type IndustryItem } from '@/lib/api/discovered_sources'
import type { ChatMessageResponse, ChatSessionDetailResponse } from '@/lib/api/types'

export type EvidenceState = 'idle' | 'thinking' | 'citations' | 'graph' | 'visualization'

export type StepStatus = 'pending' | 'active' | 'complete'

export interface ProcessStep {
  id: string
  label: string
  status: StepStatus
}

export interface Citation {
  id: string
  index: number
  sourceTitle: string
  sourceName: string
  publishedAt: string
  excerpt: string
  highlight: string
  url: string
  relevance: 'high' | 'medium' | 'low'
}

export interface Recommendation {
  id: string
  title: string
  description: string
  recommendationType: string
  confidence: number | null
}

export interface GraphNode {
  id: string
  label: string
  sublabel?: string
  type: 'company' | 'regulator' | 'market' | 'event'
  x: number
  y: number
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  label: string
}

export interface ChartSeries {
  key: string
  label: string
  color: string
  type: 'line' | 'area' | 'bar'
  yAxisId?: 'left' | 'right'
  dashed?: boolean
}

export interface ChartDefinition {
  id: string
  title: string
  subtitle: string
  leftLabel: string
  rightLabel?: string
  unit: string
  data: Record<string, string | number>[]
  series: ChartSeries[]
  insight: string
}

export interface EvidencePackage {
  charts: ChartDefinition[]
  reportMarkdown: string
  graphNarrative: string
  citationsNarrative: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
}

export interface VisualizationPoint { date: string; value: number; baseline?: number }
export interface Visualization {
  title: string; subtitle: string
  primaryLabel: string; secondaryLabel: string
  primaryColor: string; secondaryColor: string
  data: VisualizationPoint[]
}

interface UseInvestigateOptions {
  initialQuery?: string
  initialIndustrySlug?: string
  initialSessionId?: string
}

interface HydratedInvestigateSession {
  evidenceState: EvidenceState
  evidencePackage: EvidencePackage
  messages: Message[]
  citations: Citation[]
}

interface DeriveEvidenceStateOptions {
  evidencePackage: EvidencePackage
  preferredState: EvidenceState
  citations: Citation[]
  graphNodes: GraphNode[]
  recommendations: Recommendation[]
  hasConversation: boolean
}

const DEFAULT_PACKAGE: EvidencePackage = {
  charts: [],
  reportMarkdown: '',
  graphNarrative: '',
  citationsNarrative: '',
}

const DEFAULT_PROCESS_STEPS: ProcessStep[] = [
  { id: 'session', label: 'Preparing investigation session', status: 'active' },
  { id: 'reasoning', label: 'Analyzing request', status: 'pending' },
  { id: 'tools', label: 'Running intelligence tools', status: 'pending' },
  { id: 'answer', label: 'Preparing answer', status: 'pending' },
]

function cloneDefaultPackage(): EvidencePackage {
  return {
    charts: [],
    reportMarkdown: '',
    graphNarrative: '',
    citationsNarrative: '',
  }
}

function cloneProcessSteps(): ProcessStep[] {
  return DEFAULT_PROCESS_STEPS.map((step) => ({ ...step }))
}

function detectEvidenceState(query: string): EvidenceState {
  const q = query.toLowerCase()
  if (
    q.includes('graph') || q.includes('relationship') ||
    q.includes('connection') || q.includes('network') ||
    q.includes('entity') || q.includes('who is') ||
    q.includes('linked')
  ) return 'graph'
  if (
    q.includes('chart') || q.includes('compare') ||
    q.includes('trend') || q.includes('vs') ||
    q.includes('growth') || q.includes('price') ||
    q.includes('performance') || q.includes('metric') ||
    q.includes('data') || q.includes('quarter') ||
    q.includes('annual')
  ) return 'visualization'
  return 'citations'
}

function buildFallbackResponse(query: string): string {
  return `### Analysis

I completed the investigation for **"${query}"**, but Cogent could not recover structured evidence cards for this run.

- Review the answer in the chat thread for the full narrative
- Re-run the query after your signal contracts ingest fresh data if you need source cards
- Narrow the question to a single company, policy event, or market theme for more precise retrieval

> Structured citations, relationship maps, and charts appear here whenever the backend returns them for the investigation.
`.trim()
}

function buildEvidenceFallbackNote(hasConversation: boolean): string {
  if (!hasConversation) return ''
  return '> This run completed without structured evidence cards from the backend. The full analysis is available in the chat thread on the left.'
}

function buildRecommendationsNarrative(recommendations: Recommendation[]): string {
  if (!recommendations.length) return ''

  const lines = recommendations.slice(0, 4).map((recommendation, index) => (
    `${index + 1}. **${recommendation.title}**: ${recommendation.description}`
  ))

  return [
    '### Recommended Actions',
    '',
    ...lines,
  ].join('\n')
}

function humanizeToolName(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

function updateProcessStep(
  steps: ProcessStep[],
  stepId: ProcessStep['id'],
  label: string,
): ProcessStep[] {
  const order = DEFAULT_PROCESS_STEPS.map((step) => step.id)
  const targetIndex = order.indexOf(stepId)
  if (targetIndex === -1) return steps

  return steps.map((step) => {
    const currentIndex = order.indexOf(step.id)
    if (currentIndex < targetIndex) {
      return { ...step, status: 'complete' }
    }
    if (step.id === stepId) {
      return { ...step, label, status: 'active' }
    }
    return currentIndex > targetIndex ? { ...step, status: 'pending' } : step
  })
}

function completeProcessSteps(steps: ProcessStep[]): ProcessStep[] {
  return steps.map((step) => ({ ...step, status: 'complete' }))
}

export function normalizeCitation(data: Record<string, unknown>, fallbackIndex: number): Citation {
  return {
    id: (data.id as string) ?? `${data.url as string ?? 'citation'}-${fallbackIndex}`,
    index: typeof data.index === 'number' ? data.index : fallbackIndex,
    sourceTitle: (data.title as string) ?? (data.source_title as string) ?? 'Source',
    sourceName: (data.source as string) ?? (data.source_name as string) ?? '',
    publishedAt: (data.published_at as string) ?? (data.publishedAt as string) ?? '',
    excerpt: (data.excerpt as string) ?? '',
    highlight: (data.highlight as string) ?? '',
    url: (data.url as string) ?? '#',
    relevance: (data.relevance as 'high' | 'medium' | 'low') ?? 'medium',
  }
}

export function normalizeRecommendation(data: Record<string, unknown>, fallbackIndex: number): Recommendation {
  return {
    id: (data.id as string) ?? `recommendation-${fallbackIndex}`,
    title: (data.title as string) ?? 'Recommendation',
    description: (data.description as string) ?? '',
    recommendationType: (data.recommendation_type as string) ?? (data.type as string) ?? 'action',
    confidence: typeof data.confidence === 'number' ? data.confidence : null,
  }
}

export function extractCitationsFromMessages(messages: ChatMessageResponse[]): Citation[] {
  const citations: Citation[] = []
  const seen = new Set<string>()

  for (const message of messages) {
    const sources = message.sources_json
    if (!sources || typeof sources !== 'object') continue

    const rawCitations = (sources as Record<string, unknown>).citations
    if (!Array.isArray(rawCitations)) continue

    for (const rawCitation of rawCitations) {
      if (!rawCitation || typeof rawCitation !== 'object') continue
      const citation = normalizeCitation(rawCitation as Record<string, unknown>, citations.length + 1)
      const dedupeKey = citation.id || citation.url || `${citation.sourceTitle}-${citation.index}`
      if (seen.has(dedupeKey)) continue
      seen.add(dedupeKey)
      citations.push({ ...citation, index: citations.length + 1 })
    }
  }

  return citations
}

export function deriveEvidenceState({
  evidencePackage,
  preferredState,
  citations,
  graphNodes,
  recommendations,
  hasConversation,
}: DeriveEvidenceStateOptions): EvidenceState {
  if (graphNodes.length > 0 || evidencePackage.graphNarrative) {
    return 'graph'
  }

  if (evidencePackage.charts.length > 0 || evidencePackage.reportMarkdown) {
    return 'visualization'
  }

  if (
    citations.length > 0 ||
    recommendations.length > 0 ||
    evidencePackage.citationsNarrative ||
    hasConversation
  ) {
    return 'citations'
  }

  return preferredState === 'idle' ? 'idle' : 'citations'
}

export function formatInvestigateEventError(data: Record<string, unknown> | null): string {
  const code = typeof data?.code === 'string' ? data.code : null
  const detail = typeof data?.message === 'string' ? data.message : null

  const base = {
    session_not_found: 'This investigation session could not be found. Start a new thread and try again.',
    session_archived: 'This investigation thread has already been archived. Start a new thread to continue.',
    rate_limited: 'You have reached the investigation rate limit. Wait a moment, then try again.',
    input_blocked: 'Your question was blocked by safety filters. Rephrase it and try again.',
    llm_error: 'Cogent could not finish the AI response for this investigation. Please retry in a moment.',
  }[code ?? '']

  return base ?? detail ?? 'Cogent could not complete this investigation.'
}

export function formatInvestigateTransportError(error: unknown): string {
  if (error instanceof Error && error.message) {
    if (error.message.includes('401') || error.message.includes('403')) {
      return 'Your session expired or no longer has access to Investigate. Refresh and try again.'
    }
    if (error.message.includes('429')) {
      return 'You have reached the investigation rate limit. Please wait a moment before trying again.'
    }
  }

  return 'Cogent could not reach the investigation service. Check your connection and try again.'
}

export function hydrateInvestigateSession(session: ChatSessionDetailResponse): HydratedInvestigateSession {
  const messages = session.messages
    .filter((message) => message.role === 'user' || message.role === 'assistant')
    .map((message) => ({
      id: message.id,
      role: message.role as 'user' | 'assistant',
      content: message.content,
      timestamp: new Date(message.created_at),
      isStreaming: false,
    }))

  const citations = extractCitationsFromMessages(session.messages)
  const evidencePackage = cloneDefaultPackage()

  if (citations.length > 0) {
    evidencePackage.citationsNarrative = '> Resumed an active investigation thread with saved citations from previous assistant responses.'
  } else if (messages.length > 0) {
    evidencePackage.citationsNarrative = '> Resumed an active investigation thread. Continue from the latest answer in the chat pane.'
  }

  return {
    evidenceState: deriveEvidenceState({
      evidencePackage,
      preferredState: 'citations',
      citations,
      graphNodes: [],
      recommendations: [],
      hasConversation: messages.some((message) => message.role === 'assistant' && message.content.trim().length > 0),
    }),
    evidencePackage,
    messages,
    citations,
  }
}

export const INVESTIGATE_SUGGESTIONS = [
  { label: 'What are the top risks in my signal feed?', tag: 'Risks' },
  { label: 'Show entity relationships for recent signals', tag: 'Graph' },
  { label: 'Compare key metrics across my tracked domains', tag: 'Chart' },
  { label: 'Summarize the latest regulatory developments', tag: 'Regulatory' },
  { label: 'What opportunities has the system detected this week?', tag: 'Opportunities' },
  { label: 'Analyze competitive dynamics in my primary sector', tag: 'Competitive' },
]

export function useInvestigate({
  initialQuery,
  initialIndustrySlug,
  initialSessionId,
}: UseInvestigateOptions = {}) {
  const [messages, setMessages] = useState<Message[]>([])
  const [evidenceState, setEvidenceState] = useState<EvidenceState>('idle')
  const [processSteps, setProcessSteps] = useState<ProcessStep[]>([])
  const [evidencePackage, setEvidencePackage] = useState<EvidencePackage>(cloneDefaultPackage())
  const [isProcessing, setIsProcessing] = useState(false)
  const [isRestoringSession, setIsRestoringSession] = useState(true)
  const [liveCitations, setLiveCitations] = useState<Citation[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [liveGraphNodes, setLiveGraphNodes] = useState<GraphNode[]>([])
  const [liveGraphEdges, setLiveGraphEdges] = useState<GraphEdge[]>([])
  const [industries, setIndustries] = useState<IndustryItem[]>([])
  const [industriesLoading, setIndustriesLoading] = useState(true)
  const [industriesError, setIndustriesError] = useState<string | null>(null)
  const [selectedIndustrySlug, setSelectedIndustrySlug] = useState(initialIndustrySlug ?? '')
  const [sessionTitle, setSessionTitle] = useState<string | null>(null)

  const firedInitial = useRef(false)
  const sessionIdRef = useRef<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const restoreAttemptedRef = useRef(false)

  useEffect(() => {
    let cancelled = false

    const loadIndustries = async () => {
      setIndustriesLoading(true)
      setIndustriesError(null)

      try {
        const data = await getIndustries()
        if (cancelled) return
        setIndustries(data)
      } catch {
        if (cancelled) return
        setIndustriesError('Industry filters are unavailable right now. You can still investigate across all monitored industries.')
      } finally {
        if (!cancelled) {
          setIndustriesLoading(false)
        }
      }
    }

    loadIndustries()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (restoreAttemptedRef.current || industriesLoading) return
    restoreAttemptedRef.current = true

    let cancelled = false

    const restoreSession = async () => {
      setIsRestoringSession(true)

      try {
        let session: ChatSessionDetailResponse | null = null

        if (initialSessionId) {
          session = await getChatSession(initialSessionId).catch(() => null)
        }

        if (!session) {
          const sessions = await listChatSessions({ limit: 10 }).catch(() => null)
          const preferredIndustryId = selectedIndustrySlug
            ? industries.find((industry) => industry.slug === selectedIndustrySlug)?.id
            : null

          const resumeTarget = sessions?.items.find((item) => (
            preferredIndustryId
              ? item.industry_id === preferredIndustryId
              : true
          ))

          if (resumeTarget) {
            session = await getChatSession(resumeTarget.id).catch(() => null)
          }
        }

        if (cancelled || !session) return

        const hydrated = hydrateInvestigateSession(session)
        sessionIdRef.current = session.id
        setSessionTitle(session.title ?? null)
        setMessages(hydrated.messages)
        setLiveCitations(hydrated.citations)
        setRecommendations([])
        setLiveGraphNodes([])
        setLiveGraphEdges([])
        setEvidencePackage(hydrated.evidencePackage)
        setEvidenceState(hydrated.evidenceState)
      } finally {
        if (!cancelled) {
          setIsRestoringSession(false)
        }
      }
    }

    restoreSession()

    return () => {
      cancelled = true
    }
  }, [industries, industriesLoading, initialSessionId, selectedIndustrySlug])

  const finalizeThread = useCallback((
    preferredState: EvidenceState,
    assistantContent: string,
    streamedCitations: Citation[],
    streamedRecommendations: Recommendation[],
    streamedGraphNodes: GraphNode[],
    streamedPackage: EvidencePackage,
  ) => {
    const nextPackage = {
      ...streamedPackage,
      citationsNarrative: streamedPackage.citationsNarrative
        || buildRecommendationsNarrative(streamedRecommendations)
        || buildEvidenceFallbackNote(assistantContent.trim().length > 0),
    }

    setEvidencePackage(nextPackage)
    setEvidenceState(deriveEvidenceState({
      evidencePackage: nextPackage,
      preferredState,
      citations: streamedCitations,
      graphNodes: streamedGraphNodes,
      recommendations: streamedRecommendations,
      hasConversation: assistantContent.trim().length > 0,
    }))
    setProcessSteps((prev) => completeProcessSteps(prev))
    setIsProcessing(false)
  }, [])

  const stopStreaming = useCallback(() => {
    if (!abortControllerRef.current) return

    abortControllerRef.current.abort()
    abortControllerRef.current = null

    setMessages((prev) => {
      let updated = false
      return prev.map((message) => {
        if (message.isStreaming) {
          updated = true
          return {
            ...message,
            content: message.content || 'Investigation stopped before a full answer was returned.',
            isStreaming: false,
          }
        }
        return message
      }).concat(updated ? [] : [{
        id: `msg-${Date.now()}-ai-stop`,
        role: 'assistant',
        content: 'Investigation stopped before a full answer was returned.',
        timestamp: new Date(),
      }])
    })

    setProcessSteps((prev) => completeProcessSteps(prev))
    setEvidencePackage((prev) => {
      if (prev.citationsNarrative || liveCitations.length > 0 || recommendations.length > 0) {
        return prev
      }
      return {
        ...prev,
        citationsNarrative: '> Investigation was stopped before structured evidence could finish streaming.',
      }
    })
    setEvidenceState((prev) => {
      if (liveGraphNodes.length > 0 || evidencePackage.graphNarrative) return 'graph'
      if (evidencePackage.charts.length > 0 || evidencePackage.reportMarkdown) return 'visualization'
      if (liveCitations.length > 0 || recommendations.length > 0 || prev === 'citations') return 'citations'
      return 'idle'
    })
    setIsProcessing(false)
  }, [evidencePackage, liveCitations.length, liveGraphNodes.length, recommendations.length])

  const clearConversation = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    if (sessionIdRef.current) {
      archiveChatSession(sessionIdRef.current).catch(() => { /* ignore */ })
      sessionIdRef.current = null
    }

    setMessages([])
    setEvidenceState('idle')
    setProcessSteps([])
    setEvidencePackage(cloneDefaultPackage())
    setLiveCitations([])
    setRecommendations([])
    setLiveGraphNodes([])
    setLiveGraphEdges([])
    setSessionTitle(null)
    setIsProcessing(false)
  }, [])

  const changeSelectedIndustry = useCallback((nextIndustrySlug: string) => {
    if (nextIndustrySlug === selectedIndustrySlug) return
    clearConversation()
    setSelectedIndustrySlug(nextIndustrySlug)
  }, [clearConversation, selectedIndustrySlug])

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isProcessing) return

    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    const preferredState = detectEvidenceState(trimmed)
    const userMessage: Message = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }
    const aiId = `msg-${Date.now()}-ai`

    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: aiId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      },
    ])
    setProcessSteps(cloneProcessSteps())
    setEvidenceState('thinking')
    setEvidencePackage(cloneDefaultPackage())
    setLiveCitations([])
    setRecommendations([])
    setLiveGraphNodes([])
    setLiveGraphEdges([])
    setIsProcessing(true)

    let assistantContent = ''
    let streamHandled = false
    let streamedCitations: Citation[] = []
    let streamedRecommendations: Recommendation[] = []
    let streamedGraphNodes: GraphNode[] = []
    let streamedPackage = cloneDefaultPackage()

    try {
      if (!sessionIdRef.current) {
        const session = await createChatSession({
          industry_slug: selectedIndustrySlug || undefined,
          title: trimmed.slice(0, 80),
        })
        sessionIdRef.current = session.id
        setSessionTitle(session.title ?? trimmed.slice(0, 80))
      }

      setProcessSteps((prev) => updateProcessStep(prev, 'reasoning', 'Analyzing request'))

      const ctrl = await sendChatMessage(
        sessionIdRef.current,
        { message: trimmed },
        {
          onEvent: (event, data) => {
            const payload = (data && typeof data === 'object') ? data as Record<string, unknown> : null

            if (event === 'thinking') {
              const status = typeof payload?.status === 'string' ? payload.status : ''
              if (status === 'loading_context') {
                setProcessSteps((prev) => updateProcessStep(prev, 'reasoning', 'Loading conversation context'))
              } else if (status === 'processing_results') {
                setProcessSteps((prev) => updateProcessStep(prev, 'tools', 'Processing tool results'))
              } else {
                setProcessSteps((prev) => updateProcessStep(prev, 'reasoning', 'Analyzing request'))
              }
              return
            }

            if (event === 'tool_call') {
              const tool = typeof payload?.tool === 'string' ? payload.tool : 'investigation tool'
              setProcessSteps((prev) => updateProcessStep(prev, 'tools', `Running ${humanizeToolName(tool)}`))
              return
            }

            if (event === 'tool_result') {
              const summary = typeof payload?.summary === 'string' ? payload.summary : 'Collected supporting evidence'
              setProcessSteps((prev) => updateProcessStep(prev, 'tools', summary))
              return
            }

            if (event === 'content') {
              const chunk = (payload?.text as string) ?? (typeof data === 'string' ? data : '')
              assistantContent += chunk
              setProcessSteps((prev) => updateProcessStep(prev, 'answer', 'Streaming answer'))
              setMessages((prev) => prev.map((message) => (
                message.id === aiId
                  ? { ...message, content: `${message.content}${chunk}` }
                  : message
              )))
              return
            }

            if (event === 'citation' && payload) {
              const citation = normalizeCitation(payload, streamedCitations.length + 1)
              streamedCitations = [...streamedCitations, citation]
              setLiveCitations(streamedCitations)
              return
            }

            if (event === 'recommendation' && payload) {
              const recommendation = normalizeRecommendation(payload, streamedRecommendations.length + 1)
              streamedRecommendations = [...streamedRecommendations, recommendation]
              setRecommendations(streamedRecommendations)
              return
            }

            if (event === 'evidence' && payload) {
              streamedPackage = {
                charts: Array.isArray(payload.charts) ? payload.charts as ChartDefinition[] : streamedPackage.charts,
                reportMarkdown: typeof payload.reportMarkdown === 'string' ? payload.reportMarkdown : streamedPackage.reportMarkdown,
                graphNarrative: typeof payload.graphNarrative === 'string' ? payload.graphNarrative : streamedPackage.graphNarrative,
                citationsNarrative: typeof payload.citationsNarrative === 'string' ? payload.citationsNarrative : streamedPackage.citationsNarrative,
              }
              setEvidencePackage(streamedPackage)
              return
            }

            if (event === 'graph' && payload) {
              streamedGraphNodes = Array.isArray(payload.nodes) ? payload.nodes as GraphNode[] : streamedGraphNodes
              const edges = Array.isArray(payload.edges) ? payload.edges as GraphEdge[] : []
              setLiveGraphNodes(streamedGraphNodes)
              setLiveGraphEdges(edges)
              return
            }

            if (event === 'error') {
              streamHandled = true
              const errorMessage = formatInvestigateEventError(payload)
              setMessages((prev) => prev.map((message) => (
                message.id === aiId
                  ? { ...message, content: errorMessage, isStreaming: false }
                  : message
              )))
              finalizeThread(preferredState, errorMessage, streamedCitations, streamedRecommendations, streamedGraphNodes, streamedPackage)
              return
            }

            if (event === 'done') {
              streamHandled = true
              setMessages((prev) => prev.map((message) => (
                message.id === aiId
                  ? { ...message, isStreaming: false }
                  : message
              )))
              finalizeThread(preferredState, assistantContent, streamedCitations, streamedRecommendations, streamedGraphNodes, streamedPackage)
            }
          },
          onError: (error) => {
            if (streamHandled) return
            streamHandled = true
            const message = assistantContent || formatInvestigateTransportError(error)
            setMessages((prev) => prev.map((item) => (
              item.id === aiId
                ? { ...item, content: message, isStreaming: false }
                : item
            )))
            finalizeThread(preferredState, message, streamedCitations, streamedRecommendations, streamedGraphNodes, streamedPackage)
          },
          onDone: () => {
            if (streamHandled) return
            streamHandled = true
            setMessages((prev) => prev.map((item) => (
              item.id === aiId
                ? {
                  ...item,
                  content: item.content || buildFallbackResponse(trimmed),
                  isStreaming: false,
                }
                : item
            )))
            finalizeThread(
              preferredState,
              assistantContent || buildFallbackResponse(trimmed),
              streamedCitations,
              streamedRecommendations,
              streamedGraphNodes,
              streamedPackage,
            )
          },
        },
      )

      abortControllerRef.current = ctrl
    } catch (error) {
      const fallback = formatInvestigateTransportError(error)
      setMessages((prev) => prev.map((message) => (
        message.id === aiId
          ? { ...message, content: fallback, isStreaming: false }
          : message
      )))
      finalizeThread(preferredState, fallback, streamedCitations, streamedRecommendations, streamedGraphNodes, streamedPackage)
    }
  }, [finalizeThread, isProcessing, selectedIndustrySlug])

  useEffect(() => {
    if (!initialQuery || firedInitial.current || isRestoringSession) return

    firedInitial.current = true
    sendMessage(initialQuery)
  }, [initialQuery, isRestoringSession, sendMessage])

  return {
    messages,
    evidenceState,
    processSteps,
    citations: liveCitations,
    recommendations,
    graphNodes: liveGraphNodes,
    graphEdges: liveGraphEdges,
    evidencePackage,
    isProcessing,
    isRestoringSession,
    industries,
    industriesLoading,
    industriesError,
    selectedIndustrySlug,
    sessionTitle,
    suggestions: INVESTIGATE_SUGGESTIONS,
    sendMessage,
    stopStreaming,
    clearConversation,
    setSelectedIndustrySlug: changeSelectedIndustry,
  }
}
