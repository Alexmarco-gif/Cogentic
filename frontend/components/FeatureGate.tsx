"use client";

import React from 'react';
import { useFeatureGate } from '@/lib/hooks/useFeatureGate';
import { UpgradePrompt } from './UpgradePrompt';

interface FeatureGateProps {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  showUpgradePrompt?: boolean;
}

/**
 * Feature Gate Component
 * Conditionally renders children based on feature access
 *
 * @param feature - Feature key to check
 * @param children - Content to show if access granted
 * @param fallback - Content to show if access denied (optional)
 * @param showUpgradePrompt - Show upgrade prompt instead of fallback (default: true)
 */
export function FeatureGate({
  feature,
  children,
  fallback,
  showUpgradePrompt = true,
}: FeatureGateProps) {
  const { hasAccess, loading, resolved } = useFeatureGate(feature);

  if (loading) {
    return (
      <div className="animate-pulse bg-gray-100 rounded-lg p-4">
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
      </div>
    );
  }

  if (!resolved) {
    return <>{children}</>;
  }

  if (!hasAccess) {
    if (showUpgradePrompt) {
      return <UpgradePrompt feature={feature} />;
    }
    return <>{fallback}</>;
  }

  return <>{children}</>;
}
