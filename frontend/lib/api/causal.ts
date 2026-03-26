/**
 * Causal Intelligence API service.
 *
 * Maps to: backend/api/v1/causal.py
 */

import { get, post } from './client';
import type {
  CausalChainResponse,
  ImpactPredictionResponse,
  GrangerTestRequest,
  GrangerTestResponse,
  SignalImpactResponse,
} from './types';

/** GET /api/v1/causal/chains/:eventType */
export function getCausalChains(eventType: string) {
  return get<CausalChainResponse[]>(`/causal/chains/${eventType}`);
}

/** GET /api/v1/causal/predict/:eventType */
export function predictImpacts(eventType: string) {
  return get<ImpactPredictionResponse>(`/causal/predict/${eventType}`);
}

/** POST /api/v1/causal/granger-test */
export function testGrangerCausality(body: GrangerTestRequest) {
  return post<GrangerTestResponse>('/causal/granger-test', body);
}

/** GET /api/v1/causal/signal/:signalId/impact */
export function analyzeSignalImpact(signalId: string) {
  return get<SignalImpactResponse>(`/causal/signal/${signalId}/impact`);
}

/** GET /api/v1/causal/precedents/:eventType */
export function getHistoricalPrecedents(eventType: string) {
  return get<Record<string, unknown>>(`/causal/precedents/${eventType}`);
}

/** POST /api/v1/causal/counterfactual */
export function estimateCounterfactual(body: { signal_id: string; scenario: string }) {
  return post<Record<string, unknown>>('/causal/counterfactual', body);
}

/** POST /api/v1/causal/did */
export function differenceInDifferences(body: { treatment_group: string; control_group: string; event_date: string }) {
  return post<Record<string, unknown>>('/causal/did', body);
}
