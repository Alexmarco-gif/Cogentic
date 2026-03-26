/**
 * Feedback API service.
 *
 * Maps to: backend/api/v1/feedback.py
 */

import { get, post } from './client';
import type {
  FeedbackRequest,
  FeedbackResponse,
  SignalQualityResponse,
  TrendingSignalResponse,
} from './types';

/** POST /api/v1/feedback */
export function submitFeedback(body: FeedbackRequest) {
  return post<FeedbackResponse>('/feedback', body);
}

/** GET /api/v1/feedback/signal/:signalId/quality */
export function getSignalQuality(signalId: string) {
  return get<SignalQualityResponse>(`/feedback/signal/${signalId}/quality`);
}

/** GET /api/v1/feedback/trending */
export function getTrendingByFeedback() {
  return get<TrendingSignalResponse[]>('/feedback/trending');
}

/** GET /api/v1/feedback/predictions/accuracy */
export function getPredictionAccuracy() {
  return get<Record<string, unknown>>('/feedback/predictions/accuracy');
}

/** GET /api/v1/feedback/me/summary */
export function getMyFeedbackSummary() {
  return get<Record<string, unknown>>('/feedback/me/summary');
}
