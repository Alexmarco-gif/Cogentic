/**
 * Unit tests for API error types (`lib/api/errors.ts`).
 *
 * Validates:
 *   - Error class hierarchy and instanceof checks
 *   - Type guards (isApiError, isAuthTokenError, isNetworkError)
 *   - Status helper properties (isNotFound, isUnauthorized, etc.)
 *   - friendlyErrorMessage() returns human-readable strings
 */

import { describe, it, expect } from 'vitest';
import {
  ApiError,
  AuthTokenError,
  NetworkError,
  isApiError,
  isAuthTokenError,
  isNetworkError,
  friendlyErrorMessage,
} from '@/lib/api/errors';

describe('Error classes', () => {
  describe('ApiError', () => {
    it('stores status, detail, and url', () => {
      const err = new ApiError('Not found', 404, 'Signal not found', '/api/v1/signals/x');
      expect(err.message).toBe('Not found');
      expect(err.status).toBe(404);
      expect(err.detail).toBe('Signal not found');
      expect(err.url).toBe('/api/v1/signals/x');
      expect(err.name).toBe('ApiError');
    });

    it('has correct status predicates', () => {
      expect(new ApiError('', 401, null, '').isUnauthorized).toBe(true);
      expect(new ApiError('', 403, null, '').isForbidden).toBe(true);
      expect(new ApiError('', 404, null, '').isNotFound).toBe(true);
      expect(new ApiError('', 429, null, '').isRateLimited).toBe(true);
      expect(new ApiError('', 422, null, '').isValidation).toBe(true);
    });

    it('is instance of Error', () => {
      const err = new ApiError('test', 500, null, '');
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(ApiError);
    });
  });

  describe('AuthTokenError', () => {
    it('stores optional status', () => {
      const err = new AuthTokenError('Failed', 401);
      expect(err.status).toBe(401);
      expect(err.name).toBe('AuthTokenError');
    });

    it('works without status', () => {
      const err = new AuthTokenError('Missing token');
      expect(err.status).toBeUndefined();
    });
  });

  describe('NetworkError', () => {
    it('wraps a cause', () => {
      const cause = new TypeError('fetch failed');
      const err = new NetworkError('Request failed', cause);
      expect(err.cause).toBe(cause);
      expect(err.name).toBe('NetworkError');
    });
  });
});

describe('Type guards', () => {
  it('isApiError', () => {
    expect(isApiError(new ApiError('', 500, null, ''))).toBe(true);
    expect(isApiError(new Error('test'))).toBe(false);
    expect(isApiError(null)).toBe(false);
  });

  it('isAuthTokenError', () => {
    expect(isAuthTokenError(new AuthTokenError('x'))).toBe(true);
    expect(isAuthTokenError(new Error('x'))).toBe(false);
  });

  it('isNetworkError', () => {
    expect(isNetworkError(new NetworkError('x'))).toBe(true);
    expect(isNetworkError(new ApiError('x', 500, null, ''))).toBe(false);
  });
});

describe('friendlyErrorMessage()', () => {
  it('returns user-readable message for ApiError', () => {
    const msg = friendlyErrorMessage(new ApiError('', 401, null, ''));
    expect(msg).toBeTruthy();
    expect(typeof msg).toBe('string');
  });

  it('returns user-readable message for AuthTokenError', () => {
    const msg = friendlyErrorMessage(new AuthTokenError('Session expired'));
    expect(msg).toContain('session');
  });

  it('returns user-readable message for NetworkError', () => {
    const msg = friendlyErrorMessage(new NetworkError('offline'));
    expect(msg).toBeTruthy();
  });

  it('returns generic message for unknown errors', () => {
    const msg = friendlyErrorMessage(new Error('random'));
    expect(msg).toBeTruthy();
    expect(typeof msg).toBe('string');
  });
});
