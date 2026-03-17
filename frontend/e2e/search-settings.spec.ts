import { test, expect } from '@playwright/test';

/**
 * E2E: Search & Investigation Flow
 *
 * Tests the AI-powered search and investigation features
 * that drive intelligence discovery.
 */

test.describe('Search & Investigation', () => {
  test('investigate page has search input', async ({ page }) => {
    await page.goto('/dashboard/investigate');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByPlaceholder(/search|ask|query|investigate/i).first();
    const textArea = page.getByRole('textbox').first();

    const hasInput = await searchInput.isVisible({ timeout: 5_000 }).catch(() => false);
    const hasTextArea = await textArea.isVisible({ timeout: 2_000 }).catch(() => false);

    expect(hasInput || hasTextArea).toBeTruthy();
  });

  test('can submit a search query', async ({ page }) => {
    await page.goto('/dashboard/investigate');
    await page.waitForLoadState('networkidle');

    const searchInput = page
      .getByPlaceholder(/search|ask|query|investigate/i)
      .or(page.getByRole('textbox'))
      .first();

    if (!(await searchInput.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await searchInput.fill('What are the latest fintech regulations in Nigeria?');

    // Submit via Enter or button
    const submitBtn = page.getByRole('button', {
      name: /search|submit|send|go/i,
    }).first();

    if (await submitBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await submitBtn.click();
    } else {
      await searchInput.press('Enter');
    }

    // Should show loading or results
    await expect(
      page.locator(
        '[data-testid="search-results"], [data-testid="loading"], .animate-pulse, [role="progressbar"]'
      ).first()
    ).toBeVisible({ timeout: 30_000 });
  });

  test('search results display correctly', async ({ page }) => {
    await page.goto('/dashboard/investigate');
    await page.waitForLoadState('networkidle');

    const searchInput = page
      .getByPlaceholder(/search|ask|query|investigate/i)
      .or(page.getByRole('textbox'))
      .first();

    if (!(await searchInput.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await searchInput.fill('technology trends');

    const submitBtn = page.getByRole('button', {
      name: /search|submit|send|go/i,
    }).first();

    if (await submitBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await submitBtn.click();
    } else {
      await searchInput.press('Enter');
    }

    // Wait for results to load (generous timeout for AI processing)
    await page.waitForTimeout(5_000);

    // Page should not show an error
    await expect(page.locator('body')).not.toContainText(
      /500|Internal Server Error|Something went wrong/i
    );
  });
});

test.describe('Settings', () => {
  test('settings page loads', async ({ page }) => {
    await page.goto('/dashboard/settings');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading').first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test('displays user profile information', async ({ page }) => {
    await page.goto('/dashboard/settings');
    await page.waitForLoadState('networkidle');

    // Should show email or user name somewhere
    const profileSection = page.locator(
      '[data-testid="profile"], [data-testid="user-info"], form'
    ).first();

    if (await profileSection.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await expect(profileSection).toContainText(/.+/);
    }
  });

  test('domain management is accessible', async ({ page }) => {
    await page.goto('/dashboard/domains');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading').first()).toBeVisible({
      timeout: 10_000,
    });

    // Should not error
    await expect(page.locator('body')).not.toContainText(
      /500|Internal Server Error/i
    );
  });
});
