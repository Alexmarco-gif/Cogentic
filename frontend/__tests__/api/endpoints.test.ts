/**
 * Contract alignment tests for frontend API service modules.
 *
 * These tests verify that each service module hits the CORRECT endpoint
 * path with the CORRECT HTTP method. They do NOT test backend behaviour —
 * they assert that `fetch()` is called with the expected URL and method,
 * serving as a contract boundary test.
 *
 * If a backend endpoint path changes, these tests break FIRST, preventing
 * silent 404s at runtime.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// ── Helpers ───────────────────────────────────────────────────────────────────

function mockResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: 'OK',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    body: null,
  } as unknown as Response;
}

function mockTokenResponse() {
  return mockResponse({ token: 'test-token' });
}

let fetchMock: ReturnType<typeof vi.fn>;
const originalFetch = globalThis.fetch;

beforeEach(() => {
  fetchMock = vi.fn();
  globalThis.fetch = fetchMock;
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
  vi.resetModules();
});

/** Helper: returns the URL and method of the API call (second fetch after token). */
function getApiCallDetails() {
  // First call is always the token fetch; second is the actual API call
  const call = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
  return {
    url: call[0] as string,
    method: (call[1]?.method ?? 'GET') as string,
  };
}

// ── Signal endpoints ──────────────────────────────────────────────────────────

describe('Signals service endpoint paths', () => {
  it('listSignals → GET /api/v1/signals', async () => {
    const { listSignals } = await import('@/lib/api/signals');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [], total: 0, skip: 0, limit: 20 }));

    await listSignals();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toContain('/api/v1/signals');
  });

  it('getSignal → GET /api/v1/signals/:id', async () => {
    const { getSignal } = await import('@/lib/api/signals');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ id: 'abc' }));

    await getSignal('abc');
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toBe('/api/v1/signals/abc');
  });

  it('getTrendingSignals → GET /api/v1/signals/trending', async () => {
    const { getTrendingSignals } = await import('@/lib/api/signals');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse([]));

    await getTrendingSignals();
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/signals/trending');
  });

  it('getSignalsByEntity → GET /api/v1/signals/entity/:id', async () => {
    const { getSignalsByEntity } = await import('@/lib/api/signals');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

    await getSignalsByEntity('ent-1');
    const { url } = getApiCallDetails();
    expect(url).toContain('/api/v1/signals/entity/ent-1');
  });

  it('getSignalsByContract → GET /api/v1/signals/contract/:id', async () => {
    const { getSignalsByContract } = await import('@/lib/api/signals');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

    await getSignalsByContract('con-1');
    const { url } = getApiCallDetails();
    expect(url).toContain('/api/v1/signals/contract/con-1');
  });
});

// ── Brief endpoints ───────────────────────────────────────────────────────────

describe('Briefs service endpoint paths', () => {
  it('listBriefs → GET /api/v1/briefs', async () => {
    const { listBriefs } = await import('@/lib/api/briefs');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

    await listBriefs();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toContain('/api/v1/briefs');
  });

  it('getBrief → GET /api/v1/briefs/:id', async () => {
    const { getBrief } = await import('@/lib/api/briefs');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ id: 'b1' }));

    await getBrief('b1');
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/briefs/b1');
  });

  it('generateBrief → POST /api/v1/briefs/generate', async () => {
    const { generateBrief } = await import('@/lib/api/briefs');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ id: 'new' }));

    await generateBrief({ signal_id: 's1' });
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/briefs/generate');
  });
});

// ── Contract endpoints ────────────────────────────────────────────────────────

describe('Contracts service endpoint paths', () => {
  it('listContracts → GET /api/v1/contracts', async () => {
    const { listContracts } = await import('@/lib/api/contracts');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

    await listContracts();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toContain('/api/v1/contracts');
  });

  it('createContract → POST /api/v1/contracts', async () => {
    const { createContract } = await import('@/lib/api/contracts');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ id: 'c1' }));

    await createContract({ name: 'Test', schema_type: 'test' });
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/contracts');
  });

  it('deleteContract → DELETE /api/v1/contracts/:id', async () => {
    const { deleteContract } = await import('@/lib/api/contracts');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 204, statusText: 'No Content',
      headers: new Headers({ 'content-type': 'text/plain' }),
      json: () => Promise.resolve(undefined),
      text: () => Promise.resolve(''),
      body: null,
    } as unknown as Response);

    await deleteContract('c1');
    const { url, method } = getApiCallDetails();
    expect(method).toBe('DELETE');
    expect(url).toBe('/api/v1/contracts/c1');
  });
});

