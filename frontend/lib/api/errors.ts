/**
 * Unified API error types for the Cogent frontend.
 *
 * All service methods throw one of these typed errors so that callers
 * (hooks, components, middleware) can handle every failure mode uniformly.
 */

// ── Error classes ────────────────────────────────────────────────────────────

/** Thrown when the Auth0 access-token endpoint is unreachable or returns a non-OK status. */
export class AuthTokenError extends Error {
  readonly name = 'AuthTokenError' as const;
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
  }
}

/** Thrown when a backend API call returns an HTTP error (4xx / 5xx). */
export class ApiError extends Error {
  readonly name = 'ApiError' as const;
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
    public readonly url?: string,
  ) {
    super(message);
  }

  /** True when the server rejected the request due to invalid input (422). */
  get isValidation(): boolean {
    return this.status === 422;
  }

  /** True when the caller is not authenticated (401). */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** True when the caller lacks required permissions (403). */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** True when the requested resource does not exist (404). */
  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** True when the caller has exceeded their rate limit (429). */
  get isRateLimited(): boolean {
    return this.status === 429;
  }
}

/** Thrown when the network request itself fails (offline, DNS, timeout, etc.). */
export class NetworkError extends Error {
  readonly name = 'NetworkError' as const;
  constructor(message: string, public readonly cause?: unknown) {
    super(message);
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/** Type-guard for `ApiError`. */
export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}

/** Type-guard for `AuthTokenError`. */
export function isAuthTokenError(err: unknown): err is AuthTokenError {
  return err instanceof AuthTokenError;
}

/** Type-guard for `NetworkError`. */
export function isNetworkError(err: unknown): err is NetworkError {
  return err instanceof NetworkError;
}

/**
 * Returns a user-friendly error message from any error.
 * Safe to call in UI error boundaries / toast handlers.
 */
export function friendlyErrorMessage(err: unknown): string {
  if (isAuthTokenError(err)) return 'Your session has expired. Please sign in again.';
  if (isApiError(err)) {
    if (err.isUnauthorized) return 'Your session has expired. Please sign in again.';
    if (err.isForbidden) return 'You do not have permission to perform this action.';
    if (err.isNotFound) return 'The requested resource was not found.';
    if (err.isRateLimited) return 'Too many requests. Please try again shortly.';
    if (err.isValidation) return 'Invalid input. Please check your data and try again.';
    return err.message || 'An unexpected error occurred.';
  }
  if (isNetworkError(err)) return 'Network error. Please check your connection.';
  if (err instanceof Error) return err.message;
  return 'An unexpected error occurred.';
}
