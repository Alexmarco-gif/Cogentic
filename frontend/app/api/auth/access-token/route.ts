import { auth0 } from '@/lib/auth0';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET() {
  try {
    const { token, expiresAt, scope } = await auth0.getAccessToken();

    if (!token) {
      return NextResponse.json(
        { error: 'Authentication required' },
        { status: 401, headers: { 'Cache-Control': 'no-store' } },
      );
    }

    return NextResponse.json(
      { token, expiresAt, scope },
      { headers: { 'Cache-Control': 'no-store' } },
    );
  } catch {
    return NextResponse.json(
      { error: 'Authentication required' },
      { status: 401, headers: { 'Cache-Control': 'no-store' } },
    );
  }
}
