/**
 * Pipeline API service.
 *
 * Maps to: backend/api/v1/pipeline.py
 */

import { get, post } from './client';
import type {
  FetchTierRequest,
} from './types';

export interface PipelineAdminStatusResponse {
  scheduler_running: boolean;
  active_contracts: number;
  degraded_contracts: number;
  degraded_names: string[];
  queues: Record<string, { name: string; count: number; failed: number; scheduled: number }>;
  workers_online: number;
  workers: Array<{
    name: string;
    state: string;
    queues: string[];
    current_job_id: string | null;
    last_heartbeat: string | null;
  }>;
  provider_readiness: Record<string, boolean>;
}

/** GET /api/v1/pipeline/status */
export function getPipelineStatus() {
  return get<PipelineAdminStatusResponse>('/pipeline/status');
}

/** POST /api/v1/pipeline/fetch */
export function triggerTierFetch(body: FetchTierRequest) {
  return post<{ status: string; job_id: string }>('/pipeline/fetch', body);
}

/** GET /api/v1/pipeline/queues */
export function getPipelineQueues() {
  return get<Record<string, unknown>>('/pipeline/queues');
}

/** POST /api/v1/pipeline/scheduler/start */
export function startScheduler() {
  return post<{ status: string }>('/pipeline/scheduler/start');
}

/** POST /api/v1/pipeline/scheduler/stop */
export function stopScheduler() {
  return post<{ status: string }>('/pipeline/scheduler/stop');
}

// ── Source Health ──────────────────────────────────────────────────────────

export interface SourceHealthContract {
  id: string;
  name: string;
  source_url: string;
  source_type: string;
  schedule_tier: string;
  status: string;
  failure_count: number;
  last_fetched_at: string | null;
  last_error: string | null;
  health: 'healthy' | 'stale' | 'degraded' | 'critical';
  is_auto_discovered: boolean;
}

export interface SourceHealthSummary {
  total_active: number;
  healthy: number;
  stale: number;
  degraded: number;
  critical: number;
  stale_contracts: SourceHealthContract[];
  degraded_contracts: SourceHealthContract[];
  critical_contracts: SourceHealthContract[];
  auto_discovered_active: number;
}

export interface ContractDetailedHealth extends SourceHealthContract {
  max_failures: number;
  signals_24h: number;
  signals_7d: number;
  signals_30d: number;
  last_signal_at: string | null;
  hours_since_signal: number | null;
}

/** GET /api/v1/pipeline/source-health */
export function getSourceHealth() {
  return get<SourceHealthSummary>('/pipeline/source-health');
}

/** GET /api/v1/pipeline/source-health/:contractId */
export function getContractHealth(contractId: string) {
  return get<ContractDetailedHealth>(`/pipeline/source-health/${contractId}`);
}
