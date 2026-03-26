/**
 * Hook for feature gating in React components
 */

import { usePricing } from '../contexts/PricingContext';

export function useFeatureGate(featureKey: string) {
  const { features, loading, tier, featuresResolved } = usePricing();

  const hasAccess = featuresResolved ? (features?.[featureKey] ?? false) : false;

  return {
    hasAccess,
    loading,
    resolved: featuresResolved,
    isGated: featuresResolved && !hasAccess,
    currentTier: tier,
  };
}

export function useFeatures() {
  const { features, loading } = usePricing();

  return {
    features,
    loading,
    hasFeature: (featureKey: string) => features?.[featureKey] ?? false,
  };
}
