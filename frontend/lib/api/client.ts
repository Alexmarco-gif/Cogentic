/**
 * Centralized API client for the Cogent frontend.
 *
 * Every backend call should go through `apiClient` (or one of the service
 * modules that wrap it). This ensures:
 *
 *   1. Auth token is always attached (via Auth0 SDK).
 *   2. Errors are normalised into typed exceptions (see `./errors.ts`).
 *   3. Base URL is configurable via environment variable.
 *   4. Responses are parsed with a single try/catch path.
 *
 * The base URL defaults to the Next.js rewrite proxy (`/api/v1`) so the
 * browser never talks to the backend directly.
 */

import { ApiError, AuthTokenError, NetworkError } from './errors';

// ── Configuration ────────────────────────────────────────────────────────────

/**
 * Browser traffic should default to the same-origin Next.js proxy so we avoid
 * CSP/CORS drift between environments. Direct browser-to-backend calls remain
 * available behind an explicit opt-in for exceptional deployments.
 */
const API_BASE =
  (typeof window !== 'undefined'
    ? (
        process.env.NEXT_PUBLIC_DIRECT_API === 'true'
          ? (process.env.NEXT_PUBLIC_API_URL ?? '')
          : ''
      )
    : (process.env.BACKEND_URL ?? '')) || '';

const API_PREFIX = '/api/v1';

// ── Token retrieval ──────────────────────────────────────────────────────────

/**
 * Fetches a fresh access token from the Auth0 SDK route.
 * Throws `AuthTokenError` on failure.
 */
async function getAccessToken(): Promise<string> {
  try {
    const res = await fetch('/api/auth/access-token');
    if (!res.ok) {
      throw new AuthTokenError(
        `Failed to obtain access token (${res.status})`,
        res.status,
      );
    }
    const { token } = await res.json();
    if (!token) {
      throw new AuthTokenError('Access token is missing from response');
    }
    return token;
  } catch (err) {
    if (err instanceof AuthTokenError) throw err;
    throw new AuthTokenError('Unable to reach authentication service');
  }
}

/**
 * Tries to get a token but returns `null` instead of throwing.
 * Useful for contexts where the backend might not be running (frontend-only dev).
 */
async function getAccessTokenSilent(): Promise<string | null> {
  try {
    return await getAccessToken();
  } catch {
    return null;
  }
}

// ── Response parsing ─────────────────────────────────────────────────────────

/**
 * Parses the JSON body of a response and throws `ApiError` on non-OK status.
 */
async function parseResponse<T>(res: Response, url: string): Promise<T> {
  if (res.status === 204) return undefined as unknown as T;

  let body: unknown;
  const contentType = res.headers.get('content-type') ?? '';
  if (contentType.includes('application/json')) {
    body = await res.json();
  } else {
    body = await res.text();
  }

  if (!res.ok) {
    const detail = typeof body === 'object' && body !== null && 'detail' in body
      ? (body as Record<string, unknown>).detail
      : body;
    throw new ApiError(
      `API ${res.status}: ${typeof detail === 'string' ? detail : res.statusText}`,
      res.status,
      detail,
      url,
    );
  }

  return body as T;
}

// ── Core request function ────────────────────────────────────────────────────

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  /** JSON body — will be serialised automatically. */
  body?: unknown;
  /** Query string parameters. */
  params?: Record<string, string | number | boolean | undefined>;
  /**
   * When `true` the request is sent without an `Authorization` header.
   * Defaults to `false`.
   */
  noAuth?: boolean;
  /**
   * When `true` returns `null` instead of throwing on ANY error (network,
   * auth, or API). Intended for non-critical data loading where a fallback
   * is acceptable (e.g. `PricingContext`).
   */
  graceful?: boolean;
}

function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  const base = path.startsWith('http') ? path : `${API_BASE}${API_PREFIX}${path}`;
  if (!params) return base;

  const qs = new URLSearchParams();
  for (const [key, val] of Object.entries(params)) {
    if (val !== undefined) qs.set(key, String(val));
  }
  const qsStr = qs.toString();
  return qsStr ? `${base}?${qsStr}` : base;
}

/**
 * Core request function.  All service-layer helpers delegate here.
 *
 * @example
 *   const signals = await request<SignalListResponse>('/signals', { params: { limit: 20 } });
 */
export async function request<T>(
  path: string,
  { body, params, noAuth, graceful, ...init }: RequestOptions = {},
): Promise<T> {
  const url = buildUrl(path, params);
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string> ?? {}),
    };

    if (!noAuth) {
      if (graceful) {
        const token = await getAccessTokenSilent();
        if (token) headers['Authorization'] = `Bearer ${token}`;
      } else {
        const token = await getAccessToken();
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    const res = await fetch(url, {
      ...init,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    return await parseResponse<T>(res, url);
  } catch (err) {
    if (graceful) return null as unknown as T;
    if (err instanceof ApiError || err instanceof AuthTokenError) throw err;
    throw new NetworkError(
      `Network request to ${url} failed`,
      err,
    );
  }
}

// ── Convenience helpers ──────────────────────────────────────────────────────

/** GET request. */
export function get<T>(path: string, opts?: RequestOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'GET' });
}

/** POST request. */
export function post<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'POST', body });
}

/** PATCH request. */
export function patch<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'PATCH', body });
}

/** DELETE request. */
export function del<T = void>(path: string, opts?: RequestOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'DELETE' });
}

/** PUT request. */
export function put<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
  return request<T>(path, { ...opts, method: 'PUT', body });
}

// ── SSE helper ───────────────────────────────────────────────────────────────

export interface SSECallbacks {
  onEvent: (event: string, data: unknown) => void;
  onError?: (err: Error) => void;
  onDone?: () => void;
}

/**
 * Opens an SSE (Server-Sent Events) stream to a backend endpoint.
 * Used for the chat message endpoint which returns `text/event-stream`.
 *
 * Returns an `AbortController` so the caller can cancel the stream.
 */
export async function streamSSE(
  path: string,
  body: unknown,
  callbacks: SSECallbacks,
): Promise<AbortController> {
  const url = buildUrl(path);
  const controller = new AbortController();

  try {
    const token = await getAccessToken();

    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!res.ok) {
      const errBody = await res.text();
      callbacks.onError?.(new ApiError(`SSE ${res.status}`, res.status, errBody, url));
      return controller;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      callbacks.onError?.(new Error('No readable stream'));
      return controller;
    }

    const decoder = new TextDecoder();
    let buffer = '';

    const pump = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            callbacks.onDone?.();
            break;
          }
          buffer += decoder.decode(value, { stream: true });

          // Parse SSE frames
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          let currentEvent = 'message';
          for (const line of lines) {
            if (line.startsWith('event:')) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              const raw = line.slice(5).trim();
              if (raw === '[DONE]') {
                callbacks.onDone?.();
                return;
              }
              try {
                callbacks.onEvent(currentEvent, JSON.parse(raw));
              } catch {
                callbacks.onEvent(currentEvent, raw);
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          callbacks.onError?.(err as Error);
        }
      }
    };

    pump();
  } catch (err) {
    callbacks.onError?.(err as Error);
  }

  return controller;
}

// ── Export token helpers for contexts that need them directly ─────────────────

export { getAccessToken, getAccessTokenSilent };
