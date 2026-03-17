import { auth0 } from '@/lib/auth0';
import { NextRequest } from 'next/server';

/**
 * Auth0 Authentication Routes
 *
 * This handles all Auth0 authentication endpoints:
 * - /api/auth/login     - Initiates login flow
 * - /api/auth/logout    - Logs user out
 * - /api/auth/callback  - Handles Auth0 callback after login
 * - /api/auth/profile   - Returns current user session
 *
 * Uses @auth0/nextjs-auth0 v4 SDK: auth0.middleware() mounts
 * the SDK routes and handles Authorization Code Flow with PKCE,
 * encrypted httpOnly cookie sessions, and token refresh.
 */
export async function GET(req: NextRequest) {
  return auth0.middleware(req);
}

export async function POST(req: NextRequest) {
  return auth0.middleware(req);
}