// ── Search endpoints ──────────────────────────────────────────────────────────

describe('Search service endpoint paths', () => {
  it('executeSearch → POST /api/v1/search', async () => {
    const { executeSearch } = await import('@/lib/api/search');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ results: [] }));

    await executeSearch({ query: 'test', limit: 10 });
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/search');
  });
});

// ── Auth endpoints ────────────────────────────────────────────────────────────

describe('Auth service endpoint paths', () => {
  it('getCurrentUser → GET /api/v1/auth/me', async () => {
    const { getCurrentUser } = await import('@/lib/api/auth');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ user: {}, organization: {} }));

    await getCurrentUser();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toBe('/api/v1/auth/me');
  });

  it('getPermissions → GET /api/v1/auth/permissions', async () => {
    const { getPermissions } = await import('@/lib/api/auth');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ permissions: {} }));

    await getPermissions();
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/auth/permissions');
  });
});

// ── User endpoints ────────────────────────────────────────────────────────────

describe('Users service endpoint paths', () => {
  it('getMyProfile → GET /api/v1/users/me', async () => {
    const { getMyProfile } = await import('@/lib/api/users');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ email: 'a@b.com' }));

    await getMyProfile();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toBe('/api/v1/users/me');
  });

  it('updateMyProfile → PATCH /api/v1/users/me', async () => {
    const { updateMyProfile } = await import('@/lib/api/users');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ name: 'New' }));

    await updateMyProfile({ name: 'New' });
    const { url, method } = getApiCallDetails();
    expect(method).toBe('PATCH');
    expect(url).toBe('/api/v1/users/me');
  });
});

// ── Pricing endpoints ─────────────────────────────────────────────────────────

describe('Pricing service endpoint paths', () => {
  it('getCurrentPricing → GET /api/v1/pricing/current', async () => {
    const { getCurrentPricing } = await import('@/lib/api/pricing');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ tier: 'explorer' }));

    await getCurrentPricing();
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/pricing/current');
  });

  it('getFeatureAccess → GET /api/v1/pricing/features', async () => {
    const { getFeatureAccess } = await import('@/lib/api/pricing');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ features: {} }));

    await getFeatureAccess();
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/pricing/features');
  });

  it('getCreditBalance → GET /api/v1/credits/balance', async () => {
    const { getCreditBalance } = await import('@/lib/api/pricing');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ balance: 1000 }));

    await getCreditBalance();
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/credits/balance');
  });
});

// ── Admin endpoints ───────────────────────────────────────────────────────────

describe('Admin service endpoint paths', () => {
  it('getPricingMode → GET /api/v1/admin/pricing/mode', async () => {
    const { getPricingMode } = await import('@/lib/api/admin');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ mode: 'standard' }));

    await getPricingMode();
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/admin/pricing/mode');
  });

  it('setPricingMode → POST /api/v1/admin/pricing/mode', async () => {
    const { setPricingMode } = await import('@/lib/api/admin');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ mode: 'standard' }));

    await setPricingMode('standard');
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/admin/pricing/mode');
  });
});

// ── Organization endpoints ────────────────────────────────────────────────────

describe('Orgs service endpoint paths', () => {
  it('getOrganization → GET /api/v1/orgs/:id', async () => {
    const { getOrganization } = await import('@/lib/api/orgs');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ id: 'org-1' }));

    await getOrganization('org-1');
    const { url } = getApiCallDetails();
    expect(url).toBe('/api/v1/orgs/org-1');
  });

  it('listMembers → GET /api/v1/orgs/:id/members', async () => {
    const { listMembers } = await import('@/lib/api/orgs');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse([]));

    await listMembers('org-1');
    const { url } = getApiCallDetails();
    expect(url).toContain('/api/v1/orgs/org-1/members');
  });
});

// ── Chat endpoints ────────────────────────────────────────────────────────────

describe('Chat service endpoint paths', () => {
  it('listChatSessions → GET /api/v1/chat/sessions', async () => {
    const { listChatSessions } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

    await listChatSessions();
    const { url } = getApiCallDetails();
    expect(url).toContain('/api/v1/chat/sessions');
  });

  it('createChatSession → POST /api/v1/chat/sessions', async () => {
    const { createChatSession } = await import('@/lib/api/chat');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ id: 's1' }));

    await createChatSession();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/chat/sessions');
  });
});

// ── Notifications endpoints ───────────────────────────────────────────────────

