'use client';

/**
 * React hooks for market data (time-series prices/rates).
 *
 * useMarketDataStats()  — dashboard-level aggregate stats
 * useMetricTrend(metric) — time-series data for charting a single metric
 * useLatestValues(metrics) — current values for a set of metrics
 * useAvailableMetrics() — list of all tracked metric names
 */

import { useCallback, useEffect, useState } from 'react';
import {
  getMarketDataStats,
  getMetricTrend,
  getLatestValues,
  listAvailableMetrics,
} from '@/lib/api/market_data';
import { friendlyErrorMessage } from '@/lib/api';
import type {
  MarketDataStatsResponse,
  MarketDataPointResponse,
  LatestValueResponse,
} from '@/lib/api/types';

// ── useMarketDataStats ──────────────────────────────────────────────────────

export function useMarketDataStats(
  countryCode?: string,
  options?: { enabled?: boolean },
) {
  const [stats, setStats] = useState<MarketDataStatsResponse | null>(null);
  const enabled = options?.enabled ?? true;
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) {
      setStats(null);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getMarketDataStats(countryCode);
      setStats(data);
    } catch (e) {
      setError(friendlyErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [countryCode, enabled]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { stats, loading, error, refresh };
}

// ── useMetricTrend ──────────────────────────────────────────────────────────

export function useMetricTrend(
  metric: string | null,
  options?: { days?: number; countryCode?: string; entityId?: string; enabled?: boolean },
) {
  const [points, setPoints] = useState<MarketDataPointResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const enabled = options?.enabled ?? true;

  const refresh = useCallback(async () => {
    if (!enabled || !metric) {
      setPoints([]);
      setTotal(0);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getMetricTrend(metric, {
        days: options?.days ?? 30,
        country_code: options?.countryCode,
        entity_id: options?.entityId,
        limit: 500,
      });
      setPoints(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(friendlyErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [enabled, metric, options?.days, options?.countryCode, options?.entityId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { points, total, loading, error, refresh };
}

// ── useLatestValues ─────────────────────────────────────────────────────────

export function useLatestValues(metrics: string[], countryCode?: string) {
  const [values, setValues] = useState<LatestValueResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (metrics.length === 0) {
      setValues([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getLatestValues(metrics, countryCode);
      setValues(data);
    } catch (e) {
      setError(friendlyErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [metrics.join(','), countryCode]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { values, loading, error, refresh };
}

// ── useAvailableMetrics ─────────────────────────────────────────────────────

export function useAvailableMetrics(countryCode?: string) {
  const [metrics, setMetrics] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listAvailableMetrics(countryCode);
      setMetrics(data);
    } catch (e) {
      setError(friendlyErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [countryCode]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { metrics, loading, error, refresh };
}
