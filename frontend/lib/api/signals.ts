/**
 * Signals API service.
 *
 * Maps to: backend/api/v1/signals.py
 */

import { get } from './client';
import type {
  IntelligenceSignalResponse,
  SignalDetailResponse,
  SignalListResponse,
  SignalResponse,
} from './types';

export interface ListSignalsParams {
  skip?: number;
  limit?: number;
  signal_type?: string;
  min_confidence?: number;
}

export interface SignalFeedParams {
  skip?: number;
  limit?: number;
  signal_type?: string;
  min_confidence?: number;
  industry_id?: string;
}

export interface IntelligenceFeedParams {
  skip?: number;
  limit?: number;
  signal_type?: string;
  min_confidence?: number;
  country?: string;
  latest_only?: boolean;
  industry_id?: string;
}

/** GET /api/v1/signals */
export function listSignals(params?: ListSignalsParams) {
  return get<SignalListResponse>('/signals', { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/signals/trending */
export function getTrendingSignals() {
  return get<SignalResponse[]>('/signals/trending');
}

/** GET /api/v1/signals/feed */
export function getSignalFeed(params?: SignalFeedParams) {
  return get<SignalListResponse>('/signals/feed', { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/signals/feed/intelligence — enriched feed with scores, entities, causal */
export function getIntelligenceFeed(params?: IntelligenceFeedParams) {
  return get<IntelligenceSignalResponse[]>('/signals/feed/intelligence', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/** GET /api/v1/signals/:id */
export function getSignal(signalId: string) {
  return get<SignalDetailResponse>(`/signals/${signalId}`);
}

/** GET /api/v1/signals/entity/:entityId */
export function getSignalsByEntity(entityId: string, params?: { skip?: number; limit?: number }) {
  return get<SignalListResponse>(`/signals/entity/${entityId}`, { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/signals/contract/:contractId */
export function getSignalsByContract(contractId: string, params?: { skip?: number; limit?: number }) {
  return get<SignalListResponse>(`/signals/contract/${contractId}`, { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/signals/regions — region-level intelligence aggregates */
export function getSignalRegions() {
  return get<unknown[]>('/signals/regions');
}
