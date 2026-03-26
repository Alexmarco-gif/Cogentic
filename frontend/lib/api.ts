/**
 * Legacy API client — re-exports from the new centralized API layer.
 *
 * @deprecated Import from `@/lib/api` (the directory module) instead.
 *
 * This file is preserved for backward compatibility. All new code should
 * import from `@/lib/api/index.ts` (or shorthand `@/lib/api`).
 */

// Re-export everything from the new centralized module (functions, types, errors, services)
export * from './api/index';

// Preserve the legacy fetchWithAuth for any remaining consumers
import { getAccessToken as _getToken } from './api/client';

/** @deprecated Use service methods from `@/lib/api` instead. */
export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await _getToken();
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
}
