/**
 * Auth0 Configuration and Helper Functions
 *
 * This module provides type-safe access to Auth0 session data
 * and custom JWT claims (org_id, roles, plan)
 */

import { Auth0Client } from '@auth0/nextjs-auth0/server';

export const auth0 = new Auth0Client({
  domain: process.env.AUTH0_DOMAIN
    ?? process.env.AUTH0_ISSUER_BASE_URL?.replace('https://', ''),
  clientId: process.env.AUTH0_CLIENT_ID,
  clientSecret: process.env.AUTH0_CLIENT_SECRET,
  appBaseUrl: process.env.APP_BASE_URL ?? process.env.AUTH0_BASE_URL,
  secret: process.env.AUTH0_SECRET,
});

/**
 * Custom JWT claims structure
 * These are added by the Auth0 Action "Add Custom Claims"
 */
export interface CustomClaims {
  'https://cogent.ai/claims/org_id'?: string;
  'https://cogent.ai/claims/roles': string[];
  'https://cogent.ai/claims/plan': 'explorer' | 'growth' | 'mid_market' | 'enterprise';
}

/**
 * Extended user type with custom claims
 */
export interface User {
  sub: string; // Auth0 user ID
  email?: string;
  name?: string;
  picture?: string;
  org_id?: string;
  roles: string[];
  plan: 'explorer' | 'growth' | 'mid_market' | 'enterprise';
}

/**
 * Get current user session with custom claims
 *
 * @returns User object with custom claims or null if not authenticated
 *
 * Usage in Server Components:
 * ```tsx
 * import { getCurrentUser } from '@/lib/auth0';
 *
 * export default async function Page() {
 *   const user = await getCurrentUser();
 *   if (!user) redirect('/api/auth/login');
 *
 *   return <div>Hello {user.name}</div>;
 * }
 * ```
 */
export async function getCurrentUser(): Promise<User | null> {
  const session = await auth0.getSession();

  if (!session?.user) {
    return null;
  }

  const claims = session.user as CustomClaims & {
    sub: string;
    email?: string;
    name?: string;
    picture?: string;
  };

  return {
    sub: claims.sub,
    email: claims.email,
    name: claims.name,
    picture: claims.picture,
    org_id: claims['https://cogent.ai/claims/org_id'],
    roles: claims['https://cogent.ai/claims/roles'] || [],
    plan: claims['https://cogent.ai/claims/plan'] || 'explorer',
  };
}

/**
 * Get access token for calling backend APIs (server-side only)
 *
 * Uses the Auth0 SDK v4 `getAccessToken()` which handles token refresh
 * and returns `{ token, scope, expiresAt }`.
 *
 * NOTE: For client-side (browser) components, use `fetchWithAuth` from
 * `@/lib/api` instead, which fetches the token via `/api/auth/access-token`.
 *
 * @returns Access token string or null if not authenticated
 *
 * Usage in Server Components / Route Handlers:
 * ```tsx
 * const token = await getAccessToken();
 * const response = await fetch('http://localhost:8000/api/resource', {
 *   headers: { Authorization: `Bearer ${token}` }
 * });
 * ```
 */
export async function getAccessToken(): Promise<string | null> {
  try {
    const { token } = await auth0.getAccessToken();
    return token;
  } catch {
    // User not authenticated or session expired
    return null;
  }
}

/**
 * Check if user has specific role
 *
 * @param role - Role to check (owner, admin, member, viewer)
 * @returns true if user has the role
 *
 * Usage:
 * ```tsx
 * const user = await getCurrentUser();
 * if (user && hasRole(user, 'admin')) {
 *   // Show admin features
 * }
 * ```
 */
export function hasRole(user: User, role: string): boolean {
  return user.roles.includes(role);
}

/**
 * Check if user has at least one of the specified roles
 *
 * @param user - User object
 * @param roles - Array of roles to check
 * @returns true if user has any of the roles
 */
export function hasAnyRole(user: User, roles: string[]): boolean {
  return roles.some(role => user.roles.includes(role));
}

/**
 * Role hierarchy checker
 * Owner > Admin > Member > Viewer
 *
 * @param user - User object
 * @param minimumRole - Minimum required role
 * @returns true if user meets minimum role requirement
 */
export function meetsRoleRequirement(
  user: User,
  minimumRole: 'owner' | 'admin' | 'analyst' | 'member' | 'viewer'
): boolean {
  const hierarchy = {
    owner: 4,
    admin: 3,
    analyst: 2,
    member: 2,
    viewer: 1,
  };

  const userLevel = Math.max(
    ...user.roles.map(role => hierarchy[role as keyof typeof hierarchy] || 0)
  );

  return userLevel >= hierarchy[minimumRole];
}
