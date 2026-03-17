import { test, expect } from '@playwright/test';

/**
 * E2E: Dashboard Navigation
 *
 * Verifies the authenticated user can navigate to all major dashboard
 * sections and that each section renders its primary content.
 */

test.describe('Dashboard Navigation', () => {
  test('loads dashboard home', async ({ page }) => {
    await page.goto('/dashboard/home');
    await expect(page).toHaveURL(/.*dashboard\/home.*/);

    // Dashboard should show a heading or welcome element
    await expect(
      page.getByRole('heading').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to signals page', async ({ page }) => {
    await page.goto('/dashboard/signals');
    await expect(page).toHaveURL(/.*dashboard\/signals.*/);

    // Should show signals list or empty state
    await expect(
      page.locator('[data-testid="signals-list"], [data-testid="empty-state"]')
        .first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to library page', async ({ page }) => {
    await page.goto('/dashboard/library');
    await expect(page).toHaveURL(/.*dashboard\/library.*/);

    await expect(
      page.getByRole('heading').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to studio page', async ({ page }) => {
    await page.goto('/dashboard/studio');
    await expect(page).toHaveURL(/.*dashboard\/studio.*/);

    await expect(
      page.getByRole('heading').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to investigate page', async ({ page }) => {
    await page.goto('/dashboard/investigate');
    await expect(page).toHaveURL(/.*dashboard\/investigate.*/);

    await expect(
      page.getByRole('heading').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to settings page', async ({ page }) => {
    await page.goto('/dashboard/settings');
    await expect(page).toHaveURL(/.*dashboard\/settings.*/);

    await expect(
      page.getByRole('heading').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('navigates to domains page', async ({ page }) => {
    await page.goto('/dashboard/domains');
    await expect(page).toHaveURL(/.*dashboard\/domains.*/);

    await expect(
      page.getByRole('heading').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('sidebar navigation works', async ({ page }) => {
    await page.goto('/dashboard/home');
    await expect(page).toHaveURL(/.*dashboard\/home.*/);

    // Find and click the signals nav link
    const signalsLink = page.getByRole('link', { name: /signals/i }).first();
    if (await signalsLink.isVisible()) {
      await signalsLink.click();
      await expect(page).toHaveURL(/.*dashboard\/signals.*/);
    }
  });

  test('redirects unauthenticated users to login', async ({ browser }) => {
    // Create a fresh context without saved auth state
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/dashboard/home');

    // Should redirect to Auth0 login or app login page
    await expect(page).not.toHaveURL(/.*dashboard\/home.*/);

    await context.close();
  });
});
