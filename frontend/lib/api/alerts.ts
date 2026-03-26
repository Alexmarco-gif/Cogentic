/**
 * Signal Alerts API service.
 *
 * Maps to: backend/api/v1/alerts.py
 *
 * Change-detection alerts generated when MarketDataPoint values
 * deviate significantly from their rolling 30-day baseline.
 */

import { get, post } from './client';
import type {
  AlertListResponse,
  AlertSummaryResponse,
  AcknowledgeResponse,
} from './types';

// ── Query params ─────────────────────────────────────────────────────────────

export interface ListAlertsParams {
  severity?: 'low' | 'medium' | 'high' | 'critical';
  metric?: string;
  country_code?: string;
  acknowledged?: boolean;
  alert_type?: 'anomaly' | 'threshold' | 'trend_break';
  skip?: number;
  limit?: number;
}

// ── API functions ─────────────────────────────────────────────────────────────

export async function listAlerts(
  params: ListAlertsParams = {}
): Promise<AlertListResponse> {
  const query = new URLSearchParams();
  if (params.severity) query.set('severity', params.severity);
  if (params.metric) query.set('metric', params.metric);
  if (params.country_code) query.set('country_code', params.country_code);
  if (params.acknowledged !== undefined)
    query.set('acknowledged', String(params.acknowledged));
  if (params.alert_type) query.set('alert_type', params.alert_type);
  if (params.skip !== undefined) query.set('skip', String(params.skip));
  if (params.limit !== undefined) query.set('limit', String(params.limit));
  const qs = query.toString();
  return get<AlertListResponse>(`/alerts${qs ? `?${qs}` : ''}`);
}

export async function getAlertSummary(): Promise<AlertSummaryResponse> {
  return get<AlertSummaryResponse>('/alerts/summary');
}

export async function acknowledgeAlert(alertId: string): Promise<AcknowledgeResponse> {
  return post<AcknowledgeResponse>(`/alerts/${alertId}/acknowledge`, {});
}
