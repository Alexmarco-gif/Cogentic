/**
 * Situation Room API service.
 *
 * Maps to: backend/api/v1/situation_room.py
 */

import { get } from './client';
import type { SituationRoomDashboard } from './types';

export interface SituationRoomParams {
  signal_types?: string;
  min_confidence?: number;
  hours?: number;
  limit?: number;
}

/** GET /api/v1/situation-room/{industry_slug} */
export function getSituationRoomDashboard(
  industrySlug: string,
  params?: SituationRoomParams,
) {
  return get<SituationRoomDashboard>(`/situation-room/${industrySlug}`, {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}
