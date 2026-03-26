import { expect, test } from '@playwright/test'

test('legal hub lists the production legal documents', async ({ page }) => {
  await page.goto('/legal', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: /legal & compliance/i })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Terms of Service', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Privacy Policy', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /data processing addendum/i })).toBeVisible()
})

test('privacy document renders with current metadata', async ({ page }) => {
  await page.goto('/legal/privacy', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: /privacy policy/i })).toBeVisible()
  await expect(page.getByText(/effective date:/i)).toBeVisible()
})

test('terms document renders with current metadata', async ({ page }) => {
  await page.goto('/legal/terms', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: /terms of service/i })).toBeVisible()
  await expect(page.getByText(/decision support disclaimer/i)).toBeVisible()
})
