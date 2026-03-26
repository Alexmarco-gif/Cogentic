/**
 * Cogent API Layer — barrel export.
 *
 * Import from `@/lib/api` throughout the frontend.
 *
 * Usage:
 *   import { listSignals, type SignalListResponse } from '@/lib/api';
 *   import { ApiError, isApiError } from '@/lib/api';
 */

// ── Client primitives ────────────────────────────────────────────────────────
export { request, get, post, patch, put, del, streamSSE, getAccessToken, getAccessTokenSilent } from './client';
export type { RequestOptions, SSECallbacks } from './client';

// ── Error types ──────────────────────────────────────────────────────────────
export {
  ApiError,
  AuthTokenError,
  NetworkError,
  isApiError,
  isAuthTokenError,
  isNetworkError,
  friendlyErrorMessage,
} from './errors';

// ── All TS types (backend schema mirrors) ────────────────────────────────────
export type * from './types';

// ── Service modules ──────────────────────────────────────────────────────────
export * from './auth';
export * from './users';
export * from './orgs';
export * from './signals';
export * from './contracts';
export * from './briefs';
export * from './search';
export * from './chat';
export * from './pricing';
export * from './admin';
export * from './entities';
export * from './feedback';
export * from './recommendations';
export * from './features';
export * from './causal';
export * from './pipeline';
export * from './ml';
export * from './monitoring';

// Knowledge base
export * from './knowledge';

// Dynamic Intelligence (entity discovery + living contracts)
export * from './discovered_sources';

// Market data (time-series prices/rates)
export * from './market_data';

// Signal alerts (change detection)
export * from './alerts';

// Platform utilities
export * from './exports';
export * from './notifications';
export * from './api_keys';
export * from './privacy';
export * from './sessions';

// Signal Marketplace
export * from './marketplace';

// Situation Room (live industry dashboards)
export * from './situation_room';
