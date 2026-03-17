import { NextResponse } from 'next/server';
import { auth0 } from '@/lib/auth0';
import { getRecentEvents } from '@/lib/webhookStore';

/**
 * Webhook Test Endpoint (development only)
 *
 * GET /api/webhooks/test — returns recent webhook events for debugging
 * DELETE /api/webhooks/test — clears the event log
 *
 * Disabled in production to prevent information disclosure.
 */

function prodGuard() {
  if (process.env.NODE_ENV === 'production') {
    return NextResponse.json({ error: 'Not available' }, { status: 404 })
  }
  return null
}

async function authGuard() {
  const session = await auth0.getSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }
  return null;
}

export async function GET() {
  const blocked = prodGuard()
  if (blocked) return blocked

  const unauthorized = await authGuard()
  if (unauthorized) return unauthorized

  const events = getRecentEvents()
  return NextResponse.json({
    status: 'ok',
    totalEvents: events.length,
    events,
  })
}

export async function DELETE() {
  const blocked = prodGuard()
  if (blocked) return blocked

  const unauthorized = await authGuard()
  if (unauthorized) return unauthorized

  const events = getRecentEvents()
  events.length = 0
  return NextResponse.json({
    status: 'ok',
    message: 'All events cleared',
  })
}
