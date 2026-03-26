import crypto from 'crypto'

/**
 * Verify HMAC signature.
 */
export function verifyHmacSignature(
  payload: string,
  signature: string,
  secret: string,
): boolean {
  try {
    const expectedSignature = crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex')

    if (Buffer.byteLength(signature) !== Buffer.byteLength(expectedSignature)) {
      return false
    }

    return crypto.timingSafeEqual(
      Buffer.from(signature),
      Buffer.from(expectedSignature),
    )
  } catch (error) {
    console.error('HMAC verification error:', error)
    return false
  }
}

/**
 * Verify timestamp to prevent replay attacks.
 */
export function verifyTimestamp(
  timestamp: string | number,
  maxAgeSeconds: number = 300,
): boolean {
  try {
    const eventTime =
      typeof timestamp === 'string'
        ? new Date(timestamp).getTime()
        : timestamp * 1000

    const now = Date.now()
    const age = (now - eventTime) / 1000

    return age >= 0 && age <= maxAgeSeconds
  } catch (error) {
    console.error('Timestamp verification error:', error)
    return false
  }
}

export interface Auth0Event {
  type: string
  date: string
  user_id?: string
  user_name?: string
  user_email?: string
  ip?: string
  description?: string
  details?: Record<string, any>
}

export function parseAuth0Event(event: any): Auth0Event {
  return {
    type: event.type,
    date: event.date,
    user_id: event.user_id,
    user_name: event.user_name,
    user_email: event.details?.user_email || event.user_name,
    ip: event.ip,
    description: event.description,
    details: event.details || {},
  }
}

export function logWebhookEvent(
  event: Auth0Event,
  result: 'success' | 'error',
  errorMessage?: string,
) {
  const logEntry = {
    timestamp: new Date().toISOString(),
    event_type: event.type,
    user_id: event.user_id,
    user_email: event.user_email,
    ip: event.ip,
    result,
    error: errorMessage,
  }

  console.log('[WEBHOOK EVENT]', JSON.stringify(logEntry))
}

export function extractUserInfo(event: Auth0Event) {
  return {
    userId: event.user_id,
    email: event.user_email || event.user_name,
    name: event.details?.user_name,
    ip: event.ip,
    timestamp: event.date,
  }
}
