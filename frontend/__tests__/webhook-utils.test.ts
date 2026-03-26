import crypto from 'crypto'
import { describe, expect, it } from 'vitest'

import { verifyHmacSignature, verifyTimestamp } from '@/lib/webhook-utils'

describe('webhook utilities', () => {
  it('accepts matching HMAC signatures', () => {
    const payload = JSON.stringify({ type: 'ss', user_id: 'auth0|123' })
    const secret = 'super-secret'
    const signature = crypto.createHmac('sha256', secret).update(payload).digest('hex')

    expect(verifyHmacSignature(payload, signature, secret)).toBe(true)
  })

  it('rejects non-matching HMAC signatures', () => {
    expect(verifyHmacSignature('payload', 'not-valid', 'secret')).toBe(false)
  })

  it('rejects stale timestamps', () => {
    const stale = new Date(Date.now() - 10 * 60 * 1000).toISOString()
    expect(verifyTimestamp(stale, 300)).toBe(false)
  })
})
