// In-memory storage for recent webhook events (last 50)
// Used by the test webhook endpoint and the webhook handler

const recentEvents: any[] = []
const MAX_EVENTS = 50

export function addWebhookEvent(event: any) {
  recentEvents.unshift({
    ...event,
    receivedAt: new Date().toISOString(),
  })
  if (recentEvents.length > MAX_EVENTS) {
    recentEvents.pop()
  }
}

export function getRecentEvents() {
  return recentEvents
}
