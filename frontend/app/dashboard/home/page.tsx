'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  BookOpen,
  Plus,
  RefreshCw,
  ShoppingBag,
  Wifi,
  WifiOff,
  Zap,
} from 'lucide-react'
import {
  friendlyErrorMessage,
  get,
  getAccessTokenSilent,
  getSituationRoomDashboard,
  isApiError,
} from '@/lib/api'
import type {
  ActiveAlert,
  DashboardMetrics,
  SignalFeedItem,
  SituationRoomDashboard,
} from '@/lib/api'
import { useFeatureGate } from '@/lib/hooks/useFeatureGate'
import { useCredits } from '@/lib/hooks/useCredits'
import {
  useSignals,
  type FeedEvent,
  type HeatmapQuadrant,
  type Signal,
  type SignalSeverity,
  type StatusLevel,
  type StrategicStatus,
} from '@/lib/hooks/useSignals'
import { MorningBrief } from '@/components/signals/MorningBrief'
import { StrategicStatusCard } from '@/components/signals/StrategicStatusCard'
import { IntelHeatmap } from '@/components/signals/IntelHeatmap'
import { LiveIntelFeed } from '@/components/signals/LiveIntelFeed'
import { SignalDrawer } from '@/components/signals/SignalDrawer'

interface IndustryOption {
  id: string
  name: string
  slug: string
}

interface SituationRoomState {
  dashboard: SituationRoomDashboard | null
  loading: boolean
  error: string | null
  lastUpdated: Date | null
  liveConnected: boolean
  liveRevision: number
  refetch: () => void
}

interface SituationRoomWSMessage {
  event: string
  data: unknown
  timestamp?: string
}

interface StarterCreditState {
  allocated: number
  remaining: number
}

const FALLBACK_INDUSTRIES: IndustryOption[] = [
  { id: 'fintech', name: 'Fintech', slug: 'fintech' },
  { id: 'financial-services', name: 'Financial Services', slug: 'financial-services' },
  { id: 'agriculture-agritech', name: 'Agriculture & Agritech', slug: 'agriculture-agritech' },
]

const QUICK_ACTIONS = [
  { label: 'New Contract', icon: <Plus size={12} />, href: '/dashboard/studio' },
  { label: 'Signals', icon: <Zap size={12} />, href: '/dashboard/signals' },
  { label: 'Marketplace', icon: <ShoppingBag size={12} />, href: '/dashboard/marketplace' },
  { label: 'Library', icon: <BookOpen size={12} />, href: '/dashboard/library' },
] as const

const STATUS_ROUTES: Record<string, string> = {
  'critical-alerts': '/dashboard/signals?filter=critical-alerts',
  risks: '/dashboard/signals?filter=risks',
  opportunities: '/dashboard/signals?filter=opportunities',
  investigations: '/dashboard/signals?filter=investigations',
  'signals-available': '/dashboard/signals',
  'credits-left': '/dashboard/studio',
  'signals-today': '/dashboard/signals',
}

const LIVE_REFRESH_EVENTS = new Set([
  'new_signal',
  'signal_updated',
  'brief_published',
  'anomaly_detected',
  'metrics_update',
])

const POLL_INTERVAL_MS = 5 * 60 * 1000
const LIVE_REFRESH_DEBOUNCE_MS = 400
const LIVE_RECONNECT_MS = 5000
const LIVE_PING_MS = 20000

function metricToLevel(value: number, thresholds: [number, number, number]): StatusLevel {
  if (value >= thresholds[0]) return 'critical'
  if (value >= thresholds[1]) return 'elevated'
  if (value >= thresholds[2]) return 'moderate'
  return 'stable'
}

function confidenceToLevel(avgConfidence: number): StatusLevel {
  if (avgConfidence >= 0.85) return 'stable'
  if (avgConfidence >= 0.7) return 'moderate'
  if (avgConfidence >= 0.55) return 'elevated'
  return 'critical'
}

function volumeTrend(current: number, previous: number): 'up' | 'down' | 'flat' {
  if (current > previous * 1.1) return 'up'
  if (current < previous * 0.9) return 'down'
  return 'flat'
}

function volumeTrendHeatmap(
  current: number,
  previous: number,
): 'improving' | 'deteriorating' | 'stable' {
  if (current > previous * 1.1) return 'improving'
  if (current < previous * 0.9) return 'deteriorating'
  return 'stable'
}

