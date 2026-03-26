import { NextResponse } from 'next/server';
import React from 'react';

/**
 * Environment Gate Utility
 *
 * Restricts access to development-only pages in production
 * Use this in pages that should not be accessible in production
 */

/**
 * Check if development-only features are enabled
 *
 * @returns true if dev features should be available
 */
export function isDevEnvironment(): boolean {
  return process.env.NODE_ENV === 'development';
}

/**
 * Redirect to home if not in development environment
 * Use this at the top of dev-only pages
 *
 * Example:
 * ```tsx
 * import { requireDevEnvironment } from '@/lib/dev-gate';
 *
 * export default function DevOnlyPage() {
 *   requireDevEnvironment();
 *   // ... rest of component
 * }
 * ```
 */
export function requireDevEnvironment() {
  if (!isDevEnvironment()) {
    return NextResponse.redirect(new URL('/', process.env.AUTH0_BASE_URL || 'http://localhost:3000'));
  }
}

/**
 * Component wrapper for development-only pages
 *
 * Usage in server component:
 * ```tsx
 * import { DevGate } from '@/lib/dev-gate';
 *
 * export default function Page() {
 *   return (
 *     <DevGate>
 *       <YourDevContent />
 *     </DevGate>
 *   );
 * }
 * ```
 */
export function DevGate({ children }: { children: React.ReactNode }) {
  if (!isDevEnvironment()) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center p-8">
          <h1 className="text-2xl font-bold text-gray-800 mb-4">
            🚫 Development Only
          </h1>
          <p className="text-gray-600 mb-6">
            This page is only available in development environment.
          </p>
          <a
            href="/"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-block"
          >
            Go Home
          </a>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Server action to check environment
 * Returns null in production, content in development
 */
export async function devOnly<T>(content: T): Promise<T | null> {
  return isDevEnvironment() ? content : null;
}
