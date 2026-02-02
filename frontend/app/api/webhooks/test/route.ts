import { NextResponse } from 'next/server';

/**
 * Webhook Test Endpoint
 * 
 * GET /api/webhooks/test
 * 
 * Returns recent webhook events for debugging
 * (In production, store these in a database)
 */

// In-memory storage for recent events (last 50)
const recentEvents: any[] = [];
const MAX_EVENTS = 50;

export function addWebhookEvent(event: any) {
  recentEvents.unshift({
    ...event,
    receivedAt: new Date().toISOString(),
  });
  
  // Keep only last 50 events
  if (recentEvents.length > MAX_EVENTS) {
    recentEvents.pop();
  }
}

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    totalEvents: recentEvents.length,
    events: recentEvents,
  });
}

export async function DELETE() {
  recentEvents.length = 0;
  return NextResponse.json({
    status: 'ok',
    message: 'All events cleared',
  });
}
