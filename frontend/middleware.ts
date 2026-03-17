import { auth0 } from '@/lib/auth0';
import { NextResponse } from 'next/server';

/**
 * Next.js Middleware with Auth0 + CSRF Origin Check
 *
 * - /login and /signup are public (unauthenticated users land here)
 * - /dashboard/* and /api/protected/* require a valid session
 * - Auth0 callback/logout routes (/api/auth/*) pass through automatically
 * - State-changing requests to /api/* verify Origin header to prevent CSRF
 */

const STATE_CHANGING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const DEV_ONLY_PATHS = ['/jwt-test', '/auth-test', '/webhook-test'];

/**
 * Verify that state-changing requests originate from our own domain.
 * Webhooks are excluded because they use HMAC signature verification.
 */
function csrfCheck(request: Request): NextResponse | null {
  const { method, url } = request;
  const parsedUrl = new URL(url);

  // Only check state-changing methods on /api/* routes
  if (!STATE_CHANGING_METHODS.has(method)) return null;
  if (!parsedUrl.pathname.startsWith('/api/')) return null;

  // Webhooks are authenticated via HMAC — skip CSRF
  if (parsedUrl.pathname.startsWith('/api/webhooks/')) return null;

  // Auth0 SDK routes handle their own state parameter protection
  if (parsedUrl.pathname.startsWith('/api/auth/')) return null;

  const origin = request.headers.get('origin');
  const host = request.headers.get('host');

  // If there is no Origin header (e.g. same-origin fetch API calls),
  // fall back to Sec-Fetch-Site as a secondary signal.
  if (!origin) {
    const fetchSite = request.headers.get('sec-fetch-site');
    // 'same-origin' and 'none' (direct navigation) are safe
    if (fetchSite && fetchSite !== 'same-origin' && fetchSite !== 'none') {
      return NextResponse.json(
        { error: 'CSRF check failed — cross-origin request without Origin header' },
        { status: 403 },
      );
    }
    return null;
  }

  // Compare Origin to Host
  try {
    const originHost = new URL(origin).host;
    if (originHost !== host) {
      return NextResponse.json(
        { error: 'CSRF check failed — origin mismatch' },
        { status: 403 },
      );
    }
  } catch {
    return NextResponse.json(
      { error: 'CSRF check failed — malformed Origin header' },
      { status: 403 },
    );
  }

  return null;
}

export async function middleware(request: Request) {
  const { pathname } = new URL(request.url);

  // Block debug pages outside local development.
  if (DEV_ONLY_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`))) {
    if (process.env.NODE_ENV !== 'development') {
      return NextResponse.redirect(new URL('/', request.url));
    }
  }

  // CSRF origin verification (before Auth0 middleware)
  const csrfResponse = csrfCheck(request);
  if (csrfResponse) return csrfResponse;

  // /api/v1/* is a backend proxy rewrite path, not a Next Auth0 route.
  // Let it continue after CSRF checks; backend auth handles authorization.
  if (pathname.startsWith('/api/v1/')) {
    return NextResponse.next();
  }

  return await auth0.middleware(request);
}

export const config = {
  matcher: [
    /*
     * Protect dashboard and private API routes.
     * Auth0 middleware handles redirecting to /api/auth/login when no session.
     */
    '/dashboard/:path*',
    '/api/protected/:path*',
    '/api/v1/:path*',
    '/jwt-test/:path*',
    '/auth-test/:path*',
    '/webhook-test/:path*',
    '/api/webhooks/test/:path*',
    /*
     * Also run middleware on auth routes so Auth0 can handle
     * the callback, logout and session cookie refresh.
     */
    '/api/auth/:path*',
  ],
};
