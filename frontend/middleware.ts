import { withMiddlewareAuthRequired } from '@auth0/nextjs-auth0/edge';

/**
 * Next.js Middleware with Auth0
 * 
 * Automatically protects routes that require authentication
 * 
 * Current config: Only /api/protected/* routes require auth
 * 
 * To protect more routes, add patterns to matcher below
 */

export default withMiddlewareAuthRequired();

/**
 * Configure which routes require authentication
 * 
 * Examples:
 * - '/dashboard/:path*' - Protect all dashboard routes
 * - '/admin/:path*' - Protect all admin routes
 * - '/api/private/:path*' - Protect specific API routes
 */
export const config = {
  matcher: [
    '/api/protected/:path*',
    '/dashboard/:path*',
  ],
};
