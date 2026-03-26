/**
 * API Keys management service.
 *
 * Maps to: backend/api/v1/api_keys.py
 */

import { get, post, del } from './client';
import type {
  APIKeyResponse,
  CreateAPIKeyRequest,
  MappedCreateAPIKeyResponse,
} from './types';

interface APIKeyResponseRaw {
  id: string;
  name: string;
  description?: string | null;
  key_prefix: string;
  scopes: string[];
  rate_limit: number;
  created_at: string;
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  is_active: boolean;
}

interface CreateAPIKeyResponseRaw {
  api_key: string;
  key_id: string;
  key_prefix: string;
  expires_at: string | null;
}

function mapApiKey(raw: APIKeyResponseRaw): APIKeyResponse {
  return {
    id: raw.id,
    name: raw.name,
    description: raw.description ?? null,
    key_prefix: raw.key_prefix,
    scopes: raw.scopes,
    rate_limit: raw.rate_limit,
    created_at: raw.created_at,
    expires_at: raw.expires_at,
    last_used_at: raw.last_used_at,
    revoked_at: raw.revoked_at,
    is_active: raw.is_active,
  };
}

/** GET /api/v1/orgs/:orgId/api-keys */
export async function listApiKeys(orgId: string, includeRevoked = false) {
  const keys = await get<APIKeyResponseRaw[]>(`/orgs/${orgId}/api-keys`, {
    params: { include_revoked: includeRevoked },
  });
  return keys.map(mapApiKey);
}

/** POST /api/v1/orgs/:orgId/api-keys */
export async function createApiKey(
  orgId: string,
  body: CreateAPIKeyRequest,
): Promise<MappedCreateAPIKeyResponse> {
  const created = await post<CreateAPIKeyResponseRaw>(`/orgs/${orgId}/api-keys`, body);
  return {
    id: created.key_id,
    key: created.api_key,
    prefix: created.key_prefix,
    expires_at: created.expires_at,
  };
}

/** DELETE /api/v1/orgs/:orgId/api-keys/:keyId */
export function revokeApiKey(orgId: string, keyId: string) {
  return del(`/orgs/${orgId}/api-keys/${keyId}`);
}

export async function rotateApiKey(
  orgId: string,
  keyId: string,
  gracePeriodHours = 24,
): Promise<MappedCreateAPIKeyResponse> {
  const rotated = await post<CreateAPIKeyResponseRaw>(
    `/orgs/${orgId}/api-keys/${keyId}/rotate`,
    { grace_period_hours: gracePeriodHours },
  );
  return {
    id: rotated.key_id,
    key: rotated.api_key,
    prefix: rotated.key_prefix,
    expires_at: rotated.expires_at,
  };
}
