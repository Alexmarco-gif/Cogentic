'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { submitFeedback } from '@/lib/api/feedback'
import {
  normalizeIntelligenceBrief,
} from '@/lib/briefs/schema'
import {
  getSignal,
  getSignalFeed,
  listSignals as fetchSignalsList,
} from '@/lib/api/signals'
import type { SignalResponse } from '@/lib/api/types'
export type {
  Analysis,
  AnalysisDrivers,
  BriefClaim,
  BriefCategory,
  BriefConfidenceLevel,
  BriefMetadata,
  BriefPriorityLevel,
  BriefTimeframe,
  ExecutiveSummary,
  ImpactAssessment,
  IntelligenceBrief,
  KeyIntelligenceQuestions,
  LongTermImpact,
  RecommendedActions,
  RiskAssessment,
  ShortTermImpact,
  SignalEvidence,
  SignalsAndIndicators,
  SituationOverview,
  SituationStatus,
} from '@/lib/briefs/schema'
import type { IntelligenceBrief } from '@/lib/briefs/schema'

export type SignalDomain = string

export type SignalSeverity = 'critical' | 'high' | 'medium' | 'low'

export interface SignalSource {
  id: string
  name: string
  url: string
  publishedAt: string
}

export interface Signal {
  id: string
  entityName: string
  entityAvatar?: string
  entityInitial: string
  domain: SignalDomain
  severity: SignalSeverity
  confidence: number
  headline: string
  summary: string
  publishedAt: string
  relativeTime: string
  sources: SignalSource[]
  sparklineData: number[]
  isUnread: boolean
  isSaved: boolean
  brief: IntelligenceBrief
}

export interface MacroIndicator {
  label: string
  value: string
  sub: string
  change: string
  positive: boolean
}

export type StatusLevel = 'critical' | 'elevated' | 'moderate' | 'stable'

export interface StrategicStatus {
  id: string
  label: string
  count: number
  level: StatusLevel
  contextLine: string
  changeDetector: string
  suggestedAction: string
  trend: 'up' | 'down' | 'flat'
}

export const STRATEGIC_STATUSES: StrategicStatus[] = []

export interface HeatmapQuadrant {
  id: string
  label: string
  level: StatusLevel
  explanation: string
  trend: 'improving' | 'deteriorating' | 'stable'
  forecast: string
  suggestedAction: string
}

export const HEATMAP_DATA: HeatmapQuadrant[] = []

export type FeedCategory = 'risk' | 'opportunity' | 'alert' | 'investigation' | 'brief'

export interface FeedEvent {
  id: string
  timestamp: string
  relativeTime: string
  severity: SignalSeverity
  category: FeedCategory
  headline: string
  domain: SignalDomain
  explanation: string
  signalId?: string
}

export const FEED_EVENTS: FeedEvent[] = []

