import { NextResponse } from 'next/server';
import { auth0, getCurrentUser } from '@/lib/auth0';

/**
 * Protected API Route Example
 *
 * Demonstrates:
 * - JWT verification
 * - Access to user session
 * - Custom claims extraction
 * - Error handling for unauthorized access
 *
 * Usage from frontend:
 * ```tsx
 * const response = await fetch('/api/protected');
 * const data = await response.json();
 * ```
 */
export async function GET() {
  try {
    // Get session (automatically verifies JWT)
    const session = await auth0.getSession();

    if (!session) {
      return NextResponse.json(
        { error: 'Unauthorized - No session found' },
        { status: 401 }
      );
    }

    // Get user with custom claims
    const user = await getCurrentUser();

    if (!user) {
      return NextResponse.json(
        { error: 'Unauthorized - Invalid user' },
        { status: 401 }
      );
    }

    // Example: Check role
    const isAdmin = user.roles.includes('admin') || user.roles.includes('owner');

    return NextResponse.json({
      message: 'Access granted to protected resource',
      user: {
        id: user.sub,
        email: user.email,
        name: user.name,
      },
      claims: {
        org_id: user.org_id,
        roles: user.roles,
        plan: user.plan,
      },
      permissions: {
        isAdmin,
        canAccessPremiumFeatures: user.plan !== 'explorer',
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error('Protected route error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * Example POST endpoint with role check
 */
export async function POST() {
  const user = await getCurrentUser();

  if (!user) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401 }
    );
  }

  // Example: Require admin role
  const isAdmin = user.roles.includes('admin') || user.roles.includes('owner');

  if (!isAdmin) {
    return NextResponse.json(
      { error: 'Forbidden - Admin access required' },
      { status: 403 }
    );
  }

  return NextResponse.json({
    message: 'Admin action completed',
    user: user.email,
  });
}
