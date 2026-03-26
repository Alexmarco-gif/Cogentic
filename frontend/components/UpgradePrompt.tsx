"use client";

import React from 'react';
import { usePricing } from '@/lib/contexts/PricingContext';
import { ArrowUpCircle } from 'lucide-react';

interface UpgradePromptProps {
  feature: string;
}

const FEATURE_TIER_MAP: Record<string, string> = {
  'continuous_signals_full': 'Growth',
  'on_demand_synthesis': 'Growth',
  'api_access': 'Growth',
  'compliance_modules': 'Mid-Market',
  'custom_contracts': 'Mid-Market',
  'private_signal_store': 'Enterprise',
};

/**
 * Upgrade Prompt Component
 * Shows upgrade CTA when feature is gated
 */
export function UpgradePrompt({ feature }: UpgradePromptProps) {
  const { tier } = usePricing();

  const requiredTier = FEATURE_TIER_MAP[feature] || 'Growth';

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6 space-y-4">
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          <ArrowUpCircle className="w-8 h-8 text-blue-600" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">
            Upgrade Required
          </h3>
          <p className="mt-2 text-sm text-gray-600">
            This feature requires{' '}
            <span className="font-semibold text-blue-700">{requiredTier}</span>{' '}
            tier or higher.
          </p>
          <p className="mt-1 text-xs text-gray-500">
            Current tier:{' '}
            <span className="capitalize font-medium">{tier}</span>
          </p>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => (window.location.href = '/dashboard/settings?tab=plan')}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
        >
          View Pricing
        </button>
        <button
          onClick={() => (window.location.href = '/dashboard/settings?tab=plan')}
          className="px-4 py-2 bg-white border border-blue-300 text-blue-700 text-sm font-medium rounded-md hover:bg-blue-50 transition-colors"
        >
          Upgrade Now
        </button>
      </div>
    </div>
  );
}