function toSignalSeverity(priority: string): SignalSeverity {
  if (priority === 'critical') return 'critical'
  if (priority === 'high') return 'high'
  if (priority === 'medium') return 'medium'
  return 'low'
}

function getRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function buildStrategicStatuses(metrics: DashboardMetrics): StrategicStatus[] {
  const typeCount = (signalType: string) => (
    metrics.type_breakdown.find((entry) => entry.signal_type === signalType)?.count ?? 0
  )

  const signalsPerDay = metrics.signals_last_7d / 7
  const riskSignals = typeCount('regulatory') + typeCount('financial') + typeCount('news')
  const opportunitySignals = typeCount('market')
  const alertTrend = volumeTrend(metrics.anomaly_count, Math.max(1, metrics.high_priority_count))
  const volumeDirection = volumeTrend(metrics.signals_last_24h, Math.max(1, signalsPerDay))

  return [
    {
      id: 'critical-alerts',
      label: 'Critical Alerts',
      count: metrics.anomaly_count,
      level: metricToLevel(metrics.anomaly_count, [5, 3, 1]),
      contextLine: metrics.anomaly_count > 0
        ? `${metrics.anomaly_count} anomalous signals require attention`
        : 'No anomalous signals detected in the current window',
      changeDetector: alertTrend === 'up'
        ? 'Anomaly activity is increasing'
        : alertTrend === 'down'
        ? 'Critical activity is easing'
        : 'Critical activity is steady',
      suggestedAction: 'Review high-priority signals →',
      trend: alertTrend,
    },
    {
      id: 'risks',
      label: 'Risks',
      count: riskSignals,
      level: metricToLevel(riskSignals, [20, 10, 3]),
      contextLine: `${riskSignals} regulatory, financial, or news signals in scope`,
      changeDetector: volumeDirection === 'up'
        ? 'Risk volume is rising today'
        : volumeDirection === 'down'
        ? 'Risk volume is tapering'
        : 'Risk volume is stable',
      suggestedAction: 'Review risk signals →',
      trend: volumeDirection,
    },
    {
      id: 'opportunities',
      label: 'Opportunities',
      count: opportunitySignals,
      level: metricToLevel(opportunitySignals, [20, 10, 3]),
      contextLine: `${opportunitySignals} market signals flagged as opportunity-bearing`,
      changeDetector: opportunitySignals > signalsPerDay
        ? 'Opportunity discovery is accelerating'
        : 'Opportunity discovery is holding steady',
      suggestedAction: 'Review market opportunities →',
      trend: opportunitySignals > signalsPerDay ? 'up' : 'flat',
    },
    {
      id: 'signals-today',
      label: 'Signals Today',
      count: metrics.signals_last_24h,
      level: metricToLevel(metrics.signals_last_24h, [100, 50, 10]),
      contextLine: `${metrics.signals_last_24h} signals detected in the last 24 hours`,
      changeDetector: volumeDirection === 'up'
        ? 'Volume is above the weekly pace'
        : volumeDirection === 'down'
        ? 'Volume is below the weekly pace'
        : 'Volume is tracking the weekly pace',
      suggestedAction: 'Browse the latest feed →',
      trend: volumeDirection,
    },
    {
      id: 'investigations',
      label: 'Active Briefs',
      count: metrics.active_briefs,
      level: metricToLevel(metrics.active_briefs, [10, 5, 1]),
      contextLine: `${metrics.active_briefs} published brief${metrics.active_briefs === 1 ? '' : 's'} available`,
      changeDetector: metrics.active_briefs > 0
        ? 'Recent intelligence has been synthesized'
        : 'No published briefs yet',
      suggestedAction: 'Open the full signals workspace →',
      trend: metrics.active_briefs > 0 ? 'up' : 'flat',
    },
  ]
}

