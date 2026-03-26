'use client';

/**
 * React hooks for signal alerts (change detection).
 *
 * useAlerts(params?)        — paginated list of alerts with filters
 * useAlertSummary()         — aggregated counts by severity and metric
 */

import { useCallback, useEffect, useState } from 'react';
import { listAlerts, getAlertSummary, acknowledgeAlert } from '@/lib/api/alerts';
import type { ListAlertsParams } from '@/lib/api/alerts';
import type { AlertListResponse, AlertSummaryResponse } from '@/lib/api/types';

// ── useAlerts ────────────────────────────────────────────────────────────────

export function useAlerts(params: ListAlertsParams = {}) {
  const [data, setData] = useState<AlertListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const paramsKey = JSON.stringify(params);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listAlerts(params);
      setData(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load alerts');
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paramsKey]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const acknowledge = useCallback(
    async (alertId: string) => {
      await acknowledgeAlert(alertId);
      await fetch();
    },
    [fetch]
  );

  return { data, loading, error, refetch: fetch, acknowledge };
}

// ── useAlertSummary ──────────────────────────────────────────────────────────

export function useAlertSummary() {
  const [summary, setSummary] = useState<AlertSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAlertSummary();
      setSummary(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load summary');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { summary, loading, error, refetch: fetch };
}
