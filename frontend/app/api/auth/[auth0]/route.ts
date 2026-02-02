import { handleAuth } from '@auth0/nextjs-auth0';

/**
 * Auth0 Authentication Routes
 * 
 * This handles all Auth0 authentication endpoints:
 * - /api/auth/login - Initiates login flow
 * - /api/auth/logout - Logs user out
 * - /api/auth/callback - Handles Auth0 callback after login
 * - /api/auth/me - Returns current user session
 * 
 * Uses the @auth0/nextjs-auth0 SDK which automatically:
 * - Manages Authorization Code Flow with PKCE
 * - Stores session in encrypted httpOnly cookies
 * - Handles token refresh automatically
 */
export const GET = handleAuth();
