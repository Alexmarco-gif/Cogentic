/**
 * Admin API service.
 *
 * Maps to: backend/api/v1/admin.py
 */

import { get, post } from './client';
import type { PricingModeResponse, PricingModeRequest } from './types';

/** GET /api/v1/admin/pricing/mode */
export function getPricingMode() {
  return get<PricingModeResponse>('/admin/pricing/mode');
}

/** POST /api/v1/admin/pricing/mode */
export function setPricingMode(body: PricingModeRequest) {
  return post<{ mode: string; status: string }>('/admin/pricing/mode', body);
}

/** POST /api/v1/admin/trials/process-expiries */
export function processTrialExpiries() {
  return post<{ processed: number; errors: number }>('/admin/trials/process-expiries');
}
