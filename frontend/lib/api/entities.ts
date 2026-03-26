/**
 * Entities API service.
 *
 * Maps to: backend/api/v1/entities.py
 */

import { get, post } from './client';
import type {
  EntityResolveRequest,
  EntityResolveResponse,
  EntityCreateRequest,
  EntityCreateResponse,
  EntityProfileResponse,
  EntityNetworkResponse,
} from './types';

/** POST /api/v1/entities/resolve */
export function resolveEntity(body: EntityResolveRequest) {
  return post<EntityResolveResponse>('/entities/resolve', body);
}

/** POST /api/v1/entities */
export function createEntity(body: EntityCreateRequest) {
  return post<EntityCreateResponse>('/entities', body);
}

/** GET /api/v1/entities/:entityId/profile */
export function getEntityProfile(entityId: string) {
  return get<EntityProfileResponse>(`/entities/${entityId}/profile`);
}

/** GET /api/v1/entities/:entityId/network */
export function getEntityNetwork(entityId: string) {
  return get<EntityNetworkResponse>(`/entities/${entityId}/network`);
}

/** GET /api/v1/entities/:entityId/with-influence */
export function getEntityWithInfluence(entityId: string) {
  return get<Record<string, unknown>>(`/entities/${entityId}/with-influence`);
}

/** POST /api/v1/entities/relationships */
export function upsertRelationship(body: { source_id: string; target_id: string; relationship_type: string; weight?: number }) {
  return post<{ id: string; source_id: string; target_id: string; relationship_type: string }>(
    '/entities/relationships',
    body,
  );
}
