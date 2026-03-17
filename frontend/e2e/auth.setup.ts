import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '.auth', 'session.json');

/**
 * Auth0 Login Setup
 *
 * Authenticates via Auth0 Universal Login and saves the session
 * state so subsequent tests can reuse it.
 *
 * Required environment variables:
 *   E2E_USERNAME — Auth0 test user email
 *   E2E_PASSWORD — Auth0 test user password
 */
setup('authenticate', async ({ page }) => {
  const username = process.env.E2E_USERNAME;
  const password = process.env.E2E_PASSWORD;

  if (!username || !password) {
    throw new Error(
      'E2E_USERNAME and E2E_PASSWORD must be set for authentication setup'
    );
  }

  // Navigate to login page — Auth0 redirect
  await page.goto('/api/auth/login');

  // Wait for Auth0 Universal Login page
  await page.waitForURL(/.*auth0\.com.*/, { timeout: 15_000 });

  // Fill Auth0 login form
  await page.getByLabel(/email/i).fill(username);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole('button', { name: /continue|log in|submit/i }).click();

  // Handle consent screen if it appears (first-time login)
  const consentButton = page.getByRole('button', {
    name: /accept|allow|authorize/i,
  });
  if (await consentButton.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await consentButton.click();
  }

  // Wait for redirect back to the app
  await page.waitForURL('**/dashboard/**', { timeout: 30_000 });

  // Verify we're logged in
  await expect(page).toHaveURL(/.*dashboard.*/);

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
