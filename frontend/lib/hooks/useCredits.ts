/**
 * Hook for credit balance and management
 */

import { usePricing } from '../contexts/PricingContext';

export function useCredits() {
  const { credits, loading, creditsResolved } = usePricing();

  const percentage = credits.allocated > 0
    ? (credits.remaining / credits.allocated) * 100
    : 0;

  const isLow = percentage < 20;
  const hasOverage = credits.overage > 0;

  return {
    credits,
    loading,
    resolved: creditsResolved,
    percentage,
    isLow,
    hasOverage,
    overageCost: credits.overage * credits.overage_rate,
  };
}