function buildHeatmapQuadrants(
  metrics: DashboardMetrics,
  alerts: ActiveAlert[],
): HeatmapQuadrant[] {
  const anomalyRate = metrics.total_signals > 0
    ? metrics.anomaly_count / metrics.total_signals
    : 0

  const alertLevel: StatusLevel = alerts.length >= 5
    ? 'critical'
    : alerts.length >= 2
    ? 'elevated'
    : alerts.length >= 1
    ? 'moderate'
    : 'stable'

  return [
    {
      id: 'market-risk',
      label: 'Market Risk',
      level: metricToLevel(anomalyRate * 100, [15, 8, 3]),
      explanation: `${metrics.anomaly_count} anomalies across ${metrics.total_signals} signals (${(anomalyRate * 100).toFixed(1)}%)`,
      trend: anomalyRate > 0.1 ? 'deteriorating' : anomalyRate < 0.03 ? 'improving' : 'stable',
      forecast: metrics.anomaly_count > 0
        ? 'Elevated anomaly rate detected in this industry'
        : 'No immediate anomaly spike detected',
      suggestedAction: 'Review anomaly signals for emerging risks',
    },
    {
      id: 'infra-health',
      label: 'Signal Quality',
      level: confidenceToLevel(metrics.avg_confidence),
      explanation: `Average confidence ${(metrics.avg_confidence * 100).toFixed(0)}% across monitored signals`,
      trend: metrics.avg_confidence >= 0.75
        ? 'improving'
        : metrics.avg_confidence < 0.55
        ? 'deteriorating'
        : 'stable',
      forecast: metrics.avg_confidence >= 0.75
        ? 'Coverage quality is strong for this industry'
        : 'Signal quality would benefit from broader coverage',
      suggestedAction: 'Review signal quality in the main feed',
    },
    {
      id: 'competitor-activity',
      label: 'Active Alerts',
      level: alertLevel,
      explanation: `${alerts.length} alert${alerts.length === 1 ? '' : 's'} currently require review`,
      trend: alerts.length > 3 ? 'deteriorating' : alerts.length === 0 ? 'improving' : 'stable',
      forecast: alerts.length > 0
        ? 'High-priority activity is still active in the feed'
        : 'No open alert cluster right now',
      suggestedAction: 'Review open alerts and investigate',
    },
    {
      id: 'tech-trends',
      label: 'Signal Volume',
      level: metricToLevel(metrics.signals_last_24h, [100, 50, 10]),
      explanation: `${metrics.signals_last_24h} signals in the last 24h and ${metrics.signals_last_7d} in the last 7d`,
      trend: volumeTrendHeatmap(metrics.signals_last_24h, metrics.signals_last_7d / 7),
      forecast: `${metrics.type_breakdown[0]?.signal_type ?? 'news'} is leading this cycle`,
      suggestedAction: 'Browse the full industry timeline',
    },
  ]
}

function buildFeedEvents(items: SignalFeedItem[]): FeedEvent[] {
  return items.slice(0, 30).map((item) => {
    const category = item.is_anomaly
      ? 'alert'
      : item.signal_type === 'market'
      ? 'opportunity'
      : item.signal_type === 'regulatory'
      ? 'risk'
      : item.signal_type === 'news'
      ? 'risk'
      : 'alert'

    return {
      id: item.id,
      timestamp: item.fetched_at,
      relativeTime: getRelativeTime(item.fetched_at),
      severity: toSignalSeverity(item.priority),
      category,
      headline: item.title ?? 'Untitled signal',
      domain: item.signal_type,
      explanation: item.summary ?? 'New intelligence item detected in this industry.',
      signalId: item.id,
    }
  })
}

