'use client'

import { useState, useEffect, useRef } from 'react'
import { listDomains, type DomainOut } from '@/lib/api/knowledge'

/**
 * Fetches domains from the backend and caches the result for the session.
 *
 * Returns:
 *   - `domains`:  Array of domain objects from the API
 *   - `names`:    Flat string array of domain names (convenience for `availableDomains` props)
 *   - `loading`:  True while the initial fetch is in-flight
 *   - `error`:    Error object if the fetch failed
 *   - `refetch`:  Manually re-trigger the fetch
 */
export function useDomains(country?: string) {
  const [domains, setDomains] = useState<DomainOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const fetchedRef = useRef(false)

  const fetchDomains = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await listDomains(country)
      setDomains(data)
      fetchedRef.current = true
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!fetchedRef.current) {
      fetchDomains()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [country])

  const names = domains.map((d) => d.name)

  return { domains, names, loading, error, refetch: fetchDomains }
}
