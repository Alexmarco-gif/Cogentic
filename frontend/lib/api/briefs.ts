/**
 * Briefs API service.
 *
 * Maps to: backend/api/v1/briefs.py
 */

import { get, post, patch } from './client';
import type {
  BriefListResponse,
  BriefDetailResponse,
  BriefResponse,
  BriefGenerateRequest,
  BriefGenerateResponse,
  BriefRegenerateRequest,
  BriefStatusUpdate,
  BriefRefreshResponse,
  BriefRefreshBatchResponse,
} from './types';

export interface ListBriefsParams {
  skip?: number;
  limit?: number;
  brief_type?: string;
  status?: string;
}

/** GET /api/v1/briefs */
export function listBriefs(params?: ListBriefsParams) {
  return get<BriefListResponse>('/briefs', { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/briefs/:id */
export function getBrief(briefId: string) {
  return get<BriefDetailResponse>(`/briefs/${briefId}`);
}

/** POST /api/v1/briefs/generate */
export function generateBrief(body: BriefGenerateRequest) {
  return post<BriefGenerateResponse>('/briefs/generate', body);
}

/** POST /api/v1/briefs/:id/regenerate */
export function regenerateBrief(briefId: string, body?: BriefRegenerateRequest) {
  return post<BriefGenerateResponse>(`/briefs/${briefId}/regenerate`, body);
}

/** PATCH /api/v1/briefs/:id/status */
export function updateBriefStatus(briefId: string, body: BriefStatusUpdate) {
  return patch<BriefResponse>(`/briefs/${briefId}/status`, body);
}

/** POST /api/v1/briefs/:id/refresh */
export function refreshBrief(briefId: string) {
  return post<BriefRefreshResponse>(`/briefs/${briefId}/refresh`);
}

/** POST /api/v1/briefs/refresh-all */
export function refreshAllBriefs() {
  return post<BriefRefreshBatchResponse>('/briefs/refresh-all');
}
