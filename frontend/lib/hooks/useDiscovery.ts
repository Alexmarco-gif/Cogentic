'use client'

import { useState, useEffect, useCallback } from 'react'
import { friendlyErrorMessage } from '@/lib/api'
import {
  listDiscoveredSources,
  listRecommendedSources,
  getDiscoveryStats,
  activateSource,
  dismissSource,
  listPendingEntities,
  reviewEntity,
} from '@/lib/api/discovered_sources'
import type {
  DiscoveredSourceResponse,
  DiscoveredSourceStatsResponse,
  EntityDiscoveryItem,
} from '@/lib/api/types'

// ── Source Discovery Hook ──────────────────────────────────────────────────────

export function useDiscoveredSources(
  statusFilter?: 'discovered' | 'recommended' | 'activated' | 'dismissed',
) {
  const pageSize = 25
  const [sources, setSources] = useState<DiscoveredSourceResponse[]>([])
  const [stats, setStats] = useState<DiscoveredSourceStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [sourceData, statData] = await Promise.all([
        listDiscoveredSources(
          statusFilter ? { status: statusFilter, limit: pageSize, offset: 0 } : { limit: pageSize, offset: 0 },
        ),
        getDiscoveryStats(),
      ])
      setSources(sourceData)
      setStats(statData)
      setHasMore(sourceData.length === pageSize)
    } catch (err: unknown) {
      setError(friendlyErrorMessage(err))
      setSources([])
      setHasMore(false)
    } finally {
      setLoading(false)
    }
  }, [pageSize, statusFilter])

  useEffect(() => {
    refresh()
  }, [refresh])

  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return

    setLoadingMore(true)
    setError(null)
    try {
      const more = await listDiscoveredSources(
        statusFilter
          ? { status: statusFilter, limit: pageSize, offset: sources.length }
          : { limit: pageSize, offset: sources.length },
      )
      setSources((current) => [
        ...current,
        ...more.filter((candidate) => !current.some((existing) => existing.id === candidate.id)),
      ])
      setHasMore(more.length === pageSize)
    } catch (err: unknown) {
      setError(friendlyErrorMessage(err))
    } finally {
      setLoadingMore(false)
    }
  }, [hasMore, loading, loadingMore, pageSize, sources.length, statusFilter])

  const activate = useCallback(
    async (sourceId: string, industryId: string, name?: string) => {
      try {
        setError(null)
        await activateSource(sourceId, { industry_id: industryId, name })
        await refresh()
      } catch (err: unknown) {
        const message = friendlyErrorMessage(err)
        setError(message)
        throw new Error(message)
      }
    },
    [refresh],
  )

  const dismiss = useCallback(
    async (sourceId: string) => {
      try {
        setError(null)
        await dismissSource(sourceId)
        await refresh()
      } catch (err: unknown) {
        const message = friendlyErrorMessage(err)
        setError(message)
        throw new Error(message)
      }
    },
    [refresh],
  )

  return { sources, stats, loading, loadingMore, hasMore, error, refresh, loadMore, activate, dismiss }
}

// ── Recommended Sources Hook ───────────────────────────────────────────────────

export function useRecommendedSources(limit = 10) {
  const [sources, setSources] = useState<DiscoveredSourceResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listRecommendedSources(limit)
      setSources(data)
    } catch (err) {
      setSources([])
      setError(friendlyErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { sources, loading, error, refresh }
}

// ── Entity Review Hook ─────────────────────────────────────────────────────────

export function usePendingEntities(enabled = true) {
  const pageSize = 20
  const [entities, setEntities] = useState<EntityDiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (!enabled) {
      setEntities([])
      setError(null)
      setHasMore(false)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await listPendingEntities({ limit: pageSize, offset: 0 })
      setEntities(data)
      setHasMore(data.length === pageSize)
    } catch (err: unknown) {
      setError(friendlyErrorMessage(err))
      setEntities([])
      setHasMore(false)
    } finally {
      setLoading(false)
    }
  }, [enabled, pageSize])

  useEffect(() => {
    refresh()
  }, [refresh])

  const loadMore = useCallback(async () => {
    if (!enabled || loading || loadingMore || !hasMore) return

    setLoadingMore(true)
    setError(null)
    try {
      const more = await listPendingEntities({ limit: pageSize, offset: entities.length })
      setEntities((current) => [
        ...current,
        ...more.filter((candidate) => !current.some((existing) => existing.id === candidate.id)),
      ])
      setHasMore(more.length === pageSize)
    } catch (err: unknown) {
      setError(friendlyErrorMessage(err))
    } finally {
      setLoadingMore(false)
    }
  }, [enabled, entities.length, hasMore, loading, loadingMore, pageSize])

  const approve = useCallback(
    async (entityId: string) => {
      try {
        setError(null)
        await reviewEntity(entityId, { action: 'approve' })
        await refresh()
      } catch (err: unknown) {
        const message = friendlyErrorMessage(err)
        setError(message)
        throw new Error(message)
      }
    },
    [refresh],
  )

  const reject = useCallback(
    async (entityId: string) => {
      try {
        setError(null)
        await reviewEntity(entityId, { action: 'reject' })
        await refresh()
      } catch (err: unknown) {
        const message = friendlyErrorMessage(err)
        setError(message)
        throw new Error(message)
      }
    },
    [refresh],
  )

  return { entities, loading, loadingMore, hasMore, error, refresh, loadMore, approve, reject }
}
