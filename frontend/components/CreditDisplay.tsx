"use client";

import React from 'react';
import { useCreditWarning } from '@/lib/hooks/useFeatureGate';
import { AlertCircle, DollarSign } from 'lucide-react';

/**
 * Credit Display Component
 * Shows credit balance with visual indicators
 */
export function CreditDisplay() {
  const { credits, isLow, hasOverage, percentage, loading } = useCreditWarning();

  if (loading || !credits) {
    return null;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Credits</span>
        <span
          className={`text-sm font-semibold ${
            isLow ? 'text-red-600' : hasOverage ? 'text-amber-600' : 'text-gray-900'
          }`}
        >
          {credits.remaining.toLocaleString()} / {credits.allocated.toLocaleString()}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${
            isLow
              ? 'bg-red-500'
              : hasOverage
              ? 'bg-amber-500'
              : 'bg-blue-600'
          }`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>

      {/* Warning messages */}
      {hasOverage && (
        <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 p-2 rounded">
          <DollarSign className="w-4 h-4" />
          <span>
            Overage: {credits.overage.toLocaleString()} credits ($
            {(credits.overage * credits.overage_rate).toFixed(2)})
          </span>
        </div>
      )}

      {isLow && !hasOverage && (
        <div className="flex items-center gap-2 text-xs text-amber-700 bg-amber-50 p-2 rounded">
          <AlertCircle className="w-4 h-4" />
          <span>Running low on credits ({Math.round(percentage)}% remaining)</span>
        </div>
      )}
    </div>
  );
}
