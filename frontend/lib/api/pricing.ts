/**
 * Pricing & Credits API service.
 *
 * Maps to: backend/api/v1/pricing.py, backend/api/v1/credits.py
 */

import { get, post } from './client';
import type {
  PricingSummaryResponse,
  FeatureAccessResponse,
  CreditBalanceResponse,
  CreditTransactionsResponse,
  TierUpgradeRequest,
} from './types';

export interface TierUpgradeResponse {
  status: string;
  requested_tier: string;
  message: string;
}

// ── Pricing ──────────────────────────────────────────────────────────────────

/** GET /api/v1/pricing/current */
export function getCurrentPricing(opts?: { graceful?: boolean }) {
  return get<PricingSummaryResponse>('/pricing/current', opts);
}

/** GET /api/v1/pricing/features */
export function getFeatureAccess(opts?: { graceful?: boolean }) {
  return get<FeatureAccessResponse>('/pricing/features', opts);
}

/** POST /api/v1/pricing/upgrade */
export function upgradeTier(body: TierUpgradeRequest) {
  return post<TierUpgradeResponse>('/pricing/upgrade', body);
}

/** GET /api/v1/pricing/tiers */
export function getTierOptions() {
  return get<{ tiers: Array<{ tier: string; price: number }> }>(
    '/pricing/tiers',
    { noAuth: true },
  );
}

// ── Credits ──────────────────────────────────────────────────────────────────

/** GET /api/v1/credits/balance */
export function getCreditBalance(opts?: { graceful?: boolean }) {
  return get<CreditBalanceResponse>('/credits/balance', opts);
}

/** GET /api/v1/credits/transactions */
export function getCreditTransactions(params?: { skip?: number; limit?: number }) {
  return get<CreditTransactionsResponse>('/credits/transactions', { params: params as Record<string, string | number | boolean | undefined> });
}

/** GET /api/v1/credits/costs */
export function getCreditCosts() {
  return get<Record<string, number>>('/credits/costs', { noAuth: true });
}
