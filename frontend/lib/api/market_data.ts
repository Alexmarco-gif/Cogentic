/**
 * Market Data API service.
 *
 * Maps to: backend/api/v1/market_data.py
 *
 * Time-series price/rate data extracted from signals by NER.
 * Supports filtering, trend queries, latest values, and stats.
 */

import { get } from './client';
import type {
  MarketDataListResponse,
  MarketDataStatsResponse,
  LatestValueResponse,
} from './types';

// ── Query params ────────────────────────────────────────────────────────────

export interface ListMarketDataParams {
  metric?: string;
  entity_id?: string;
  country_code?: string;
  since?: string;       // ISO datetime
  until?: string;       // ISO datetime
  min_confidence?: number;
  skip?: number;
  limit?: number;
}

export interface TrendParams {
  entity_id?: string;
  country_code?: string;
  days?: number;
  skip?: number;
  limit?: number;
}

// ── Endpoints ───────────────────────────────────────────────────────────────

/** GET /api/v1/market-data */
export function listMarketData(params?: ListMarketDataParams) {
  return get<MarketDataListResponse>('/market-data', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/** GET /api/v1/market-data/stats */
export function getMarketDataStats(countryCode?: string) {
  return get<MarketDataStatsResponse>('/market-data/stats', {
    params: countryCode ? { country_code: countryCode } : undefined,
  });
}

/** GET /api/v1/market-data/latest?metrics=... */
export function getLatestValues(metrics: string[], countryCode?: string) {
  return get<LatestValueResponse[]>('/market-data/latest', {
    params: {
      metrics: metrics.join(','),
      ...(countryCode ? { country_code: countryCode } : {}),
    },
  });
}

/** GET /api/v1/market-data/trend/:metric */
export function getMetricTrend(metric: string, params?: TrendParams) {
  return get<MarketDataListResponse>(`/market-data/trend/${encodeURIComponent(metric)}`, {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/** GET /api/v1/market-data/metrics */
export function listAvailableMetrics(countryCode?: string) {
  return get<string[]>('/market-data/metrics', {
    params: countryCode ? { country_code: countryCode } : undefined,
  });
}
