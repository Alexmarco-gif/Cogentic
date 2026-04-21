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
import { friendlyErrorMessage } from '@/lib/api';

// ── useAlerts ────────────────────────────────────────────────────────────────

export function useAlerts(params: ListAlertsParams = {}) {
  const [data, setData] = useState<AlertListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const paramsKey = JSON.stringify(params);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listAlerts(params);
      setData(result);
    } catch (e: unknown) {
      setError(friendlyErrorMessage(e));
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
      setAcknowledgingId(alertId);
      setActionError(null);
      try {
        await acknowledgeAlert(alertId);
        await fetch();
      } catch (e: unknown) {
        setActionError(friendlyErrorMessage(e));
      } finally {
        setAcknowledgingId(null);
      }
    },
    [fetch]
  );

  return { data, loading, error, actionError, acknowledgingId, refetch: fetch, acknowledge };
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
      setError(friendlyErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { summary, loading, error, refetch: fetch };
}
