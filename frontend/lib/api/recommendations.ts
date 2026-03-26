/**
 * Recommendations API service.
 *
 * Maps to: backend/api/v1/recommendations.py
 */

import { get, post } from './client';
import type {
  RecommendationListResponse,
  RecommendationResponse,
  RecommendationBatchResponse,
} from './types';

/** GET /api/v1/recommendations/signals/:signalId */
export function getSignalRecommendations(signalId: string) {
  return get<RecommendationListResponse>(`/recommendations/signals/${signalId}`);
}

/** GET /api/v1/recommendations/active */
export function getActiveRecommendations() {
  return get<RecommendationResponse[]>('/recommendations/active');
}

/** POST /api/v1/recommendations/generate */
export function triggerRecommendationBatch() {
  return post<RecommendationBatchResponse>('/recommendations/generate');
}
