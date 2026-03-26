/**
 * Knowledge API service.
 *
 * Maps to: backend/api/v1/knowledge.py
 */

import { get } from './client';

// ── Types ────────────────────────────────────────────────────────────────────

export interface DomainOut {
  id: string;
  code: string;
  name: string;
  description: string | null;
  metadata: Record<string, unknown>;
  sort_order: number;
}

// ── Public endpoints (no auth required) ──────────────────────────────────────

/** GET /api/v1/knowledge/domains */
export function listDomains(country?: string) {
  const params: Record<string, string> = {};
  if (country) params.country = country;
  return get<DomainOut[]>('/knowledge/domains', { params });
}
