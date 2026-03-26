/**
 * Monitoring API service.
 *
 * Maps to: backend/api/v1/monitoring.py
 */

import { get } from './client';
import type {
  SLOMetricsResponse,
  CacheMetricsResponse,
  CircuitBreakerResponse,
} from './types';

/** GET /api/v1/monitoring/slo */
export function getSLOMetrics() {
  return get<SLOMetricsResponse>('/monitoring/slo');
}

/** GET /api/v1/monitoring/cache */
export function getCacheMetrics() {
  return get<CacheMetricsResponse>('/monitoring/cache');
}

/** GET /api/v1/monitoring/circuit-breakers */
export function getCircuitBreakerStatus() {
  return get<CircuitBreakerResponse>('/monitoring/circuit-breakers');
}

/** GET /api/v1/monitoring/cost/budget */
export function getCostBudget() {
  return get<Record<string, unknown>>('/monitoring/cost/budget');
}

/** GET /api/v1/monitoring/cost/summary */
export function getCostSummary() {
  return get<Record<string, unknown>>('/monitoring/cost/summary');
}

/** GET /api/v1/monitoring/dlq */
export function getDeadLetterQueue() {
  return get<{ items: Array<{ id: string; error: string; created_at: string }>; total: number }>(
    '/monitoring/dlq',
  );
}

/** GET /api/v1/monitoring/health */
export function getSystemHealth() {
  return get<{ status: string; components: Record<string, { status: string; latency_ms: number }> }>(
    '/monitoring/health',
  );
}
