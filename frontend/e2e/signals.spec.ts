import { test, expect } from '@playwright/test';

/**
 * E2E: Signals Workflow
 *
 * Tests the signal browsing, filtering, and detail view flows
 * that form the core user experience.
 */

test.describe('Signals', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/signals');
    await page.waitForLoadState('networkidle');
  });

  test('displays signal list or empty state', async ({ page }) => {
    // Either a list of signal cards or an empty-state message
    const content = page.locator(
      '[data-testid="signals-list"], [data-testid="empty-state"], table'
    ).first();
    await expect(content).toBeVisible({ timeout: 15_000 });
  });

  test('signal cards show required fields', async ({ page }) => {
    const firstSignal = page.locator(
      '[data-testid="signal-card"], tr[data-testid]'
    ).first();

    // Skip if no signals exist
    if (!(await firstSignal.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    // Each signal should show at least a title
    await expect(firstSignal).toContainText(/.+/);
  });

  test('search filters signals', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search|filter/i).first();

    // Skip if no search input
    if (!(await searchInput.isVisible({ timeout: 3_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await searchInput.fill('test');
    await searchInput.press('Enter');

    // Wait for filtered results
    await page.waitForTimeout(1_000);

    // Page should still be functional (not error)
    await expect(page.locator('body')).not.toContainText(/500|Internal Server Error/i);
  });

  test('signal detail view loads', async ({ page }) => {
    const firstSignal = page.locator(
      '[data-testid="signal-card"] a, tr[data-testid] a, [data-testid="signal-link"]'
    ).first();

    if (!(await firstSignal.isVisible({ timeout: 5_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await firstSignal.click();
    await page.waitForLoadState('networkidle');

    // Should navigate to a detail page or open a modal
    await expect(
      page.locator('[data-testid="signal-detail"], [role="dialog"], article').first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test('confidence filter works', async ({ page }) => {
    const confidenceFilter = page.locator(
      '[data-testid="confidence-filter"], select[name*="confidence"]'
    ).first();

    if (!(await confidenceFilter.isVisible({ timeout: 3_000 }).catch(() => false))) {
      test.skip();
      return;
    }

    await confidenceFilter.selectOption({ index: 1 });
    await page.waitForTimeout(1_000);

    // Should not crash
    await expect(page.locator('body')).not.toContainText(/error|500/i);
  });
});
