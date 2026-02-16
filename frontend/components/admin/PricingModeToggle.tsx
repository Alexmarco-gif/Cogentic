"use client";

import React, { useState } from 'react';
import { Switch } from '@headlessui/react';

/**
 * Admin component for toggling global pricing mode
 */
export function PricingModeToggle() {
  const [mode, setMode] = useState<'beta' | 'standard'>('beta');
  const [loading, setLoading] = useState(false);

  const toggleMode = async () => {
    setLoading(true);
    try {
      const newMode = mode === 'beta' ? 'standard' : 'beta';

      const response = await fetch('/api/v1/admin/pricing/mode', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mode: newMode }),
      });

      if (!response.ok) {
        throw new Error('Failed to update pricing mode');
      }

      setMode(newMode);
    } catch (error) {
      console.error('Failed to toggle pricing mode:', error);
      alert('Failed to update pricing mode. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    // Fetch current mode on mount
    fetch('/api/v1/admin/pricing/mode')
      .then((res) => res.json())
      .then((data) => setMode(data.mode))
      .catch(console.error);
  }, []);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">
          Global Pricing Mode
        </h3>
        <p className="mt-2 text-sm text-gray-600">
          Controls whether new accounts receive beta pricing or standard pricing.
        </p>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Current Mode:</span>
          <span
            className={`px-3 py-1 rounded-full text-sm font-semibold ${
              mode === 'beta'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {mode.toUpperCase()}
          </span>
        </div>

        <Switch
          checked={mode === 'beta'}
          onChange={toggleMode}
          disabled={loading}
          className={`${
            mode === 'beta' ? 'bg-blue-600' : 'bg-gray-400'
          } relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50`}
        >
          <span
            className={`${
              mode === 'beta' ? 'translate-x-6' : 'translate-x-1'
            } inline-block h-4 w-4 transform rounded-full bg-white transition-transform`}
          />
        </Switch>
      </div>

      <div className="pt-2 border-t border-gray-200">
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="font-medium text-gray-500">Beta Mode</dt>
            <dd className="mt-1 text-gray-900">50% discount for new accounts</dd>
          </div>
          <div>
            <dt className="font-medium text-gray-500">Standard Mode</dt>
            <dd className="mt-1 text-gray-900">Full price for new accounts</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