function buildStarterStatuses(
  signals: Signal[],
  credits: StarterCreditState,
): StrategicStatus[] {
  const criticalSignals = signals.filter((signal) => signal.severity === 'critical' || signal.severity === 'high').length
  const opportunitySignals = signals.filter((signal) => signal.severity === 'medium').length
  const creditsUsed = Math.max(0, credits.allocated - credits.remaining)
  const creditUtilization = credits.allocated > 0 ? creditsUsed / credits.allocated : 0
  const creditLevel: StatusLevel = credits.remaining <= 0
    ? 'critical'
    : creditUtilization >= 0.8
    ? 'elevated'
    : 'stable'

  return [
    {
      id: 'critical-alerts',
      label: 'Critical Signals',
      count: criticalSignals,
      level: metricToLevel(criticalSignals, [15, 8, 3]),
      contextLine: `${criticalSignals} high-severity signals are available for review`,
      changeDetector: criticalSignals > 0 ? 'Important signals are waiting in your feed' : 'No critical cluster detected right now',
      suggestedAction: 'Open the signals workspace',
      trend: criticalSignals > 0 ? 'up' : 'flat',
    },
    {
      id: 'opportunities',
      label: 'Opportunities',
      count: opportunitySignals,
      level: metricToLevel(opportunitySignals, [15, 8, 3]),
      contextLine: `${opportunitySignals} signals look opportunity-oriented`,
      changeDetector: opportunitySignals > 0 ? 'Fresh opportunities are visible in the feed' : 'Opportunity flow is currently quiet',
      suggestedAction: 'Review market opportunities',
      trend: opportunitySignals > 0 ? 'up' : 'flat',
    },
    {
      id: 'signals-available',
      label: 'Signals Available',
      count: signals.length,
      level: metricToLevel(signals.length, [80, 30, 10]),
      contextLine: `${signals.length} signals are available in your current workspace`,
      changeDetector: signals.length > 0 ? 'Your signal library is populated' : 'No signals have been ingested yet',
      suggestedAction: 'Browse the latest feed',
      trend: signals.length > 0 ? 'up' : 'flat',
    },
    {
      id: 'credits-left',
      label: 'Credits Left',
      count: Math.max(0, credits.remaining),
      level: creditLevel,
      contextLine: credits.remaining > 0
        ? `${credits.remaining} free credit${credits.remaining === 1 ? '' : 's'} are still available`
        : 'Free credits are exhausted, but Home remains available in read-only mode',
      changeDetector: credits.remaining > 0
        ? `${creditsUsed} of ${credits.allocated} credits have been used`
        : 'Upgrade or top up to resume premium actions',
      suggestedAction: credits.remaining > 0 ? 'Create a new contract' : 'Browse marketplace sources',
      trend: credits.remaining > 0 ? 'flat' : 'down',
    },
  ]
}

function buildStarterFeedEvents(signals: Signal[]): FeedEvent[] {
  return signals.slice(0, 30).map((signal) => ({
    id: signal.id,
    timestamp: signal.publishedAt,
    relativeTime: signal.relativeTime,
    severity: signal.severity,
    category: signal.severity === 'medium' ? 'opportunity' : signal.severity === 'low' ? 'investigation' : 'risk',
    headline: signal.headline,
    domain: signal.domain,
    explanation: signal.summary || 'Signal available in your workspace.',
    signalId: signal.id,
  }))
}

function isSituationRoomDashboardPayload(data: unknown): data is SituationRoomDashboard {
  return Boolean(
    data
    && typeof data === 'object'
    && 'industry_id' in data
    && 'metrics' in data
    && 'recent_signals' in data,
  )
}

function extractWsErrorMessage(data: unknown): string | null {
  if (typeof data === 'string') return data
  if (data && typeof data === 'object' && 'message' in data && typeof data.message === 'string') {
    return data.message
  }
  return null
}

function buildSituationRoomWebSocketUrl(industrySlug: string, token: string): string {
  const configuredBase = process.env.NEXT_PUBLIC_API_URL?.replace(/\/api\/v1\/?$/, '')
  const base = configuredBase || window.location.origin
  const url = new URL(`/api/v1/situation-room/${industrySlug}/live`, base)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.searchParams.set('token', token)
  return url.toString()
}