describe('Notifications service endpoint paths', () => {
  it('listNotifications → GET /api/v1/notifications', async () => {
    const { listNotifications } = await import('@/lib/api/notifications');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ items: [], unread_count: 0 }));

    await listNotifications();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toContain('/api/v1/notifications');
  });
});

// ── API Keys endpoints ────────────────────────────────────────────────────────

describe('API Keys service endpoint paths', () => {
  it('listApiKeys → GET /api/v1/orgs/:orgId/api-keys', async () => {
    const { listApiKeys } = await import('@/lib/api/api_keys');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse([]));

    await listApiKeys('org-1');
    const { url, method } = getApiCallDetails();
    expect(method).toBe('GET');
    expect(url).toContain('/api/v1/orgs/org-1/api-keys');
  });

  it('createApiKey → POST /api/v1/orgs/:orgId/api-keys', async () => {
    const { createApiKey } = await import('@/lib/api/api_keys');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ api_key: 'key', key_id: 'id', key_prefix: 'pre', expires_at: null }));

    await createApiKey('org-1', { name: 'test', scopes: ['read:documents'], rate_limit: 100 });
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/orgs/org-1/api-keys');
  });

  it('revokeApiKey → DELETE /api/v1/orgs/:orgId/api-keys/:keyId', async () => {
    const { revokeApiKey } = await import('@/lib/api/api_keys');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 204, statusText: 'No Content',
      headers: new Headers({ 'content-type': 'text/plain' }),
      json: () => Promise.resolve(undefined),
      text: () => Promise.resolve(''),
      body: null,
    } as unknown as Response);

    await revokeApiKey('org-1', 'key-42');
    const { url, method } = getApiCallDetails();
    expect(method).toBe('DELETE');
    expect(url).toBe('/api/v1/orgs/org-1/api-keys/key-42');
  });
});

// ── Privacy endpoints ─────────────────────────────────────────────────────────

describe('Privacy service endpoint paths', () => {
  it('clearUserHistory → DELETE /api/v1/users/me/history', async () => {
    const { clearUserHistory } = await import('@/lib/api/privacy');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ deleted_sessions: 3, message: 'ok' }));

    await clearUserHistory();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('DELETE');
    expect(url).toBe('/api/v1/users/me/history');
  });

  it('requestDataDeletion → POST /api/v1/users/me/deletion-request', async () => {
    const { requestDataDeletion } = await import('@/lib/api/privacy');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ request_id: 'r1', status: 'pending', message: 'ok' }));

    await requestDataDeletion();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/users/me/deletion-request');
  });

  it('requestDataExport → POST /api/v1/users/me/data-export-request', async () => {
    const { requestDataExport } = await import('@/lib/api/privacy');
    fetchMock.mockResolvedValueOnce(mockTokenResponse());
    fetchMock.mockResolvedValueOnce(mockResponse({ request_id: 'r2', status: 'queued', message: 'ok' }));

    await requestDataExport();
    const { url, method } = getApiCallDetails();
    expect(method).toBe('POST');
    expect(url).toBe('/api/v1/users/me/data-export-request');
  });
});

// ── Exports service endpoint paths ────────────────────────────────────────────

describe('Exports service endpoint paths', () => {
  it('exportBrief → POST /api/v1/exports/brief', async () => {
    const { exportBrief } = await import('@/lib/api/exports');
    // exports.ts uses direct fetch (binary response), mock it directly
    fetchMock.mockResolvedValueOnce(mockTokenResponse()); // token fetch
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 200, statusText: 'OK',
      headers: new Headers({ 'content-type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }),
      json: () => Promise.resolve({}),
      text: () => Promise.resolve(''),
      blob: () => Promise.resolve(new Blob([])),
      body: null,
    } as unknown as Response);

    // Mock browser APIs used by the download path
    (globalThis as Record<string, unknown>).URL = {
      createObjectURL: () => 'blob:test',
      revokeObjectURL: () => {},
    };
    (globalThis as Record<string, unknown>).document = {
      createElement: () => ({ click: () => {}, href: '', download: '' }),
    };

    await exportBrief({ title: 'Test Brief', sections: [{ heading: 'H1', content: 'C1' }], format: 'docx' });

    // Second call is the actual export request
    const exportCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
    const exportUrl = exportCall[0] as string;
    const exportMethod = (exportCall[1]?.method ?? 'GET') as string;
    expect(exportMethod).toBe('POST');
    expect(exportUrl).toContain('/api/v1/exports/brief');
  });
});
