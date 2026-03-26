/**
 * Features API service.
 *
 * Maps to: backend/api/v1/features.py
 */

import { get } from './client';
import type { FeaturesResponse } from './types';

/** GET /api/v1/features */
export function listFeatures() {
  return get<FeaturesResponse>('/features');
}

/** GET /api/v1/features/:featureName */
export function checkFeature(featureName: string) {
  return get<{ enabled: boolean; feature: string }>(`/features/${featureName}`);
}
