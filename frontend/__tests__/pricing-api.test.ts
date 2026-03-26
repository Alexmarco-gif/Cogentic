import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getTierOptions, upgradeTier } from '@/lib/api/pricing'

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: {
      get: vi.fn().mockReturnValue('application/json'),
    },
    json: vi.fn().mockResolvedValue(body),
    text: vi.fn().mockResolvedValue(JSON.stringify(body)),
  } as unknown as Response
}

describe('pricing api', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('loads public tier options without auth', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ tiers: [{ tier: 'growth', price: 499 }] }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await getTierOptions()

    expect(result.tiers).toEqual([{ tier: 'growth', price: 499 }])
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/pricing/tiers',
      expect.objectContaining({
        method: 'GET',
        headers: expect.not.objectContaining({ Authorization: expect.any(String) }),
      }),
    )
  })

  it('submits upgrade requests through the authenticated pricing endpoint', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ token: 'test-token' }))
      .mockResolvedValueOnce(
        jsonResponse({
          status: 'pending_review',
          requested_tier: 'growth',
          message: 'Tier upgrade recorded.',
        }),
      )
    vi.stubGlobal('fetch', fetchMock)

    const result = await upgradeTier({ target_tier: 'growth' })

    expect(result.status).toBe('pending_review')
    expect(fetchMock).toHaveBeenNthCalledWith(1, '/api/auth/access-token')
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/pricing/upgrade',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
        }),
        body: JSON.stringify({ target_tier: 'growth' }),
      }),
    )
  })
})
