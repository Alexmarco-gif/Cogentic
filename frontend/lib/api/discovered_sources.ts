/**
 * Discovered Sources API service.
 *
 * Maps to: backend/api/v1/discovered_sources.py
 *
 * Discovered sources are URLs the system finds during signal refinement.
 * Once they hit enough mentions / relevance they become "recommended"
 * and can be promoted into full signal contracts ("living contracts").
 */

import { get, post } from './client';
import type {
  DiscoveredSourceResponse,
  DiscoveredSourceStatsResponse,
  ActivateSourceRequest,
  ActivateSourceResponse,
  EntityDiscoveryItem,
  EntityReviewRequest,
  EntityReviewResponse,
} from './types';

// ── Discovered Sources ──────────────────────────────────────────────────────

export interface ListDiscoveredSourcesParams {
  status?: 'discovered' | 'recommended' | 'activated' | 'dismissed';
  domain?: string;
  min_relevance?: number;
  limit?: number;
  offset?: number;
}

/** GET /api/v1/discovered-sources */
export function listDiscoveredSources(params?: ListDiscoveredSourcesParams) {
  return get<DiscoveredSourceResponse[]>('/discovered-sources', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/** GET /api/v1/discovered-sources/recommended */
export function listRecommendedSources(limit = 20) {
  return get<DiscoveredSourceResponse[]>('/discovered-sources/recommended', {
    params: { limit },
  });
}

/** GET /api/v1/discovered-sources/stats */
export function getDiscoveryStats() {
  return get<DiscoveredSourceStatsResponse>('/discovered-sources/stats');
}

/** POST /api/v1/discovered-sources/:id/activate */
export function activateSource(sourceId: string, body: ActivateSourceRequest) {
  return post<ActivateSourceResponse>(`/discovered-sources/${sourceId}/activate`, body);
}

/** POST /api/v1/discovered-sources/:id/dismiss */
export function dismissSource(sourceId: string) {
  return post<{ source_id: string; status: string; message: string }>(
    `/discovered-sources/${sourceId}/dismiss`,
  );
}

// ── Entity Discovery Review ─────────────────────────────────────────────────

export interface ListPendingEntitiesParams {
  discovery_source?: 'auto_extracted' | 'agent';
  limit?: number;
  offset?: number;
}

/** GET /api/v1/entities/discovery/pending */
export function listPendingEntities(params?: ListPendingEntitiesParams) {
  return get<EntityDiscoveryItem[]>('/entities/discovery/pending', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

/** POST /api/v1/entities/:id/review */
export function reviewEntity(entityId: string, body: EntityReviewRequest) {
  return post<EntityReviewResponse>(`/entities/${entityId}/review`, body);
}

// ── Industries ──────────────────────────────────────────────────────────────

export interface IndustryItem {
  id: string
  name: string
  slug: string
}

/** GET /api/v1/industries */
export function getIndustries() {
  return get<IndustryItem[]>('/industries');
}
