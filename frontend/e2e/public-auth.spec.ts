import { expect, test } from '@playwright/test'

test('login page exposes the unauthenticated sign-in experience', async ({ page }) => {
  await page.goto('/login', { waitUntil: 'domcontentloaded' })
  await expect(
    page.getByRole('heading', { name: /log in and get oriented fast/i }),
  ).toBeVisible({ timeout: 30000 })
})

test('signup page exposes the secure account onboarding flow', async ({ page }) => {
  await page.goto('/signup', { waitUntil: 'domcontentloaded' })
  await expect(page.getByRole('heading', { name: /create your account and launch with intent/i })).toBeVisible()
  await expect(page.getByText(/password creation and verification happen on the secure auth0 page/i)).toBeVisible()
})
