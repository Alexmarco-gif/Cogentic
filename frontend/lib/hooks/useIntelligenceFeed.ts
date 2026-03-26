'use client'

import { useState, useEffect } from 'react'
import { getIntelligenceFeed } from '@/lib/api/signals'
import type { IntelligenceSignalResponse } from '@/lib/api/types'

export interface IntelligenceFeedOptions {
  country?: string
  limit?: number
  latestOnly?: boolean
}

export interface UseIntelligenceFeedResult {
  items: IntelligenceSignalResponse[]
  loading: boolean
  error: string | null
  refetch: () => void
}

export function useIntelligenceFeed({
  country,
  limit = 10,
  latestOnly = true,
}: IntelligenceFeedOptions = {}): UseIntelligenceFeedResult {
  const [items, setItems]     = useState<IntelligenceSignalResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [seq, setSeq]         = useState(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getIntelligenceFeed({ country, limit, latest_only: latestOnly })
      .then((data) => {
        if (!cancelled) {
          setItems(Array.isArray(data) ? data : [])
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load intelligence feed')
          setItems([])
          setLoading(false)
        }
      })

    return () => { cancelled = true }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [country, limit, latestOnly, seq])

  return {
    items,
    loading,
    error,
    refetch: () => setSeq((s) => s + 1),
  }
}
