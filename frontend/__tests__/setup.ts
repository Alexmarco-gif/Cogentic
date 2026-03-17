/**
 * Vitest global setup.
 *
 * Stubs `fetch` and environment variables so unit tests can run without
 * a network connection or running backend.
 */

import { vi } from 'vitest';

// Ensure NEXT_PUBLIC_API_URL is unset so the client defaults to '/api/v1'
process.env.NEXT_PUBLIC_API_URL = '';
process.env.BACKEND_URL = '';

// Provide a global fetch stub.  Individual tests override as needed.
if (typeof globalThis.fetch === 'undefined') {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
}
