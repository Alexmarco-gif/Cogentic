"use client";

import React from 'react';
import { usePricing } from '@/lib/contexts/PricingContext';
import { AlertTriangle, Info } from 'lucide-react';

/**
 * Beta Banner Component
 * Shows beta pricing status and expiration warning
 */
export function BetaBanner() {
  const { isBeta, betaEnds } = usePricing();

  if (!isBeta || !betaEnds) {
    return null;
  }

  const endDate = new Date(betaEnds);
  const daysRemaining = Math.ceil(
    (endDate.getTime() - Date.now()) / (1000 * 60 * 60 * 24)
  );

  const isUrgent = daysRemaining <= 14;

  return (
    <div
      className={`${
        isUrgent
          ? 'bg-amber-50 border-amber-400'
          : 'bg-blue-50 border-blue-400'
      } border-l-4 p-4 mb-6`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {isUrgent ? (
            <AlertTriangle className="w-5 h-5 text-amber-600" />
          ) : (
            <Info className="w-5 h-5 text-blue-600" />
          )}
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900">
            <span className="font-semibold">Beta Pricing Active:</span> Your 50%
            discount ends in {daysRemaining} day{daysRemaining !== 1 ? 's' : ''}.
          </p>
          <p className="mt-1 text-xs text-gray-600">
            Standard pricing will apply starting{' '}
            {endDate.toLocaleDateString('en-US', {
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
            .
          </p>
          {isUrgent && (
            <button
              onClick={() => (window.location.href = '/pricing')}
              className="mt-2 text-xs font-medium text-amber-700 hover:text-amber-800 underline"
            >
              View pricing details →
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