function toBriefDate(): string {
  const now = new Date()
  const h = now.getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export function useGreeting(name?: string) {
  return `${toBriefDate()}${name ? `, ${name}` : ''}.`
}

function mapBackendSignal(raw: SignalResponse): Signal {
  const data = raw.extracted_data ?? {} as Record<string, unknown>
  const publishedAt = raw.published_at ?? raw.created_at
  const domain = (data.domain as SignalDomain) ?? 'Uncategorized'
  const confidence = Math.round(raw.confidence * 100)

  return {
    id: raw.id,
    entityName: (data.entity_name as string) ?? raw.title ?? 'Unknown',
    entityInitial: ((data.entity_name as string) ?? raw.title ?? 'U').charAt(0).toUpperCase(),
    entityAvatar: data.entity_avatar as string | undefined,
    domain,
    severity: mapConfidenceToSeverity(raw.confidence),
    confidence,
    headline: raw.title ?? '',
    summary: raw.summary ?? '',
    publishedAt,
    relativeTime: getRelativeTime(publishedAt),
    sources: (data.sources as SignalSource[]) ?? [],
    sparklineData: (data.sparkline as number[]) ?? [],
    isUnread: true,
    isSaved: false,
    brief: normalizeIntelligenceBrief(data.brief, {
      headline: raw.title,
      summary: raw.summary,
      domain,
      confidence,
      tags: [],
    }),
  }
}

function mapConfidenceToSeverity(confidence: number): SignalSeverity {
  if (confidence >= 0.85) return 'critical'
  if (confidence >= 0.7) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

function getRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function sortSignalsByPublishedAt(signals: Signal[]): Signal[] {
  return [...signals].sort(
    (a, b) => new Date(b.publishedAt).getTime() - new Date(a.publishedAt).getTime(),
  )
}

function storageKey(scope: 'read' | 'saved' | 'dismissed', mode: UseSignalsOptions['mode'], industryId?: string) {
  return `cogent:signals:${mode}:${industryId ?? 'all'}:${scope}`
}

export function serializeSignalIds(ids: Iterable<string>): string {
  return JSON.stringify(Array.from(ids))
}

export function deserializeSignalIds(raw: string | null): Set<string> {
  if (!raw) return new Set()
  try {
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed)
      ? new Set(parsed.filter((value): value is string => typeof value === 'string'))
      : new Set()
  } catch {
    return new Set()
  }
}

export function toggleSignalId(ids: Set<string>, id: string): Set<string> {
  const next = new Set(ids)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  return next
}

export interface UseSignalsOptions {
  enabled?: boolean
  industryId?: string
  mode?: 'catalog' | 'feed'
  pageSize?: number
}

export function useSignals({
  enabled = true,
  industryId,
  mode = 'catalog',
  pageSize = 50,
}: UseSignalsOptions = {}) {
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeDrawerSignal, setActiveDrawerSignal] = useState<Signal | null>(null)
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const [isLoadingMore, setIsLoadingMore] = useState(false)
  const [seq, setSeq] = useState(0)
  const readSignalIdsRef = useRef<Set<string>>(new Set())
  const savedSignalIdsRef = useRef<Set<string>>(new Set())
  const dismissedSignalIdsRef = useRef<Set<string>>(new Set())

  const persistIds = useCallback((scope: 'read' | 'saved' | 'dismissed', ids: Set<string>) => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(storageKey(scope, mode, industryId), serializeSignalIds(ids))
  }, [industryId, mode])

  const applyUiState = useCallback((signal: Signal): Signal => ({
    ...signal,
    isUnread: !readSignalIdsRef.current.has(signal.id),
    isSaved: savedSignalIdsRef.current.has(signal.id),
  }), [])

  const mapFetchedSignals = useCallback((items: SignalResponse[]): Signal[] => {
    const hydrated = items
      .map((item) => mapBackendSignal(item))
      .filter((signal) => !dismissedSignalIdsRef.current.has(signal.id))
      .map(applyUiState)

    return sortSignalsByPublishedAt(hydrated)
  }, [applyUiState])

  const fetchPage = useCallback(async (pageSkip: number) => {
    if (mode === 'feed') {
      return getSignalFeed({
        industry_id: industryId,
        limit: pageSize,
        skip: pageSkip,
      })
    }

    return fetchSignalsList({
      limit: pageSize,
      skip: pageSkip,
    })
  }, [industryId, mode, pageSize])

  const refresh = useCallback(() => setSeq((current) => current + 1), [])

  useEffect(() => {
    if (typeof window === 'undefined') return

    readSignalIdsRef.current = deserializeSignalIds(window.localStorage.getItem(storageKey('read', mode, industryId)))
    savedSignalIdsRef.current = deserializeSignalIds(window.localStorage.getItem(storageKey('saved', mode, industryId)))
    dismissedSignalIdsRef.current = deserializeSignalIds(window.localStorage.getItem(storageKey('dismissed', mode, industryId)))
  }, [industryId, mode])

  useEffect(() => {
    let cancelled = false

    if (!enabled) {
      setSignals([])
      setTotal(0)
      setSkip(0)
      setLoading(false)
      setError(null)
      return () => { cancelled = true }
    }

    async function load() {
      setLoading(true)
      setError(null)

      try {
        const data = await fetchPage(0)
        if (!cancelled) {
          const nextSignals = mapFetchedSignals(data?.items ?? [])
          setSignals(nextSignals)
          setTotal(data.total ?? nextSignals.length)
          setSkip(data.items?.length ?? 0)
        }
      } catch (err) {
        if (!cancelled) {
          setSignals([])
          setTotal(0)
          setSkip(0)
          setError(err instanceof Error ? err.message : 'Failed to load signals')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => { cancelled = true }
  }, [enabled, fetchPage, mapFetchedSignals, seq])

  const loadMore = useCallback(async () => {
    if (!enabled || isLoadingMore || skip >= total) return

    setIsLoadingMore(true)
    try {
      const data = await fetchPage(skip)
      if (data?.items?.length) {
        const nextSignals = mapFetchedSignals(data.items)
        setSignals((prev) => sortSignalsByPublishedAt([...prev, ...nextSignals]))
        setSkip((prev) => prev + data.items.length)
        setTotal(data.total ?? total)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load more signals')
    } finally {
      setIsLoadingMore(false)
    }
  }, [enabled, fetchPage, isLoadingMore, mapFetchedSignals, skip, total])

  const markSignalRead = useCallback((id: string) => {
    const nextReadIds = new Set(readSignalIdsRef.current)
    nextReadIds.add(id)
    readSignalIdsRef.current = nextReadIds
    persistIds('read', nextReadIds)

    setSignals((prev) =>
      prev.map((signal) => (
        signal.id === id
          ? { ...signal, isUnread: false }
          : signal
      )),
    )
    setActiveDrawerSignal((prev) => (
      prev?.id === id
        ? { ...prev, isUnread: false }
        : prev
    ))
  }, [persistIds])

  const openDrawer = useCallback((signal: Signal) => {
    const hydrated = applyUiState(signal)
    setActiveDrawerSignal({ ...hydrated, isUnread: false })
    markSignalRead(signal.id)
  }, [applyUiState, markSignalRead])

  const openDrawerById = useCallback(async (signalId: string) => {
    const existingSignal = signals.find((signal) => signal.id === signalId)
    if (existingSignal) {
      openDrawer(existingSignal)
      return
    }

    try {
      const detail = await getSignal(signalId)
      const hydrated = applyUiState(mapBackendSignal(detail))

      setSignals((prev) => sortSignalsByPublishedAt([...prev, hydrated]))
      openDrawer(hydrated)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open signal')
    }
  }, [applyUiState, openDrawer, signals])

  const closeDrawer = useCallback(() => setActiveDrawerSignal(null), [])

  const toggleSave = useCallback((id: string) => {
    const previousSavedIds = savedSignalIdsRef.current
    const isCurrentlySaved = previousSavedIds.has(id)
    const nextSavedIds = toggleSignalId(previousSavedIds, id)
    savedSignalIdsRef.current = nextSavedIds
    persistIds('saved', nextSavedIds)

    setSignals((prev) =>
      prev.map((signal) => (
        signal.id === id
          ? { ...signal, isSaved: !isCurrentlySaved }
          : signal
      )),
    )
    setActiveDrawerSignal((prev) => (
      prev?.id === id
        ? { ...prev, isSaved: !isCurrentlySaved }
        : prev
    ))

    if (isCurrentlySaved) return

    void submitFeedback({
      feedback_type: 'signal_saved',
      target_type: 'signal',
      target_id: id,
      context: {
        source: mode,
        industry_id: industryId ?? null,
      },
    }).catch(() => {
      savedSignalIdsRef.current = previousSavedIds
      persistIds('saved', previousSavedIds)
      setSignals((prev) =>
        prev.map((signal) => (
          signal.id === id
            ? { ...signal, isSaved: false }
            : signal
        )),
      )
      setActiveDrawerSignal((prev) => (
        prev?.id === id
          ? { ...prev, isSaved: false }
          : prev
      ))
      setError('Unable to save signal right now')
    })
  }, [industryId, mode, persistIds])

  const dismiss = useCallback((id: string) => {
    let removedSignal: Signal | null = null
    const previousDismissedIds = dismissedSignalIdsRef.current
    const nextDismissedIds = new Set(previousDismissedIds)
    nextDismissedIds.add(id)
    dismissedSignalIdsRef.current = nextDismissedIds
    persistIds('dismissed', nextDismissedIds)

    setSignals((prev) => {
      removedSignal = prev.find((signal) => signal.id === id) ?? null
      return prev.filter((signal) => signal.id !== id)
    })
    setActiveDrawerSignal((prev) => (
      prev?.id === id
        ? null
        : prev
    ))

    void submitFeedback({
      feedback_type: 'signal_dismissed',
      target_type: 'signal',
      target_id: id,
      context: {
        source: mode,
        industry_id: industryId ?? null,
      },
    }).catch(() => {
      dismissedSignalIdsRef.current = previousDismissedIds
      persistIds('dismissed', previousDismissedIds)
      if (removedSignal) {
        setSignals((prev) => sortSignalsByPublishedAt([...prev, applyUiState(removedSignal!)]))
      }
      setError('Unable to dismiss signal right now')
    })
  }, [applyUiState, industryId, mode, persistIds])

  const unreadCount = signals.filter((signal) => signal.isUnread).length
  const riskCount = signals.filter((signal) => signal.severity === 'critical' || signal.severity === 'high').length
  const opportunityCount = signals.filter((signal) => signal.severity === 'medium').length

  return {
    signals,
    loading,
    error,
    activeDrawerSignal,
    openDrawer,
    openDrawerById,
    closeDrawer,
    toggleSave,
    dismiss,
    unreadCount,
    riskCount,
    opportunityCount,
    total,
    hasMore: skip < total,
    isLoadingMore,
    loadMore,
    refresh,
  }
}
