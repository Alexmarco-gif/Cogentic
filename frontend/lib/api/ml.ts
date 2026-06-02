/**
 * ML API service.
 *
 * Maps to: backend/api/v1/ml.py
 */

import { get, post } from './client';
import type {
  SignalScoresResponse,
  MLStatusResponse,
  MLModelRunResponse,
  MLModelRegistryResponse,
  TrainingRequest,
  TrainingResponse,
  TrainAllQueuedResponse,
  RefinementResponse,
} from './types';

/** GET /api/v1/ml/signals/:signalId/scores */
export function getSignalScores(signalId: string) {
  return get<SignalScoresResponse>(`/ml/signals/${signalId}/scores`);
}

/** GET /api/v1/ml/status */
export function getMLStatus() {
  return get<MLStatusResponse>('/ml/status');
}

/** GET /api/v1/ml/runs */
export function getModelRuns() {
  return get<MLModelRunResponse[]>('/ml/runs');
}

/** GET /api/v1/ml/registry */
export function getModelRegistry() {
  return get<MLModelRegistryResponse[]>('/ml/registry');
}

/** POST /api/v1/ml/train */
export function trainModel(body: TrainingRequest) {
  return post<TrainingResponse>('/ml/train', body);
}

/** POST /api/v1/ml/train/all */
export function trainAllModels() {
  return post<TrainAllQueuedResponse>('/ml/train/all');
}

/** POST /api/v1/ml/refine/unprocessed */
export function refineUnprocessed() {
  return post<RefinementResponse>('/ml/refine/unprocessed');
}
