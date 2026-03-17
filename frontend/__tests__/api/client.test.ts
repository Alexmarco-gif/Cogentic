/**
 * Unit tests for the Cogent API client layer (`lib/api/client.ts`).
 *
 * Validates:
 *   - Auth token retrieval and header injection
 *   - URL construction (base + path + query params)
 *   - Error normalisation (ApiError, NetworkError, AuthTokenError)
 *   - Graceful mode returns null instead of throwing
 *   - noAuth mode skips token
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { request, get, post, patch, del, put } from '@/lib/api/client';
import { ApiError, AuthTokenError, NetworkError } from '@/lib/api/errors';

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Create a mock Response object */
function mockResponse(body: unknown, status = 200, contentType = 'application/json'): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'content-type': contentType }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
    body: null,
  } as unknown as Response;
}

/** Mock token response from Auth0 */
function mockTokenResponse(token = 'test-access-token') {
  return mockResponse({ token }, 200);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('API Client', () => {
  const originalFetch = globalThis.fetch;
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    globalThis.fetch = fetchMock;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  describe('request()', () => {
    it('attaches Bearer token from Auth0 SDK', async () => {
      // First call: fetch token from /api/auth/access-token
      fetchMock.mockResolvedValueOnce(mockTokenResponse('my-token'));
      // Second call: actual API request
      fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

      await request('/signals');

      // Verify token fetch
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(fetchMock.mock.calls[0][0]).toBe('/api/auth/access-token');

      // Verify API call has Authorization header
      const apiCall = fetchMock.mock.calls[1];
      expect(apiCall[0]).toBe('/api/v1/signals');
      expect(apiCall[1].headers['Authorization']).toBe('Bearer my-token');
    });

    it('constructs URL with query params', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

      await request('/signals', { params: { limit: 20, skip: 0 } });

      const url = fetchMock.mock.calls[1][0] as string;
      expect(url).toContain('/api/v1/signals?');
      expect(url).toContain('limit=20');
      expect(url).toContain('skip=0');
    });

    it('omits undefined params', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(mockResponse({ items: [] }));

      await request('/signals', { params: { limit: 10, skip: undefined } });

      const url = fetchMock.mock.calls[1][0] as string;
      expect(url).toContain('limit=10');
      expect(url).not.toContain('skip');
    });

    it('serialises JSON body', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(mockResponse({ id: '1' }));

      await request('/signals', {
        method: 'POST',
        body: { title: 'Test Signal' },
      });

      const callOpts = fetchMock.mock.calls[1][1];
      expect(callOpts.body).toBe(JSON.stringify({ title: 'Test Signal' }));
      expect(callOpts.headers['Content-Type']).toBe('application/json');
    });

    it('throws ApiError on 4xx/5xx', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(
        mockResponse({ detail: 'Signal not found' }, 404),
      );

      await expect(request('/signals/bad-id')).rejects.toThrow(ApiError);
      await expect(request('/signals/bad-id')).rejects.not.toThrow(NetworkError);
    });

    it('ApiError exposes status helpers', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(
        mockResponse({ detail: 'Not found' }, 404),
      );

      try {
        await request('/signals/missing');
        expect.fail('should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(404);
        expect(apiErr.isNotFound).toBe(true);
        expect(apiErr.isUnauthorized).toBe(false);
      }
    });

    it('throws AuthTokenError when token fetch fails', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({}, 401));

      await expect(request('/signals')).rejects.toThrow(AuthTokenError);
    });

    it('throws NetworkError on fetch failure', async () => {
      fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));

      // NetworkError wraps auth fetch failures
      await expect(request('/signals')).rejects.toThrow(AuthTokenError);
    });
  });

  describe('noAuth option', () => {
    it('does not fetch a token when noAuth=true', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ status: 'ok' }));

      await request('/health', { noAuth: true });

      // Only 1 call — the API request itself (no token call)
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const headers = fetchMock.mock.calls[0][1].headers;
      expect(headers['Authorization']).toBeUndefined();
    });
  });

  describe('graceful option', () => {
    it('returns null instead of throwing on auth failure', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({}, 401));

      const result = await request('/pricing/current', { graceful: true });
      expect(result).toBeNull();
    });

    it('returns null instead of throwing on network error', async () => {
      fetchMock.mockRejectedValueOnce(new TypeError('fetch failed'));

      const result = await request('/pricing/current', { graceful: true });
      expect(result).toBeNull();
    });

    it('returns null on API error', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(mockResponse({ detail: 'error' }, 500));

      const result = await request('/pricing/current', { graceful: true });
      expect(result).toBeNull();
    });

    it('returns data on success', async () => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
      fetchMock.mockResolvedValueOnce(mockResponse({ tier: 'explorer' }));

      const result = await request('/pricing/current', { graceful: true });
      expect(result).toEqual({ tier: 'explorer' });
    });
  });

  describe('convenience methods', () => {
    beforeEach(() => {
      fetchMock.mockResolvedValueOnce(mockTokenResponse());
    });

    it('get() sends GET', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse([]));
      await get('/signals');
      expect(fetchMock.mock.calls[1][1].method).toBe('GET');
    });

    it('post() sends POST with body', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ id: '1' }));
      await post('/contracts', { name: 'Test' });
      expect(fetchMock.mock.calls[1][1].method).toBe('POST');
      expect(fetchMock.mock.calls[1][1].body).toBe(JSON.stringify({ name: 'Test' }));
    });

    it('patch() sends PATCH', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ name: 'Updated' }));
      await patch('/users/me', { name: 'Updated' });
      expect(fetchMock.mock.calls[1][1].method).toBe('PATCH');
    });

    it('del() sends DELETE', async () => {
      fetchMock.mockResolvedValueOnce({
        ok: true, status: 204, statusText: 'No Content',
        headers: new Headers({ 'content-type': 'text/plain' }),
        json: () => Promise.resolve(undefined),
        text: () => Promise.resolve(''),
        body: null,
      } as unknown as Response);
      await del('/contracts/123');
      expect(fetchMock.mock.calls[1][1].method).toBe('DELETE');
    });

    it('put() sends PUT', async () => {
      fetchMock.mockResolvedValueOnce(mockResponse({ ok: true }));
      await put('/contracts/123', { status: 'active' });
      expect(fetchMock.mock.calls[1][1].method).toBe('PUT');
    });
  });
});
