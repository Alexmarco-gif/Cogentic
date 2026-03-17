/**
 * Temporary verification tests for pre-launch frontend fixes.
 *
 * Covers (all via mocked `fetch` — no component rendering needed):
 *  1. Privacy API calls throw on non-OK responses
 *     (confirms DataPrivacySection error states will be triggered)
 *  2. Pipeline triggerTierFetch throws on non-OK response
 *     (confirms PipelinePage tierFetchError state will be triggered)
 *  3. Discovery getIndustries throws on non-OK response
 *     (confirms DiscoveryPage industriesError state will be triggered)
 *  4. Briefs listBriefs total field is passed through correctly
 *     (confirms pagination total is not silently dropped by the API client)
 *
 * Delete this file once the fixes have been verified.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ApiError } from '@/lib/api/errors';

// ── helpers ───────────────────────────────────────────────────────────────────

/** Build a minimal Response stub */
function makeResponse(status: number, body: unknown): Response {
  const json = JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => 'application/json' },
    json: async () => JSON.parse(json),
    text: async () => json,
  } as unknown as Response;
}

// ── 1. Privacy API — error propagation ───────────────────────────────────────

describe('Privacy API error propagation', () => {
  beforeEach(() => {
    // Reset fetch mock before each test
    vi.resetAllMocks();
    // Stub Auth0 token endpoint so the client doesn't fail on token fetch
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/api/auth/access-token')) {
        return Promise.resolve(makeResponse(200, { token: 'test-token' }));
      }
      return Promise.resolve(makeResponse(500, { detail: 'Internal Server Error' }));
    });
  });

  it('clearUserHistory throws ApiError on 500', async () => {
    const { clearUserHistory } = await import('@/lib/api/privacy');
    await expect(clearUserHistory()).rejects.toBeInstanceOf(ApiError);
  });

  it('requestDataDeletion throws ApiError on 500', async () => {
    const { requestDataDeletion } = await import('@/lib/api/privacy');
    await expect(requestDataDeletion()).rejects.toBeInstanceOf(ApiError);
  });

  it('requestDataExport throws ApiError on 500', async () => {
    const { requestDataExport } = await import('@/lib/api/privacy');
    await expect(requestDataExport()).rejects.toBeInstanceOf(ApiError);
  });
});

// ── 2. Pipeline triggerTierFetch — error propagation ─────────────────────────

describe('Pipeline triggerTierFetch error propagation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/api/auth/access-token')) {
        return Promise.resolve(makeResponse(200, { token: 'test-token' }));
      }
      return Promise.resolve(makeResponse(403, { detail: 'Forbidden' }));
    });
  });

  it('triggerTierFetch throws ApiError on 403', async () => {
    const { triggerTierFetch } = await import('@/lib/api/pipeline');
    await expect(triggerTierFetch({ tier: 'realtime' })).rejects.toBeInstanceOf(ApiError);
  });
});

// ── 3. Discovery getIndustries — error propagation ───────────────────────────

describe('Discovery getIndustries error propagation', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/api/auth/access-token')) {
        return Promise.resolve(makeResponse(200, { token: 'test-token' }));
      }
      return Promise.resolve(makeResponse(503, { detail: 'Service Unavailable' }));
    });
  });

  it('getIndustries throws ApiError on 503 (triggers industriesError state)', async () => {
    const { getIndustries } = await import('@/lib/api/discovered_sources');
    await expect(getIndustries()).rejects.toBeInstanceOf(ApiError);
  });
});

// ── 4. Briefs listBriefs — total field passthrough ────────────────────────────

describe('Briefs listBriefs total passthrough', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (String(url).includes('/api/auth/access-token')) {
        return Promise.resolve(makeResponse(200, { token: 'test-token' }));
      }
      // Simulate backend returning 200 items total but only 2 in this page
      return Promise.resolve(makeResponse(200, {
        items: [{ id: 'a' }, { id: 'b' }],
        total: 200,
        skip: 0,
        limit: 2,
      }));
    });
  });

  it('listBriefs returns total=200 even though only 2 items in page', async () => {
    const { listBriefs } = await import('@/lib/api/briefs');
    const result = await listBriefs({ limit: 2, skip: 0 });
    expect(result.total).toBe(200);      // true DB count
    expect(result.items.length).toBe(2); // page slice
    expect(result.total).not.toBe(result.items.length); // regression guard
  });

  it('listBriefs total is preserved across pagination calls', async () => {
    const { listBriefs } = await import('@/lib/api/briefs');
    // Both pages report same total
    const page1 = await listBriefs({ limit: 2, skip: 0 });
    const page2 = await listBriefs({ limit: 2, skip: 2 });
    expect(page1.total).toBe(page2.total);
  });
});
