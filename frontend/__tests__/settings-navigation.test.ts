import { describe, expect, it } from 'vitest'

import { SETTINGS_TABS } from '@/lib/hooks/useSettings'

describe('settings navigation', () => {
  it('exposes the live plan and notification tabs', () => {
    const tabIds = SETTINGS_TABS.map((tab) => tab.id)

    expect(tabIds).toContain('notifications')
    expect(tabIds).toContain('plan')
    expect(tabIds).not.toContain('billing')
    expect(tabIds).not.toContain('integrations')
  })
})