function useIndustryOptions(enabled: boolean) {
  const [industries, setIndustries] = useState<IndustryOption[]>(FALLBACK_INDUSTRIES)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    if (!enabled) {
      setLoading(false)
      setError(null)
      return () => { cancelled = true }
    }

    async function loadIndustries() {
      setLoading(true)
      setError(null)

      try {
        const data = await get<IndustryOption[]>('/industries')
        if (!cancelled && Array.isArray(data) && data.length > 0) {
          setIndustries(data)
        }
      } catch (err) {
        if (!cancelled) {
          setIndustries(FALLBACK_INDUSTRIES)
          setError(friendlyErrorMessage(err))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadIndustries()

    return () => { cancelled = true }
  }, [enabled])

  return { industries, loading, error }
}

function useSituationRoomDashboard(industrySlug: string, enabled: boolean): SituationRoomState {
  const [dashboard, setDashboard] = useState<SituationRoomDashboard | null>(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [liveConnected, setLiveConnected] = useState(false)
  const [liveRevision, setLiveRevision] = useState(0)
  const [seq, setSeq] = useState(0)
  const debounceTimerRef = useRef<number | null>(null)

  const refetch = useCallback(() => setSeq((current) => current + 1), [])

  useEffect(() => {
    let cancelled = false

    if (!enabled || !industrySlug) {
      setDashboard(null)
      setLoading(false)
      setError(null)
      setLastUpdated(null)
      setLiveConnected(false)
      return () => { cancelled = true }
    }

    async function loadDashboard() {
      setLoading(true)
      setError(null)
      setDashboard((current) => (
        current?.industry_slug === industrySlug
          ? current
          : null
      ))

      try {
        const data = await getSituationRoomDashboard(industrySlug, { hours: 168, limit: 50 })
        if (!cancelled) {
          setDashboard(data)
          setLastUpdated(new Date(data.generated_at))
        }
      } catch (err) {
        if (!cancelled) {
          if (isApiError(err) && err.isForbidden) {
            setError('Situation Room is not available on the current plan.')
          } else if (isApiError(err) && err.isNotFound) {
            setError(`Industry "${industrySlug}" is not available right now.`)
          } else {
            setError(friendlyErrorMessage(err))
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadDashboard()

    return () => { cancelled = true }
  }, [enabled, industrySlug, seq])

  useEffect(() => {
    if (!enabled || !industrySlug) return undefined

    const timer = window.setInterval(() => {
      refetch()
    }, POLL_INTERVAL_MS)

    return () => window.clearInterval(timer)
  }, [enabled, industrySlug, refetch])

  useEffect(() => {
    if (!enabled || !industrySlug || typeof window === 'undefined') {
      setLiveConnected(false)
      return undefined
    }

    let disposed = false
    let socket: WebSocket | null = null
    let reconnectTimer: number | null = null
    let pingTimer: number | null = null

    const clearTimers = () => {
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
      if (pingTimer) window.clearInterval(pingTimer)
      if (debounceTimerRef.current) window.clearTimeout(debounceTimerRef.current)
    }

    const scheduleSnapshotRefresh = () => {
      if (debounceTimerRef.current) {
        window.clearTimeout(debounceTimerRef.current)
      }

      debounceTimerRef.current = window.setTimeout(() => {
        setLiveRevision((current) => current + 1)
        setSeq((current) => current + 1)
      }, LIVE_REFRESH_DEBOUNCE_MS)
    }

    async function connect() {
      const token = await getAccessTokenSilent()
      if (!token || disposed) {
        setLiveConnected(false)
        return
      }

      socket = new WebSocket(buildSituationRoomWebSocketUrl(industrySlug, token))

      socket.onopen = () => {
        if (disposed) return

        setLiveConnected(true)
        pingTimer = window.setInterval(() => {
          if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ action: 'ping' }))
          }
        }, LIVE_PING_MS)
      }

      socket.onmessage = (message) => {
        let payload: SituationRoomWSMessage

        try {
          payload = JSON.parse(message.data) as SituationRoomWSMessage
        } catch {
          return
        }

        if (payload.event === 'heartbeat') {
          setLiveConnected(true)
          return
        }

        if (payload.event === 'initial_state' && isSituationRoomDashboardPayload(payload.data)) {
          setDashboard(payload.data)
          setLastUpdated(new Date(payload.timestamp ?? payload.data.generated_at))
          setError(null)
          return
        }

        if (payload.event === 'error') {
          const messageText = extractWsErrorMessage(payload.data)
          if (messageText) setError(messageText)
          return
        }

        if (LIVE_REFRESH_EVENTS.has(payload.event)) {
          setLastUpdated(new Date(payload.timestamp ?? Date.now()))
          scheduleSnapshotRefresh()
        }
      }

      socket.onerror = () => {
        socket?.close()
      }

      socket.onclose = () => {
        if (disposed) return

        setLiveConnected(false)
        reconnectTimer = window.setTimeout(() => {
          void connect()
        }, LIVE_RECONNECT_MS)
      }
    }

    void connect()

    return () => {
      disposed = true
      setLiveConnected(false)
      clearTimers()
      socket?.close()
    }
  }, [enabled, industrySlug])

  return {
    dashboard,
    loading,
    error,
    lastUpdated,
    liveConnected,
    liveRevision,
    refetch,
  }
}

export default function HomePage() {
  const router = useRouter()
  const { hasAccess, loading: gateLoading } = useFeatureGate('situation_room')
  const { credits } = useCredits()
  const premiumHomeEnabled = !gateLoading && hasAccess
  const { industries, loading: industriesLoading, error: industriesError } = useIndustryOptions(premiumHomeEnabled)
  const [industrySlug, setIndustrySlug] = useState(FALLBACK_INDUSTRIES[0].slug)

  useEffect(() => {
    if (!premiumHomeEnabled || industries.length === 0) return

    setIndustrySlug((current) => (
      industries.some((industry) => industry.slug === current)
        ? current
        : industries[0].slug
    ))
  }, [industries, premiumHomeEnabled])

  const {
    dashboard,
    loading: roomLoading,
    error: roomError,
    lastUpdated,
    liveConnected,
    liveRevision,
    refetch: refetchRoom,
  } = useSituationRoomDashboard(
    industrySlug,
    premiumHomeEnabled && industries.length > 0,
  )

  const {
    signals,
    loading: signalsLoading,
    error: signalsError,
    activeDrawerSignal,
    openDrawer,
    openDrawerById,
    closeDrawer,
    toggleSave,
    unreadCount,
    riskCount,
    opportunityCount,
    refresh: refreshSignals,
  } = useSignals({
    enabled: !gateLoading && (!premiumHomeEnabled || Boolean(dashboard?.industry_id)),
    industryId: dashboard?.industry_id,
    mode: premiumHomeEnabled ? 'feed' : 'catalog',
    pageSize: 50,
  })

  useEffect(() => {
    if (liveRevision > 0) {
      refreshSignals()
    }
  }, [liveRevision, refreshSignals])

  const strategicStatuses = useMemo(() => {
    if (premiumHomeEnabled && dashboard) {
      return buildStrategicStatuses(dashboard.metrics)
    }

    return buildStarterStatuses(signals, {
      allocated: credits.allocated,
      remaining: credits.remaining,
    })
  }, [credits.allocated, credits.remaining, dashboard, premiumHomeEnabled, signals])
  const heatmapQuadrants = useMemo(
    () => (premiumHomeEnabled && dashboard
      ? buildHeatmapQuadrants(dashboard.metrics, dashboard.active_alerts)
      : []),
    [dashboard, premiumHomeEnabled],
  )
  const feedEvents = useMemo(
    () => (premiumHomeEnabled && dashboard
      ? buildFeedEvents(dashboard.recent_signals)
      : buildStarterFeedEvents(signals)),
    [dashboard, premiumHomeEnabled, signals],
  )

  const pageLoading = gateLoading
    || Boolean(premiumHomeEnabled && (industriesLoading || roomLoading))
    || signalsLoading
  const feedLoading = signalsLoading || Boolean(premiumHomeEnabled && roomLoading)

  const selectedIndustryName = premiumHomeEnabled
    ? dashboard?.industry_name
      ?? industries.find((industry) => industry.slug === industrySlug)?.name
      ?? 'Selected industry'
    : 'Starter Home'

  const effectiveLastUpdated = premiumHomeEnabled
    ? lastUpdated
    : (signals[0]?.publishedAt ? new Date(signals[0].publishedAt) : null)

  const criticalCount = strategicStatuses.find((status) => status.id === 'critical-alerts')?.count ?? 0
  const surfaceError = signalsError ?? (premiumHomeEnabled ? roomError ?? industriesError : null)
  const isEmpty = !feedLoading && signals.length === 0 && feedEvents.length === 0

  const handleRefresh = useCallback(() => {
    if (premiumHomeEnabled) {
      refetchRoom()
    }
    refreshSignals()
  }, [premiumHomeEnabled, refetchRoom, refreshSignals])

  if (premiumHomeEnabled && !pageLoading && !dashboard && roomError) {
    return (
      <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-6">
        <MorningBrief
          unreadCount={0}
          criticalCount={0}
          riskCount={0}
          opportunityCount={0}
          lastUpdated={effectiveLastUpdated}
          liveConnected={premiumHomeEnabled && liveConnected}
        />
        <div className="rounded-3xl border border-border bg-surface p-8 shadow-card">
          <div className="flex items-start gap-4">
            <div className="rounded-2xl bg-red-500/10 p-3 text-red-600">
              <AlertTriangle size={18} />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-heading">Home dashboard could not load</h2>
              <p className="mt-2 max-w-2xl text-sm text-subtle">{roomError}</p>
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  onClick={handleRefresh}
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
                >
                  <RefreshCw size={14} />
                  Retry
                </button>
                <button
                  onClick={() => router.push('/dashboard/signals')}
                  className="rounded-xl border border-border bg-surface px-5 py-2.5 text-sm font-medium text-body hover:bg-muted transition-colors"
                >
                  Open Signals Workspace
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div className="px-6 py-6 max-w-[1400px] mx-auto">
        <MorningBrief
          unreadCount={0}
          criticalCount={0}
          riskCount={0}
          opportunityCount={0}
          lastUpdated={effectiveLastUpdated}
          liveConnected={premiumHomeEnabled && liveConnected}
        />
        <div className="mt-10 flex flex-col items-center justify-center text-center py-20">
          <div className="rounded-2xl border border-dashed border-primary/30 bg-primary/5 p-10 max-w-lg">
            <h2 className="text-lg font-semibold text-heading mb-2">Welcome to Cogent</h2>
            <p className="text-sm text-subtle mb-6">
              {premiumHomeEnabled
                ? 'Your dashboard is ready, but there are no signals in this industry yet. Create a contract or subscribe to a marketplace source to start ingestion.'
                : 'Your starter workspace is ready, but there are no signals yet. Use your free credits to activate a source or browse the marketplace to get started.'}
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <button
                onClick={() => router.push(!premiumHomeEnabled && credits.remaining <= 0 ? '/dashboard/marketplace' : '/dashboard/studio')}
                className="rounded-xl bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
              >
                {!premiumHomeEnabled && credits.remaining <= 0 ? 'Browse Signal Marketplace' : 'Create a Contract'}
              </button>
              <button
                onClick={() => router.push('/dashboard/marketplace')}
                className="rounded-xl border border-border bg-surface px-5 py-2.5 text-sm font-medium text-body hover:bg-muted transition-colors"
              >
                Browse Signal Marketplace
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-6">
        <MorningBrief
          unreadCount={unreadCount}
          criticalCount={criticalCount}
          riskCount={riskCount}
          opportunityCount={opportunityCount}
          lastUpdated={effectiveLastUpdated}
          liveConnected={premiumHomeEnabled && liveConnected}
        />

        {!premiumHomeEnabled && (
          <div className="rounded-2xl border border-primary/15 bg-primary/5 px-4 py-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-1">
                <p className="text-sm font-medium text-heading">Starter access is active</p>
                <p className="text-sm text-subtle max-w-2xl">
                  {credits.remaining > 0
                    ? `You still have ${credits.remaining} of ${credits.allocated} free credits available. You can view signals, monitor updates, create contracts, and browse the marketplace from Home.`
                    : 'Your free credits are exhausted, but you can still use Home in read-only mode to view signals and updates. Premium Situation Room features stay locked until you upgrade or top up.'}
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => router.push(credits.remaining > 0 ? '/dashboard/studio' : '/dashboard/marketplace')}
                  className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
                >
                  {credits.remaining > 0 ? 'Use Free Credits' : 'Browse Sources'}
                </button>
                <button
                  onClick={() => router.push('/dashboard/signals')}
                  className="rounded-xl border border-border bg-surface px-4 py-2 text-sm font-medium text-body hover:bg-muted transition-colors"
                >
                  Open Signals Workspace
                </button>
              </div>
            </div>
          </div>
        )}

        {surfaceError && (
          <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 rounded-full bg-amber-500/10 p-1.5 text-amber-600">
                  <AlertTriangle size={14} />
                </div>
                <div>
                  <p className="text-sm font-medium text-heading">Some Home data is temporarily unavailable</p>
                  <p className="text-xs text-subtle">{surfaceError}</p>
                </div>
              </div>
              <button
                onClick={handleRefresh}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-[11px] font-medium text-body hover:bg-muted transition-colors"
              >
                <RefreshCw size={12} />
                Retry sync
              </button>
            </div>
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          {QUICK_ACTIONS.map(({ label, icon, href }) => (
            <button
              key={href}
              onClick={() => router.push(href)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-surface text-[11px] font-medium text-body hover:bg-muted hover:border-border-hover transition-colors"
            >
              {icon}
              {label}
            </button>
          ))}
          <button
            onClick={handleRefresh}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-border bg-surface text-[11px] font-medium text-body hover:bg-muted hover:border-border-hover transition-colors"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
          <div className="ml-auto inline-flex items-center gap-3 text-[11px] text-subtle select-none">
            <span className="inline-flex items-center gap-1">
              {liveConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
              {liveConnected ? 'Live sync connected' : 'Auto-refresh active'}
            </span>
            <kbd className="font-mono text-[10px] bg-muted border border-border px-1.5 py-0.5 rounded">⌘K</kbd>
            <span>to search</span>
          </div>
        </div>

        <section>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mb-3">
            <div>
              <h2 className="text-[13px] font-medium text-heading tracking-wide uppercase">
                Strategic Status
              </h2>
              <p className="text-[11px] text-subtle mt-0.5">
                {premiumHomeEnabled
                  ? `${selectedIndustryName} · What changed · Why it matters · What to do next`
                  : 'Starter overview · Your signals, credits, and next best actions'}
              </p>
            </div>
            {premiumHomeEnabled && (
              <select
                value={industrySlug}
                onChange={(event) => setIndustrySlug(event.target.value)}
                className="rounded-lg border border-white/10 bg-surface px-2.5 py-1 text-[11px] text-body focus:outline-none focus:ring-1 focus:ring-primary/50"
                aria-label="Select industry"
                disabled={industriesLoading || industries.length === 0}
              >
                {industries.map((industry) => (
                  <option key={industry.slug} value={industry.slug}>
                    {industry.name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
            {roomLoading
              ? Array.from({ length: 5 }).map((_, index) => (
                  <StrategicStatusCard
                    key={index}
                    status={{
                      id: `skeleton-${index}`,
                      label: '',
                      count: 0,
                      level: 'stable',
                      contextLine: '',
                      changeDetector: '',
                      suggestedAction: '',
                      trend: 'flat',
                    }}
                    loading
                  />
                ))
              : strategicStatuses.map((status) => (
                  <StrategicStatusCard
                    key={status.id}
                    status={status}
                    loading={false}
                    onClick={() => router.push(STATUS_ROUTES[status.id] ?? '/dashboard/signals')}
                  />
                ))
            }
          </div>
        </section>

        <section>
          {premiumHomeEnabled ? (
            <IntelHeatmap quadrants={heatmapQuadrants} loading={roomLoading} />
          ) : (
            <div className="bg-surface border border-border rounded-card shadow-card p-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 className="text-[14px] font-medium text-heading">Unlock Situation Room</h2>
                  <p className="mt-1 text-[11px] text-subtle max-w-2xl">
                    Paid plans add industry heatmaps, strategic status by sector, and live premium intelligence updates.
                    Your starter Home still shows signals and activity, but the advanced strategic dashboard stays premium.
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button
                    onClick={() => router.push('/dashboard/marketplace')}
                    className="rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90 transition-colors"
                  >
                    Browse Sources
                  </button>
                  <button
                    onClick={() => router.push('/dashboard/signals')}
                    className="rounded-xl border border-border bg-surface px-4 py-2 text-sm font-medium text-body hover:bg-muted transition-colors"
                  >
                    Keep Exploring Signals
                  </button>
                </div>
              </div>
            </div>
          )}
        </section>

        <section>
          {signals.length > 0 && !feedLoading && (
            <div className="mb-3 flex items-center gap-2 flex-wrap">
              <span className="text-[11px] text-subtle whitespace-nowrap">Latest on radar:</span>
              {signals.slice(0, 4).map((signal) => (
                <button
                  key={signal.id}
                  onClick={() => openDrawer(signal)}
                  className="inline-flex items-center max-w-[220px] gap-1.5 px-2.5 py-1 rounded-full border border-border bg-surface text-[11px] text-body hover:bg-muted transition-colors"
                >
                  <span className="truncate">{signal.headline || signal.domain || 'Signal'}</span>
                </button>
              ))}
            </div>
          )}
          <LiveIntelFeed
            events={feedEvents}
            signals={signals}
            loading={feedLoading}
            liveConnected={premiumHomeEnabled && liveConnected}
            onOpenSignal={(signalId) => { void openDrawerById(signalId) }}
            onViewTimeline={() => router.push('/dashboard/signals')}
            lastUpdated={lastUpdated ?? undefined}
          />
        </section>
      </div>

      <SignalDrawer
        signal={activeDrawerSignal}
        onClose={closeDrawer}
        onSave={toggleSave}
      />
    </>
  )
}
